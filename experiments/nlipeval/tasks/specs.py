"""Stage 02: pin CAMARA OpenAPI files, count breaking changes, build prompt excerpts.

Run from experiments/:  uv run python -m nlipeval.tasks.specs [fetch|diff|excerpts|all]
"""
from __future__ import annotations

import copy
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "specs"
RESULTS = ROOT / "results" / "specs"
OASDIFF_VERSION = "1.33.0"

# api -> (repository, [(our_version, git_tag, path)], server_version)
VERSIONS: dict[str, dict] = {
    "L1": {
        "repo": "DeviceStatus",
        "server": "v1.0.0",
        "versions": [
            ("v0.5.1", "v0.5.1", "code/API_definitions/device-status.yaml"),
            ("v0.6.0", "r1.2", "code/API_definitions/device-reachability-status.yaml"),
            ("v1.0.0", "r2.2", "code/API_definitions/device-reachability-status.yaml"),
        ],
    },
    "L2": {
        "repo": "DeviceLocation",
        "server": "v3.0.0",
        "versions": [
            ("v0.1.0", "v0.1.0", "code/API_definitions/location.yaml"),
            ("v0.2.0", "v0.2.0", "code/API_definitions/location-verification.yaml"),
            ("v1.0.0", "r1.2", "code/API_definitions/location-verification.yaml"),
            ("v2.0.0", "r2.2", "code/API_definitions/location-verification.yaml"),
            ("v3.0.0", "r3.2", "code/API_definitions/location-verification.yaml"),
        ],
    },
    "L3": {
        "repo": "QualityOnDemand",
        "server": "v1.1.0",
        "versions": [
            ("v0.8.1", "v0.8.1", "code/API_definitions/qod-api.yaml"),
            ("v0.9.0", "v0.9.0", "code/API_definitions/qod-api.yaml"),
            ("v0.10.0", "v0.10.0", "code/API_definitions/qod-api.yaml"),
            ("v0.11.0", "r1.2", "code/API_definitions/quality-on-demand.yaml"),
            ("v1.0.0", "r2.2", "code/API_definitions/quality-on-demand.yaml"),
            ("v1.1.0", "r3.2", "code/API_definitions/quality-on-demand.yaml"),
        ],
    },
}
# Extra pinned files (server agent looks up profiles at the server version)
EXTRA = [("L3", "qos-profiles", "v1.1.0", "r3.2", "code/API_definitions/qos-profiles.yaml")]

# Operations the tasks use (path, method); path matching is by suffix, see _find_ops
OPERATIONS = {
    "L1": ["retrieve reachability", "reachability"],
    "L2": ["verify"],
    "L3": ["sessions"],
}


# stage 03b: oasdiff --match-path, restricted to the paths the tasks use (L1's first step needs both paths)
MATCH_PATH = {
    "L1": r"^/(connectivity|retrieve)$",
    "L2": r"^/verify$",
    "L3": r"^/sessions(/\{sessionId\})?$",
}


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _git(repo_dir: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo_dir), *args], check=True, capture_output=True, text=True).stdout.strip()


def fetch(cache: Path = Path("/tmp/camara")) -> None:
    """Download every spec at its tag (shallow clones in `cache`) and write MANIFEST.yaml."""
    cache.mkdir(parents=True, exist_ok=True)
    manifest = []
    jobs = [(api, c["repo"], v, t, p, f"{v}.yaml") for api, c in VERSIONS.items() for v, t, p in c["versions"]]
    jobs += [(api, VERSIONS[api]["repo"], v, t, p, f"{name}-{v}.yaml") for api, name, v, t, p in EXTRA]
    for api, repo, version, tag, path, fname in jobs:
        rd = cache / repo
        if not rd.exists():
            subprocess.run(
                ["git", "clone", "-q", "--filter=blob:none", f"https://github.com/camaraproject/{repo}.git", str(rd)],
                check=True,
            )
        data = subprocess.run(["git", "-C", str(rd), "show", f"{tag}:{path}"], check=True, capture_output=True).stdout
        out = SPECS / api / fname
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        doc = yaml.safe_load(data)
        assert str(doc["openapi"]).startswith("3."), out
        assert f"v{doc['info']['version']}" == version, (out, doc["info"]["version"])
        manifest.append(
            {
                "api": api,
                "file": f"{api}/{fname}",
                "version": version,
                "repository": f"https://github.com/camaraproject/{repo}",
                "tag": tag,
                "path": path,
                "commit_sha": _git(rd, "rev-parse", f"{tag}^{{commit}}"),
                "sha256": sha256(data),
                "licence": "Apache-2.0",
                "openapi": str(doc["openapi"]),
            }
        )
    note = (
        "Pinned CAMARA OpenAPI files. L1 v0.5.1 is the combined `device-status` API (connectivity + roaming); "
        "later L1 files are the separate reachability-status API. L3 qos-profiles-v1.1.0 is the extra file the "
        "server agent needs for profile lookup."
    )
    (SPECS / "MANIFEST.yaml").write_text(yaml.safe_dump({"note": note, "oasdiff_version": OASDIFF_VERSION, "files": manifest}, sort_keys=False))
    print(f"pinned {len(manifest)} files")


def _oasdiff(*args: str) -> list:
    r = subprocess.run(["oasdiff", *args, "--format", "json"], capture_output=True, text=True)
    if r.returncode not in (0,):  # breaking/changelog return 0 unless --fail-on is set
        raise RuntimeError(f"oasdiff {' '.join(args)} failed: {r.stderr}")
    return json.loads(r.stdout or "[]") or []


def check_oasdiff() -> None:
    v = subprocess.run(["oasdiff", "--version"], capture_output=True, text=True).stdout
    assert OASDIFF_VERSION in v, f"expected oasdiff {OASDIFF_VERSION}, got {v!r}"


def diff() -> None:
    check_oasdiff()
    RESULTS.mkdir(parents=True, exist_ok=True)
    rows = []
    err_by_step: dict[tuple[str, str, str], int] = {}
    ops_by_step: dict[tuple[str, str, str], int] = {}
    for api, c in VERSIONS.items():
        vs = [v for v, _, _ in c["versions"]]
        for old, new in zip(vs, vs[1:]):
            a, b = str(SPECS / api / f"{old}.yaml"), str(SPECS / api / f"{new}.yaml")
            br = _oasdiff("breaking", a, b)
            err = sum(1 for x in br if x.get("level") == 3)
            warn = sum(1 for x in br if x.get("level") == 2)
            allc = len(_oasdiff("changelog", a, b))
            bo = _oasdiff("breaking", a, b, "--match-path", MATCH_PATH[api])
            err_ops = sum(1 for x in bo if x.get("level") == 3)
            warn_ops = sum(1 for x in bo if x.get("level") == 2)
            err_by_step[(api, old, new)] = err
            ops_by_step[(api, old, new)] = err_ops
            rows.append(dict(api=api, from_version=old, to_version=new, all_changes=allc, breaking_err=err, breaking_warn=warn,
                             breaking_err_ops=err_ops, breaking_warn_ops=warn_ops))
    with open(RESULTS / "breaking_changes.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["api", "from_version", "to_version", "all_changes", "breaking_err", "breaking_warn",
                                          "breaking_err_ops", "breaking_warn_ops"])
        w.writeheader()
        w.writerows(rows)
    crossed = []
    for api, c in VERSIONS.items():
        vs = [v for v, _, _ in c["versions"]]
        server_i = vs.index(c["server"])
        for i, v in enumerate(vs):
            total = sum(err_by_step[(api, vs[j], vs[j + 1])] for j in range(i, server_i))
            total_ops = sum(ops_by_step[(api, vs[j], vs[j + 1])] for j in range(i, server_i))
            crossed.append(dict(api=api, client_version=v, versions_behind=server_i - i, breaking_crossed=total,
                                breaking_crossed_ops=total_ops))
    with open(RESULTS / "breaking_crossed.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["api", "client_version", "versions_behind", "breaking_crossed", "breaking_crossed_ops"])
        w.writeheader()
        w.writerows(crossed)

    # Catalogue-based measure of breaking changes (stage 04b)
    from nlipeval.tasks import changes
    catalogue_crossed = []
    for api, c in VERSIONS.items():
        vs = [v for v, _, _ in c["versions"]]
        server_i = vs.index(c["server"])
        for i, v in enumerate(vs):
            total, req, res = changes.catalogue_breaking_counts(api, v)
            catalogue_crossed.append(dict(
                api=api, client_version=v, versions_behind=server_i - i,
                catalogue_breaking_crossed=total,
                catalogue_breaking_request=req,
                catalogue_breaking_response=res
            ))
    with open(RESULTS / "catalogue_breaking_crossed.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["api", "client_version", "versions_behind",
                                          "catalogue_breaking_crossed",
                                          "catalogue_breaking_request",
                                          "catalogue_breaking_response"])
        w.writeheader()
        w.writerows(catalogue_crossed)
    print("wrote breaking_changes.csv, breaking_crossed.csv, catalogue_breaking_crossed.csv")


def patch_check(cache: Path = Path("/tmp/camara")) -> None:
    """D10: oasdiff L3 v0.10.0 -> v0.10.1, to show the patch release has no ERR-level breaking change.
    v0.10.1 is not pinned in specs/ (the design keeps v0.10.0); the file is read from the git tag."""
    check_oasdiff()
    rd = cache / "QualityOnDemand"
    data = subprocess.run(["git", "-C", str(rd), "show", "v0.10.1:code/API_definitions/qod-api.yaml"], check=True, capture_output=True).stdout
    with tempfile.NamedTemporaryFile("wb", suffix=".yaml", delete=False) as t:
        t.write(data)
    a = str(SPECS / "L3" / "v0.10.0.yaml")
    br = _oasdiff("breaking", a, t.name)
    row = dict(api="L3", from_version="v0.10.0", to_version="v0.10.1", tag_commit=_git(rd, "rev-parse", "v0.10.1^{commit}"),
               sha256=sha256(data), all_changes=len(_oasdiff("changelog", a, t.name)),
               breaking_err=sum(1 for x in br if x.get("level") == 3), breaking_warn=sum(1 for x in br if x.get("level") == 2))
    RESULTS.mkdir(parents=True, exist_ok=True)
    with open(RESULTS / "breaking_patch_v0.10.1.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        w.writeheader()
        w.writerow(row)
    print(row)


# ---------------------------------------------------------------- excerpts

def _resolve(node, root, seen=()):
    """Inline local $refs (cycles are cut with a marker)."""
    if isinstance(node, dict):
        if "$ref" in node and isinstance(node["$ref"], str) and node["$ref"].startswith("#/"):
            ref = node["$ref"]
            if ref in seen:
                return {"description": f"(recursive reference to {ref.split('/')[-1]})"}
            target = root
            for part in ref[2:].split("/"):
                target = target[part.replace("~1", "/").replace("~0", "~")]
            out = _resolve(copy.deepcopy(target), root, seen + (ref,))
            extra = {k: _resolve(v, root, seen) for k, v in node.items() if k != "$ref"}
            if isinstance(out, dict):
                out = {**out, **extra}
            return out
        out = {k: _resolve(v, root, seen) for k, v in node.items()}
        disc = node.get("discriminator")
        if isinstance(disc, dict) and disc.get("mapping") and "oneOf" not in node:
            # discriminator mappings are plain strings, so the subtypes (e.g. Circle) would be lost
            subtypes = {key: _resolve({"$ref": ref}, root, seen) for key, ref in disc["mapping"].items() if ref.startswith("#/")}
            for sub in subtypes.values():  # drop the cut-off back-reference to the base schema
                if isinstance(sub.get("allOf"), list):
                    sub["allOf"] = [x for x in sub["allOf"] if not str(x.get("description", "")).startswith("(recursive reference")]
            out["x-discriminator-subtypes"] = subtypes
        return out
    if isinstance(node, list):
        return [_resolve(v, root, seen) for v in node]
    return node


def _wanted(api: str, path: str, method: str, op: dict) -> bool:
    text = (path + " " + op.get("operationId", "")).lower()
    if api == "L1":
        return method == "post" and ("reachab" in text or "connectiv" in text or path.endswith("/retrieve"))
    if api == "L2":
        return method == "post" and "verify" in text
    if api == "L3":
        # create (POST /sessions), get and delete (/sessions/{sessionId}); no extend, retrieve-sessions or list
        if path.endswith("/sessions"):
            return method == "post"
        if path.endswith("/sessions/{sessionId}"):
            return method in {"get", "delete"}
        return False
    raise ValueError(api)


def _callback_summary(op: dict, doc: dict) -> dict:
    """Callback URL expressions of an operation with the summary line only, no payload schema (07b A12).

    The expression says where the server delivers notifications, for example `{$request.body#/sink}`: it is the
    only place where a version's use of the notification URL field is visible.
    """
    out: dict = {}
    for name, expressions in (op.get("callbacks") or {}).items():
        entry: dict = {}
        for expr, item in expressions.items():
            if "$ref" in item:
                target = doc
                for part in item["$ref"][2:].split("/"):
                    target = target[part.replace("~1", "/").replace("~0", "~")]
                item = target
            summary = (item.get("post") or {}).get("summary")
            entry[expr] = {"post": {"summary": summary}} if summary else {}
        out[name] = entry
    return out


def make_excerpt(api: str, spec_file: Path) -> dict:
    doc = yaml.safe_load(spec_file.read_text())
    paths = {}
    for p, item in (doc.get("paths") or {}).items():
        ops = {}
        for m, op in item.items():
            if m in {"get", "post", "put", "delete", "patch"} and _wanted(api, p, m, op):
                callbacks = _callback_summary(op, doc)
                op = {k: v for k, v in op.items() if k not in {"callbacks", "security"}}
                op = _resolve(op, doc)
                if callbacks:
                    op["callbacks"] = callbacks
                ops[m] = op
        if ops:
            paths[p] = ops
    if api == "L1" and not paths:
        raise RuntimeError(f"no L1 operations found in {spec_file}")
    out = {"openapi": doc["openapi"], "info": {"title": doc["info"]["title"], "version": doc["info"]["version"]}, "paths": paths}
    if "servers" in doc:
        out["servers"] = doc["servers"]
    return out


def excerpts() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    rows = []
    for api, c in VERSIONS.items():
        for v, _, _ in c["versions"]:
            ex = make_excerpt(api, SPECS / api / f"{v}.yaml")
            text = yaml.safe_dump(ex, sort_keys=False, allow_unicode=True, width=120)
            out = SPECS / "excerpts" / api / f"{v}.yaml"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text)
            rows.append(dict(api=api, version=v, operations=sum(len(x) for x in ex["paths"].values()), chars=len(text), approx_tokens=len(text) // 4))
    # QoS Profiles API at the server version: the server agent's profile lookup (kept apart from the L3 excerpts)
    for _, name, v, _, _ in EXTRA:
        ex = make_profile_excerpt(SPECS / "L3" / f"{name}-{v}.yaml")
        text = yaml.safe_dump(ex, sort_keys=False, allow_unicode=True, width=120)
        (SPECS / "excerpts" / "L3" / f"{name}-{v}.yaml").write_text(text)
        rows.append(dict(api="L3", version=f"{name}-{v}", operations=sum(len(x) for x in ex["paths"].values()), chars=len(text), approx_tokens=len(text) // 4))
    with open(RESULTS / "excerpt_sizes.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["api", "version", "operations", "chars", "approx_tokens"])
        w.writeheader()
        w.writerows(rows)
    print("wrote", len(rows), "excerpts")


# ---------------------------------------------------------------- prompt excerpts (stage 03b, speed-up 2)
SERIALISATIONS = {"json": "json", "yaml": "yaml"}
PROMPT_DIR = SPECS / "excerpts_prompt"


def strip_examples(node, in_properties: bool = False):
    """Drop `example` / `examples` keywords everywhere (a *property* called `example` is kept); descriptions stay."""
    if isinstance(node, dict):
        return {k: strip_examples(v, k == "properties") for k, v in node.items()
                if in_properties or k not in ("example", "examples")}
    if isinstance(node, list):
        return [strip_examples(v) for v in node]
    return node


def serialise(doc: dict, how: str) -> str:
    if how == "json":
        return json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=120)


def prompt_excerpts() -> list[tuple[str, str, dict]]:
    """Write specs/excerpts_prompt/<api>/<version>.{json,yaml} from the reference excerpts. Returns (api, version, doc)."""
    out = []
    for api, c in VERSIONS.items():
        for v, _, _ in c["versions"]:
            doc = strip_examples(yaml.safe_load((SPECS / "excerpts" / api / f"{v}.yaml").read_text()))
            (PROMPT_DIR / api).mkdir(parents=True, exist_ok=True)
            for how, ext in SERIALISATIONS.items():
                (PROMPT_DIR / api / f"{v}.{ext}").write_text(serialise(doc, how))
            out.append((api, v, doc))
    return out


def make_profile_excerpt(spec_file: Path) -> dict:
    doc = yaml.safe_load(spec_file.read_text())
    paths = {}
    for p, item in doc["paths"].items():
        ops = {m: _resolve({k: v for k, v in op.items() if k not in {"security"}}, doc) for m, op in item.items() if m in {"get", "post"}}
        if ops:
            paths[p] = ops
    return {"info": {"title": doc["info"]["title"], "version": doc["info"]["version"]}, "paths": paths}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("fetch", "all"):
        fetch()
    if cmd in ("diff", "all"):
        diff()
    if cmd == "prompt":
        prompt_excerpts()
    if cmd == "patch":
        patch_check()
    if cmd in ("excerpts", "all"):
        excerpts()
