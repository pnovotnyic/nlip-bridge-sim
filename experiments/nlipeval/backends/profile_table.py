"""The QoS profile table for the L3 server prompt (stage 04, step 1; stage 03b B3).

An operator's agent knows its own catalogue. The table is rendered from `config/world/qos_profiles.yaml`,
the same file the L3 backend reads, so the table and the backend can never disagree.

    name | status | min duration | max duration | description
"""
from __future__ import annotations

from nlipeval.backends.world import Profile, World

HEADER = "name | status | min duration | max duration | description"


def human_duration(seconds: int) -> str:
    for unit, size in (("d", 86400), ("h", 3600), ("min", 60)):
        if seconds % size == 0:
            return f"{seconds // size} {unit} ({seconds} s)"
    return f"{seconds} s"


def render_row(p: Profile) -> str:
    return " | ".join([p.name, p.status, human_duration(p.min_duration_s), human_duration(p.max_duration_s),
                       p.description])


def render_profile_table(world: World | None = None) -> str:
    world = world or World()
    return "\n".join([HEADER, *(render_row(p) for p in world.profiles.values())])


if __name__ == "__main__":
    print(render_profile_table())
