"""The world the mock backends serve (stage 04): devices, locations, QoS profiles, QoD sessions.

The files are in config/world/ and are hashed at the freeze (`world_hash`). Nothing here is random:
the same files and the same clock always give the same answers.
"""
from __future__ import annotations

import hashlib
import ipaddress
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORLD_DIR = ROOT / "config" / "world"
WORLD_FILES = ("devices.yaml", "qos_profiles.yaml", "service.yaml", "sessions.yaml")

REACHABILITY_STATES = ("DATA_SMS", "DATA_ONLY", "SMS_ONLY", "NONE")
PROFILE_STATUSES = ("ACTIVE", "INACTIVE", "DEPRECATED")


def parse_ts(text: str) -> datetime:
    """RFC 3339 with time zone, as used for clocks."""
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


def fmt_ts(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class Location:
    city: str
    latitude: float
    longitude: float
    accuracy_m: float
    age_s: int
    fresh_available: bool


@dataclass(frozen=True)
class Device:
    id: str
    phone_number: str
    public_address: str
    public_port: int
    private_address: str
    ipv6_address: str
    ipv6_prefix: str
    network_access_identifier: str
    reach_state: str
    status_age_s: int
    location: Location | None


@dataclass(frozen=True)
class Profile:
    name: str
    status: str
    min_duration_s: int
    max_duration_s: int
    description: str


@dataclass(frozen=True)
class WorldSession:
    id: str
    device_id: str
    application_server: dict[str, str]
    qos_profile: str
    duration_s: int
    started_ago_s: int
    qos_status: str
    status_info: str | None
    device_ports: dict | None
    application_server_ports: dict | None
    sink: str | None


def world_hash(world_dir: Path = WORLD_DIR) -> str:
    """SHA-256 of the canonical file set: names and bytes, in sorted order (manifest `world_hash`)."""
    h = hashlib.sha256()
    for name in sorted(WORLD_FILES):
        h.update(name.encode() + b"\0" + (world_dir / name).read_bytes() + b"\0")
    return h.hexdigest()


class World:
    def __init__(self, world_dir: Path = WORLD_DIR):
        self.dir = Path(world_dir)
        load = lambda n: yaml.safe_load((self.dir / n).read_text())  # noqa: E731
        svc = load("service.yaml")
        self.service: dict[str, Any] = svc
        self.clock_default = parse_ts(svc["clock_default"])
        self.ports: dict[str, int] = dict(svc["ports"])
        self.unsupported_identifiers: set[str] = set(svc["unsupported_identifiers"])
        self.location_rules: dict[str, Any] = svc["location"]

        self.devices: list[Device] = []
        for d in load("devices.yaml")["devices"]:
            loc = d["location"]
            self.devices.append(Device(
                id=d["id"], phone_number=d["phone_number"],
                public_address=d["ipv4"]["public_address"], public_port=d["ipv4"]["public_port"],
                private_address=d["ipv4"]["private_address"],
                ipv6_address=d["ipv6"]["address"], ipv6_prefix=d["ipv6"]["prefix"],
                network_access_identifier=d["network_access_identifier"],
                reach_state=d["reachability"]["state"], status_age_s=d["reachability"]["last_status_age_s"],
                location=None if loc is None else Location(
                    loc["city"], loc["latitude"], loc["longitude"], loc["accuracy_m"],
                    loc["last_location_age_s"], loc["fresh_available"]),
            ))
        self.profiles: dict[str, Profile] = {
            p["name"]: Profile(p["name"], p["status"], p["min_duration_s"], p["max_duration_s"], p["description"])
            for p in load("qos_profiles.yaml")["profiles"]}
        self.sessions: dict[str, WorldSession] = {
            s["id"]: WorldSession(
                id=s["id"], device_id=s["device"], application_server=s["application_server"],
                qos_profile=s["qos_profile"], duration_s=s["duration_s"], started_ago_s=s["started_ago_s"],
                qos_status=s["qos_status"], status_info=s.get("status_info"),
                device_ports=s.get("device_ports"), application_server_ports=s.get("application_server_ports"),
                sink=s.get("sink"))
            for s in load("sessions.yaml")["sessions"]}
        self._by_id = {d.id: d for d in self.devices}
        self._by_phone = {d.phone_number: d for d in self.devices}
        self._by_nai = {d.network_access_identifier: d for d in self.devices}
        self.hash = world_hash(self.dir)

    # --- lookups -----------------------------------------------------------------------------
    def device(self, device_id: str) -> Device:
        return self._by_id[device_id]

    def by_phone(self, number: str) -> Device | None:
        return self._by_phone.get(number)

    def by_ipv4(self, public_address: str, public_port: int | None, private_address: str | None) -> Device | None:
        """Every component that the request gives must match (public address, plus port and/or private address)."""
        for d in self.devices:
            if d.public_address != public_address:
                continue
            if public_port is not None and d.public_port != public_port:
                continue
            if private_address is not None and d.private_address != private_address:
                continue
            return d
        return None

    def by_ipv6(self, address: str) -> Device | None:
        """Any address inside the device's /64 identifies it (IPv6 schema description)."""
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            return None
        for d in self.devices:
            if ip in ipaddress.ip_network(d.ipv6_prefix):
                return d
        return None

    # --- sanity ------------------------------------------------------------------------------
    def check(self) -> list[str]:
        """Return a list of problems with the world files (empty when they are consistent)."""
        problems: list[str] = []
        nets = {k: ipaddress.ip_network(self.service[k]) for k in
                ("ipv4_public_range", "ipv4_private_range", "ipv4_application_server_range", "ipv6_range")}
        ids = [d.id for d in self.devices]
        if len(set(ids)) != len(ids):
            problems.append("duplicate device ids")
        for key, attr in (("phone", "phone_number"), ("nai", "network_access_identifier"), ("ipv6", "ipv6_prefix")):
            vals = [getattr(d, attr) for d in self.devices]
            if len(set(vals)) != len(vals):
                problems.append(f"duplicate {key}")
        if len({(d.public_address, d.public_port) for d in self.devices}) != len(self.devices):
            problems.append("duplicate public address and port")
        for d in self.devices:
            if not d.phone_number.startswith(self.service["phone_number_prefix"]):
                problems.append(f"{d.id}: phone number outside the documented range")
            if ipaddress.ip_address(d.public_address) not in nets["ipv4_public_range"]:
                problems.append(f"{d.id}: public address outside {nets['ipv4_public_range']}")
            if ipaddress.ip_address(d.private_address) not in nets["ipv4_private_range"]:
                problems.append(f"{d.id}: private address outside {nets['ipv4_private_range']}")
            if ipaddress.ip_address(d.ipv6_address) not in nets["ipv6_range"]:
                problems.append(f"{d.id}: IPv6 address outside {nets['ipv6_range']}")
            if ipaddress.ip_address(d.ipv6_address) not in ipaddress.ip_network(d.ipv6_prefix):
                problems.append(f"{d.id}: IPv6 address outside its own prefix")
            if d.reach_state not in REACHABILITY_STATES:
                problems.append(f"{d.id}: bad reachability state {d.reach_state}")
        for p in self.profiles.values():
            if p.status not in PROFILE_STATUSES:
                problems.append(f"{p.name}: bad status {p.status}")
            if not 0 < p.min_duration_s <= p.max_duration_s:
                problems.append(f"{p.name}: bad duration limits")
        for s in self.sessions.values():
            if s.device_id not in self._by_id:
                problems.append(f"session {s.id}: unknown device {s.device_id}")
            if s.qos_profile not in self.profiles:
                problems.append(f"session {s.id}: unknown profile {s.qos_profile}")
            if s.qos_status == "AVAILABLE" and s.started_ago_s >= s.duration_s:
                problems.append(f"session {s.id}: AVAILABLE but already expired at the default clock")
        return problems

    def expires_at(self, s: WorldSession, clock: datetime) -> datetime:
        return clock - timedelta(seconds=s.started_ago_s) + timedelta(seconds=s.duration_s)
