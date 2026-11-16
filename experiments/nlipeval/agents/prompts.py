"""Prompt rendering for the client and server agents (stage 06).

`render_client(task, prompt_type)` → system prompt string
`render_server(api, server_version, prompt_type, condition)` → system prompt string

Also provides:
- `prompts_hash()` → SHA-256 of all template files, stable across a run
- token sizes of the rendered prompts are measured in `nlipeval/agents/prompt_sizes.py`
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from nlipeval.agents.schemas import CLIENT_SCHEMA, SERVER_SCHEMA

ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = ROOT / "prompts"
SPECS_DIR = ROOT / "specs" / "excerpts_prompt"
NOTES_DIR = PROMPTS_DIR / "notes"


# --------------------------------------------------------------------------- template loading

def _load_template(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def _load_excerpt(api: str, version: str) -> str:
    """Return the prompt excerpt (JSON) for a given API version. A missing file is an error."""
    p = SPECS_DIR / api / f"{version}.json"
    if not p.exists():
        raise FileNotFoundError(f"No prompt excerpt for {api} {version}: {p}")
    return p.read_text(encoding="utf-8")


def notes_path(api: str, version: str) -> Path:
    return NOTES_DIR / api / f"{version}.md"


def _load_notes(api: str, version: str) -> str:
    """P3 notes for one version. A missing notes file is an error."""
    p = notes_path(api, version)
    if not p.exists():
        raise FileNotFoundError(f"No P3 notes for {api} {version}: {p}")
    return p.read_text(encoding="utf-8").strip() + "\n"


# --------------------------------------------------------------------------- schema rendering

def _schema_str(schema: dict) -> str:
    return json.dumps(schema, indent=2)


# --------------------------------------------------------------------------- client prompt

def render_client(task: dict, prompt_type: str, condition: str = "NLIP") -> str:
    """Render the full system prompt for the client agent.

    Args:
        task: a loaded task instance dict.
        prompt_type: "P1", "P2", "P3".
        condition: "NLIP" or "NLIP-0".
    """
    api = task["api"]
    client_version = task["client_version"]
    excerpt = _load_excerpt(api, client_version)

    if condition == "NLIP-0":
        template_name = "client_NLIP0.txt"
    else:
        template_name = f"client_{prompt_type}.txt"

    template = _load_template(template_name)

    facts = task.get("client_facts") or []
    if facts:
        facts_text = "\n".join(f"- {f['fact']}: {f['value']}" for f in facts)
    else:
        facts_text = "(none)"

    subs: dict[str, str] = {
        "api": api,
        "client_version": client_version,
        "excerpt": excerpt,
        "intent_text": task["intent_text"],
        "native_request": json.dumps(task["client_native_request"], indent=2),
        "client_facts": facts_text,
        "answer_schema": _schema_str(task["client_answer_schema"]),
        "client_schema": _schema_str(CLIENT_SCHEMA),
    }

    if prompt_type == "P3" and condition != "NLIP-0":
        subs["notes"] = _load_notes(api, client_version)

    return template.format(**subs)


# --------------------------------------------------------------------------- server prompt

def render_server(
    api: str,
    server_version: str,
    prompt_type: str,
    condition: str = "NLIP",
    world: Any | None = None,
) -> str:
    """Render the full system prompt for the server agent.

    Args:
        api: "L1", "L2", "L3".
        server_version: e.g. "v1.0.0".
        prompt_type: "P1", "P2", "P3".
        condition: "NLIP" or "NLIP-0".
        world: an optional `World` instance for the L3 profile table.
    """
    excerpt = _load_excerpt(api, server_version)

    if condition == "NLIP-0":
        template_name = "server_NLIP0.txt"
    else:
        template_name = f"server_{prompt_type}.txt"

    template = _load_template(template_name)

    # L3 gets the QoS profile table in place of a live call to the Profiles API
    if api == "L3":
        from nlipeval.backends.profile_table import render_profile_table
        table = render_profile_table(world)
        profile_table_section = f"## QoS profile table\n\n{table}\n\n"
    else:
        profile_table_section = ""

    subs: dict[str, str] = {
        "api": api,
        "server_version": server_version,
        "excerpt": excerpt,
        "profile_table_section": profile_table_section,
        "server_schema": _schema_str(SERVER_SCHEMA),
    }

    if prompt_type == "P3" and condition != "NLIP-0":
        subs["notes"] = _load_notes(api, server_version)

    return template.format(**subs)


# --------------------------------------------------------------------------- prompts hash

def prompts_hash() -> str:
    """SHA-256 of all template files in prompts/ (sorted), plus the rendered notes (not *.sources.md)."""
    h = hashlib.sha256()
    files: list[Path] = []
    for p in sorted(PROMPTS_DIR.glob("*.txt")):
        files.append(p)
    if NOTES_DIR.exists():
        for p in sorted(NOTES_DIR.rglob("*.md")):
            if not p.name.endswith(".sources.md"):   # sources are not rendered into any prompt
                files.append(p)
    for p in files:
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()
