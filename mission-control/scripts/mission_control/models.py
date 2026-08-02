"""Shared value validation and state-machine constants."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 2
BLAST_ORDER = ("low", "medium", "high", "critical")
COMPLEXITIES = ("low", "medium", "high")
TRACKS = ("express", "standard", "full")
SPEED_PREFERENCES = ("thorough", "balanced", "fast")
MERGE_STATES = (
    "merge-pending",
    "merging",
    "merge-conflict",
    "post-merge-verifying",
)
TRANSITIONS = {
    "backlog": ("researching", "approved"),
    "researching": ("plan-review",),
    "plan-review": (
        "orchestrator-approval", "approved", "researching", "blocked",
    ),
    "orchestrator-approval": ("approved", "researching", "blocked"),
    "approved": ("building",),
    "building": ("verifying", "blocked"),
    "verifying": ("code-review", "merge-pending", "building", "blocked"),
    "code-review": ("merge-pending", "building", "blocked"),
    "merge-pending": ("merging", "blocked"),
    "merging": ("merge-conflict", "post-merge-verifying", "merge-pending",
                "blocked"),
    "merge-conflict": ("merging", "merge-pending", "blocked"),
    "post-merge-verifying": ("done", "merge-conflict", "merge-pending"),
    "blocked": ("approved", "researching", "merge-pending"),
    "done": (),
}
BOUNCES = {
    ("plan-review", "researching"),
    ("orchestrator-approval", "researching"),
    ("verifying", "building"),
    ("code-review", "building"),
}
GATE_EVIDENCE = {
    "researching": "research.md",
    "plan-review": "plan-review.json",
    "orchestrator-approval": "approval.json",
    "building": "handoff.md",
    "verifying": "verify.json",
    "code-review": "code-review.json",
}


class StateConflict(ValueError):
    """An optimistic update lost a race or observed a different state."""


class LeaseConflict(ValueError):
    """A requested lease conflicts with an existing lease."""

    def __init__(self, conflicts: list[tuple[dict[str, Any], dict[str, Any]]]):
        self.conflicts = conflicts
        super().__init__("one or more lease targets conflict")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def classify_risk(blast: str, complexity: str, concurrency: bool) -> str:
    """Collapse routing signals into low/medium/high risk.

    High risk is any single strong signal; low risk requires every signal to be
    benign.  Concurrency is always high because shared mutable state cannot be
    graded mechanically.
    """
    if blast in ("high", "critical") or complexity == "high" or concurrency:
        return "high"
    if blast == "low" and complexity == "low" and not concurrency:
        return "low"
    return "medium"


def recommend_track(
    blast: str, complexity: str, concurrency: bool, speed: str,
) -> tuple[str, str, str]:
    """Return (track, risk, rationale) for an item.

    The track scales ceremony to risk first and speed second.  A speed request
    can only *lower* ceremony inside the safe envelope; it never overrides a
    risk-driven floor, which is how the orchestrator pushes back on unwise
    fast-tracking.
    """
    risk = classify_risk(blast, complexity, concurrency)
    if risk == "high":
        drivers = []
        if blast in ("high", "critical"):
            drivers.append(f"blast_radius={blast}")
        if complexity == "high":
            drivers.append("complexity=high")
        if concurrency:
            drivers.append("concurrency")
        reason = (
            "high risk (" + ", ".join(drivers) + ") requires full ceremony: "
            "research, plan review, and code review")
        if speed == "fast":
            reason += "; speed request declined — correctness dominates here"
        return "full", risk, reason
    if risk == "low":
        if speed == "thorough":
            return (
                "standard", risk,
                "low risk, but thorough posture keeps the plan-review gate")
        detail = ("fast" if speed == "fast" else "balanced default")
        return (
            "express", risk,
            f"low-risk mechanical change ({detail}); express track — plan and "
            "code review skipped, mechanical gates still apply")
    if speed == "fast":
        return (
            "standard", risk,
            "medium risk; express declined, standard track is the safe floor")
    if speed == "thorough":
        return (
            "full", risk,
            "medium risk with thorough posture; full ceremony")
    return "standard", risk, "medium risk; standard track"


def route_snapshot(
    blast: str, complexity: str, concurrency: bool, speed: str, *,
    source: str,
) -> dict[str, Any]:
    if blast not in BLAST_ORDER:
        raise ValueError(f"invalid blast radius: {blast}")
    if complexity not in COMPLEXITIES:
        raise ValueError(f"invalid complexity: {complexity}")
    if not isinstance(concurrency, bool):
        raise ValueError("concurrency must be boolean")
    if speed not in SPEED_PREFERENCES:
        raise ValueError(f"invalid speed preference: {speed}")
    track, risk, rationale = recommend_track(
        blast, complexity, concurrency, speed)
    return {
        "track": track,
        "risk": risk,
        "blast_radius": blast,
        "complexity": complexity,
        "concurrency": concurrency,
        "speed_preference": speed,
        "source": source,
        "rationale": rationale,
        "decided_at": now(),
    }


def validate_id(value: str, field: str = "id") -> str:
    if not isinstance(value, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
        raise ValueError(
            f"{field} must use only letters, digits, '.', '_', and '-'")
    return value


def parse_time(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def parse_bool(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in ("true", "false"):
        return value.lower() == "true"
    raise ValueError(f"{field} must be true or false")


def normalize_path(raw: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("paths must be non-empty strings")
    value = raw.strip().replace("\\", "/")
    if re.match(r"^[A-Za-z]:", value) or value.startswith("/"):
        raise ValueError(f"path must be repo-relative, not absolute: {raw}")
    parts: list[str] = []
    for part in value.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise ValueError(f"path may not traverse outside the repo: {raw}")
        parts.append(part)
    if not parts:
        raise ValueError(f"path must identify a repo child: {raw}")
    normalized = "/".join(parts)
    return normalized.casefold() if os.name == "nt" else normalized


def ensure_repo_child(repo: Path, raw: str) -> str:
    path = normalize_path(raw)
    try:
        (repo / path).resolve().relative_to(repo.resolve())
    except ValueError as exc:
        raise ValueError(f"path resolves outside the repository: {raw}") from exc
    return path


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bytes_hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def json_text(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def public_record(value: dict[str, Any], version: int) -> dict[str, Any]:
    result = dict(value)
    result["version"] = version
    return result


def remove_tree(path: Path) -> None:
    """Remove a private tree deterministically, including read-only Git files."""
    if not path.exists():
        return
    for child in sorted(path.rglob("*"), key=lambda value: len(value.parts),
                        reverse=True):
        if child.is_symlink():
            continue
        try:
            mode = stat.S_IRUSR | stat.S_IWUSR
            if child.is_dir():
                mode |= stat.S_IXUSR
            child.chmod(mode)
        except OSError:
            pass
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    except OSError:
        pass
    shutil.rmtree(path)
