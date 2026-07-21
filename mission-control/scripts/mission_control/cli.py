#!/usr/bin/env python3
"""Mission Control transactional command workflows.

SQLite is canonical state.  The CLI composes evidence, semantic leasing,
sandbox, Git worktree, and merge-coordinator modules; JSON files are explicit
read-only compatibility exports.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from mission_control.evidence import (
    record_gate_baseline,
    research_header,
    seal_gate_evidence,
    sealed_record,
    validate_code_review,
    validate_diagnosis,
    validate_handoff,
    validate_merge_artifact,
    validate_mission,
    validate_research,
    validate_review_json,
    validate_sandbox,
    validate_sealed_evidence,
    validate_verify,
)
from mission_control.merge import (
    MergeCoordinator,
    RefCASRetry,
    current_target_ref,
    git,
)
from mission_control.models import (
    BLAST_ORDER,
    BOUNCES,
    GATE_EVIDENCE,
    MERGE_STATES,
    TRANSITIONS,
    LeaseConflict,
    StateConflict,
    ensure_repo_child,
    file_hash,
    normalize_path,
    now,
    parse_time,
    validate_id,
)
from mission_control.sandbox import SandboxManager
from mission_control.semantic import (
    SemanticRegistry,
    canonical_target,
    parse_target_json,
    target_covers,
    targets_conflict,
    validate_committed_scope,
)
from mission_control.store import MissionStore


def die(message: str, code: int = 1) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True, capture_output=True,
    )
    if result.returncode:
        raise ValueError("this command must run inside a Git repository")
    return Path(result.stdout.strip()).resolve()


def store_for(args: argparse.Namespace) -> MissionStore:
    return MissionStore(args.root)


def _default_mission(goal: str | None) -> dict[str, Any]:
    build, test = None, None
    if Path("package.json").exists():
        build, test = "npm run build --if-present", "npm test"
    elif Path("Cargo.toml").exists():
        build, test = "cargo build", "cargo test"
    elif Path("CMakeLists.txt").exists():
        build = "cmake -B build && cmake --build build"
        test = "ctest --test-dir build"
    elif Path("pytest.ini").exists() or Path("requirements.txt").exists():
        build, test = f'"{sys.executable}" -m compileall -q .', "pytest"
    return {
        "goal": goal or "TODO: configure the mission goal",
        "created": now(),
        "state": {
            "backend": "sqlite",
            "journal_mode": "WAL",
            "busy_timeout_ms": 10000,
        },
        "terminal_conditions": {
            "backlog_drained": True,
            "max_items_completed": None,
            "token_budget": None,
            "deadline": None,
        },
        "concurrency": {
            "implementers": 2, "scouts": 2, "investigators": 1,
        },
        "throughput": {
            "maximize": False, "decided_by": "user", "reason": None,
        },
        "lease_ttl_minutes": 90,
        "bounce_limit": 3,
        "semantic": {"python_adapter": "stdlib-ast", "fallback": "file"},
        "execution": {
            "backend": "auto",
            "image": None,
            "native_fallback": True,
            "network": "none",
            "read_only_root": True,
            "resources": {"cpus": 2, "memory": "2g", "pids": 256},
            "commands": None,
            "artifact_paths": [],
        },
        "merge": {
            "target_ref": None,
            "max_cas_retries": 3,
            "require_resolution_review": True,
        },
        "repo_oracle": {"build": build, "test": test, "lint": None},
        "gates": {
            "orchestrator_approval_min_blast": "high",
            "code_review_min_blast": "medium",
        },
    }


def cmd_init(args: argparse.Namespace) -> None:
    mission = _default_mission(args.goal)
    MissionStore.initialize(args.root, mission)
    print(
        f"initialized {args.root} with canonical SQLite/WAL state; "
        "use configure, then export-json for compatibility snapshots")


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def cmd_configure(args: argparse.Namespace) -> None:
    store = store_for(args)
    if bool(args.json) == bool(args.file):
        raise ValueError("configure requires exactly one of --json or --file")
    raw = args.json if args.json else Path(args.file).read_text(encoding="utf-8")
    try:
        patch = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"configuration is not valid JSON: {exc}") from exc
    if not isinstance(patch, dict):
        raise ValueError("configuration patch must be a JSON object")
    current = store.document("mission")
    replacement = _deep_merge(current.data, patch)
    validate_mission(replacement)
    store.update_document(
        "mission", replacement, current.version, action="configure")
    print("mission configuration updated transactionally")


def cmd_migrate_state(args: argparse.Namespace) -> None:
    root = Path(args.root)
    existed = (root / "state.db").exists()
    store = MissionStore(root)
    info = store.migration_info()
    if existed:
        print(
            f"state.db already at schema {info.get('schema_version')}; "
            "migration is idempotent")
    else:
        print(
            f"migrated JSON state to SQLite; backup: "
            f"{info.get('migration_backup')}")


def cmd_export_json(args: argparse.Namespace) -> None:
    paths = store_for(args).export_json(force=args.force)
    print(f"exported {len(paths)} compatibility snapshot(s)")


def _terminal_stop_reasons(store: MissionStore) -> list[str]:
    mission = store.document("mission").data
    validate_mission(mission)
    items = store.rows("queue_items")
    done = sum(item["state"] == "done" for item in items)
    tokens = sum(
        history.get("tokens", 0)
        for item in items for history in item.get("history", [])
    )
    conditions = mission["terminal_conditions"]
    reasons = []
    maximum = conditions.get("max_items_completed")
    if maximum is not None and done >= maximum:
        reasons.append("max_items_completed")
    budget = conditions.get("token_budget")
    if budget is not None and tokens >= budget:
        reasons.append("token_budget")
    deadline = conditions.get("deadline")
    if deadline and datetime.now(timezone.utc) >= parse_time(
            deadline, "terminal_conditions.deadline"):
        reasons.append("deadline")
    return reasons


def _require_spawning(store: MissionStore, action: str) -> None:
    reasons = _terminal_stop_reasons(store)
    if reasons:
        raise ValueError(
            f"cannot {action}: terminal condition reached "
            f"({', '.join(reasons)})")


def cmd_add_item(args: argparse.Namespace) -> None:
    store = store_for(args)
    validate_id(args.id, "backlog id")
    if not (
            args.origin in ("architect", "user") or re.fullmatch(
                r"(?:escalation|split|investigation):"
                r"[A-Za-z0-9][A-Za-z0-9._-]*", args.origin)):
        raise ValueError(
            "--origin must be architect, user, or "
            "escalation:<id>/split:<id>/investigation:<id>")
    store.add_backlog_item({
        "id": args.id,
        "title": args.title,
        "priority": args.priority,
        "depends_on": args.depends_on or [],
        "ui": args.ui,
        "fast_track": args.fast_track,
        "constraints": args.constraint or [],
        "origin": args.origin,
        "status": "open",
    })
    print(f"added {args.id} (priority {args.priority})")


def cmd_claim(args: argparse.Namespace) -> None:
    store = store_for(args)
    _require_spawning(store, f"claim {args.id}")
    backlog = store.backlog_item(args.id)
    if backlog.data["status"] != "open":
        raise ValueError(
            f"{args.id} is {backlog.data['status']}, not open")
    state = "approved" if backlog.data.get("fast_track") else "researching"
    evidence = store.evidence_dir(args.id)
    evidence.mkdir(parents=True, exist_ok=True)
    item = {
        "id": args.id,
        "state": state,
        "ui": backlog.data.get("ui", False),
        "history": [{"state": state, "at": now()}],
    }
    record_gate_baseline(item, state, evidence)
    store.claim_item(args.id, backlog.version, item)
    print(f"{args.id}: backlog -> {state} (evidence: {evidence})")


def _blocked_origin(item: dict[str, Any]) -> str | None:
    if item.get("blocked_from"):
        return item["blocked_from"]
    history = item.get("history", [])
    if history and history[-1].get("state") == "blocked" and len(history) > 1:
        return history[-2].get("state")
    return None


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _research(
    store: MissionStore, item_id: str, item: dict[str, Any],
    fast_track: bool, *, current: str,
) -> dict[str, Any]:
    if fast_track:
        return {}
    return validate_research(
        store.evidence_dir(item_id), item_id, item,
        require_fresh=current == "researching",
    )


def _worktree_tip(item: dict[str, Any]) -> tuple[Path, str, str]:
    path_value, base = item.get("worktree"), item.get("base_commit")
    if not path_value or not base:
        raise ValueError("item has no recorded worktree/base commit")
    path = Path(path_value)
    count = git(
        path, ["rev-list", "--count", f"{base}..HEAD"], check=False)
    if count.returncode or int(count.stdout.strip() or "0") < 1:
        raise ValueError(
            "verification requires at least one committed diff from the "
            "worktree base")
    tip = git(path, ["rev-parse", "HEAD"]).stdout.strip()
    return path, base, tip


def _semantic_scope_for_item(
    store: MissionStore, item: dict[str, Any],
) -> dict[str, Any]:
    worktree, base, tip = _worktree_tip(item)
    leases = store.leases(item["id"])
    report = validate_committed_scope(worktree, base, tip, leases)
    report.update({"item": item["id"], "timestamp": now()})
    path = store.evidence_dir(item["id"]) / "semantic-scope.json"
    _write_json(path, report)
    if report["verdict"] != "green":
        labels = [
            f"{target['path']}::{target['type']}::"
            f"{target.get('qualified_symbol') or '*'}"
            for target in report["uncovered_targets"]
        ]
        raise ValueError(
            "committed diff contains semantic targets outside the lease: "
            + ", ".join(labels))
    return report


def _expected_targets(
    store: MissionStore, item_id: str, header: dict[str, Any],
    fast_track: bool,
) -> list[dict[str, Any]]:
    if fast_track:
        return []
    values = header.get("lease_targets") or []
    if values:
        return [parse_target_json(raw) for raw in values]
    return [{
        "path": normalize_path(path),
        "type": "file",
        "qualified_symbol": None,
        "node_kind": "file",
        "base_blob": None,
        "base_commit": None,
        "structural_anchor_hash": None,
        "adapter": "touch-list-file-fallback",
    } for path in header["touch_list"]]


def cmd_transition(args: argparse.Namespace) -> None:
    store = store_for(args)
    mission = store.document("mission").data
    validate_mission(mission)
    versioned = store.queue_item(args.id)
    item = dict(versioned.data)
    current = item["state"]
    target = args.to
    if target == "ready-to-merge":
        print(
            "warning: ready-to-merge is deprecated; using merge-pending",
            file=sys.stderr,
        )
        target = "merge-pending"
    if target not in TRANSITIONS.get(current, ()):
        raise ValueError(
            f"illegal transition {current} -> {target} "
            f"(legal: {', '.join(TRANSITIONS.get(current, ())) or 'none'})")
    if args.tokens is not None and args.tokens < 0:
        raise ValueError("--tokens must be non-negative")
    origin = _blocked_origin(item)
    if current == "blocked":
        if target == "approved" and origin not in (
                "building", "verifying", "code-review"):
            raise ValueError(
                f"{args.id} was blocked from {origin or 'unknown'}; "
                "plan-side blocks must return to researching")
        if target == "merge-pending" and origin not in MERGE_STATES:
            raise ValueError(
                "only merge-side blocks may return to merge-pending")
    backlog = store.backlog_item(args.id)
    fast_track = bool(backlog.data.get("fast_track"))
    header = _research(
        store, args.id, item, fast_track, current=current)
    blast = header.get("blast_radius", "low")
    is_bounce = (current, target) in BOUNCES
    forward = target != "blocked"
    additional_seals: list[dict[str, str]] = []

    if forward:
        evidence_dir = store.evidence_dir(args.id)
        if current == "plan-review":
            validate_review_json(
                evidence_dir, args.id, item, "plan-review.json",
                "plan-review", "plan-reviewer",
                forward=target != "researching",
            )
        elif current == "orchestrator-approval":
            validate_review_json(
                evidence_dir, args.id, item, "approval.json",
                "orchestrator-approval", "orchestrator",
                forward=target != "researching",
            )
        elif current == "building":
            validate_handoff(evidence_dir, args.id, item)
            scope = _semantic_scope_for_item(store, item)
            item["implementation_commit"] = scope["result_commit"]
            item["leased_targets"] = [
                lease["target"] for lease in store.leases(args.id)]
            additional_seals.append({
                "file": "semantic-scope.json",
                "sha256": file_hash(evidence_dir / "semantic-scope.json"),
            })
        elif current == "verifying":
            forward_verify = target in ("code-review", "merge-pending")
            _, sandbox = validate_verify(
                evidence_dir, args.id, item, forward=forward_verify)
            if sandbox is not None:
                additional_seals.append({
                    "file": "sandbox.json",
                    "sha256": file_hash(evidence_dir / "sandbox.json"),
                })
        elif current == "code-review":
            validate_code_review(
                evidence_dir, args.id, item, header,
                forward=target == "merge-pending",
            )

    forced_block = None
    if is_bounce:
        limit = mission.get("bounce_limit", 3)
        prior = sum(
            bool(history.get("bounce")) for history in item["history"])
        if prior + 1 >= limit:
            forced_block = (
                f"bounce limit ({limit}) reached — orchestrator diagnosis "
                "required")
            target = "blocked"

    if target != "blocked":
        gates = mission["gates"]
        if current == "plan-review" and target == "approved" and \
                BLAST_ORDER.index(blast) >= BLAST_ORDER.index(
                    gates["orchestrator_approval_min_blast"]):
            raise ValueError(
                f"{args.id} blast_radius={blast} requires "
                "orchestrator-approval")
        if current == "verifying" and target == "merge-pending" and \
                BLAST_ORDER.index(blast) >= BLAST_ORDER.index(
                    gates["code_review_min_blast"]):
            raise ValueError(
                f"{args.id} blast_radius={blast} requires code-review")
        if target == "building":
            _require_spawning(store, f"start building {args.id}")
            if not (
                    mission["repo_oracle"].get("build") and
                    mission["repo_oracle"].get("test")):
                raise ValueError(
                    "repo_oracle.build/test unset — no oracle, no building")
            leases = store.leases(args.id)
            if not leases:
                raise ValueError(
                    f"{args.id} must hold leases before entering building")
            if not item.get("worktree"):
                raise ValueError(
                    f"{args.id} must have a worktree before entering building")
            expected = _expected_targets(
                store, args.id, header, fast_track)
            uncovered = [
                wanted for wanted in expected
                if not any(target_covers(lease["target"], wanted)
                           for lease in leases)
            ]
            if uncovered:
                raise ValueError(
                    f"{args.id} does not hold leases covering its touch_list/"
                    "research targets: "
                    + ", ".join(
                        f"{value['path']}::{value['type']}::"
                        f"{value.get('qualified_symbol') or '*'}"
                        for value in uncovered))
            item["leased_targets"] = [
                lease["target"] for lease in leases]
        if target == "merge-pending":
            target_ref = (mission.get("merge") or {}).get("target_ref")
            target_ref = target_ref or current_target_ref(repo_root())
            item["target_ref"] = target_ref
            item["target_head"] = git(
                repo_root(), ["rev-parse", target_ref]).stdout.strip()

    entry: dict[str, Any] = {"state": target, "at": now()}
    if forward:
        seals = seal_gate_evidence(
            item, current, entry, store.evidence_dir(args.id))
    else:
        seals = []
    if additional_seals:
        entry["additional_evidence"] = additional_seals
        seals.extend(additional_seals)
    if is_bounce:
        entry["bounce"] = True
    if forced_block:
        entry["reason"] = forced_block
    if args.blocked_on:
        entry["blocked_on"] = args.blocked_on
        item["blocked_on"] = args.blocked_on
    if args.tokens is not None:
        entry["tokens"] = args.tokens
    if args.note:
        entry["note"] = args.note
    if current == "blocked":
        item.pop("blocked_on", None)
        item.pop("blocked_from", None)
    if target == "blocked":
        item["blocked_from"] = current
    item["state"] = target
    item.setdefault("history", []).append(entry)
    record_gate_baseline(item, target, store.evidence_dir(args.id))
    store.update_queue_item(
        args.id, item, versioned.version, current,
        action="transition",
        detail={"from": current, "to": target, "forced": forced_block},
    )
    for seal in seals:
        store.seal_evidence(
            args.id, current, store.evidence_dir(args.id) / seal["file"])
    if target == "blocked":
        store.force_release_leases(args.id)
    message = f"{args.id}: {current} -> {target}"
    if forced_block:
        message += f" ({forced_block})"
    if target == "merge-pending":
        message += (
            f"\n{args.id}: automated merge queued; run merge prepare, then "
            "merge finalize")
    print(message)


def _file_target(path: str, diagnostic: str) -> dict[str, Any]:
    return canonical_target({
        "path": path,
        "type": "file",
        "qualified_symbol": None,
        "node_kind": "file",
        "base_blob": None,
        "base_commit": None,
        "structural_anchor_hash": None,
        "adapter": "file-fallback",
        "diagnostic": diagnostic,
    })


def _split_selector(raw: str, kind: str) -> tuple[str, str]:
    if "::" not in raw:
        raise ValueError(
            f"--{kind} syntax is PATH::QUALIFIED, got {raw!r}")
    path, qualified = raw.split("::", 1)
    if not path or not qualified:
        raise ValueError(f"--{kind} requires PATH::QUALIFIED")
    return path, qualified


def _target_args(
    args: argparse.Namespace, store: MissionStore, repo: Path,
) -> list[dict[str, Any]]:
    registry = SemanticRegistry()
    targets = [parse_target_json(value) for value in (args.target or [])]
    for raw in args.symbol or []:
        path, qualified = _split_selector(raw, "symbol")
        targets.append(registry.resolve(
            repo, path, "symbol", qualified, commit=args.commit))
    for raw in args.synthetic or []:
        path, qualified = _split_selector(raw, "synthetic")
        targets.append(registry.resolve(
            repo, path, "synthetic", qualified, commit=args.commit))
    for raw in args.path or []:
        path = ensure_repo_child(repo, raw)
        try:
            targets.append(registry.resolve(
                repo, path, "file", commit=args.commit))
        except ValueError as exc:
            if (repo / path).is_dir() or not (repo / path).exists():
                targets.append(_file_target(
                    path, "directory/future-path file fallback"))
            else:
                raise exc
    if not targets:
        header = research_header(store.evidence_dir(args.id))
        if header.get("lease_targets"):
            targets = [
                parse_target_json(raw) for raw in header["lease_targets"]]
        else:
            targets = [
                _file_target(path, "touch-list file fallback")
                for path in header.get("touch_list", [])
            ]
    if not targets:
        raise ValueError(
            "no targets given and research has no lease_targets/touch_list")
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for target in targets:
        target = canonical_target(target)
        ensure_repo_child(repo, target["path"])
        key = (
            target["path"], target["type"],
            target.get("qualified_symbol") or "",
        )
        unique[key] = target
    state_relative = None
    try:
        state_relative = store.root.resolve().relative_to(repo).as_posix()
    except ValueError:
        pass
    if state_relative:
        state_target = _file_target(
            state_relative, "mission state directory")
        if any(targets_conflict(target, state_target)
               for target in unique.values()):
            raise ValueError(
                "lease targets may not include the mission state directory")
    return list(unique.values())


def cmd_lease(args: argparse.Namespace) -> None:
    store = store_for(args)
    _require_spawning(store, f"lease targets for {args.id}")
    versioned = store.queue_item(args.id)
    if versioned.data["state"] not in ("approved", "building"):
        raise ValueError(
            f"{args.id} cannot lease while {versioned.data['state']}")
    targets = _target_args(args, store, repo_root())
    ttl = store.document("mission").data["lease_ttl_minutes"]
    try:
        store.acquire_leases(
            args.id, targets, versioned.version, ttl, targets_conflict)
    except LeaseConflict as exc:
        for requested, held in exc.conflicts:
            print(
                f"semantic contention: {requested['path']}::"
                f"{requested['type']}::"
                f"{requested.get('qualified_symbol') or '*'} vs "
                f"{held['path']}::{held['type']}::"
                f"{held.get('qualified_symbol') or '*'} "
                f"(held by {held['item']}); conflict",
                file=sys.stderr,
            )
        raise SystemExit(2)
    print(f"{args.id}: leased {len(targets)} semantic target(s)")


def cmd_release(args: argparse.Namespace) -> None:
    count = store_for(args).release_leases(args.id)
    print(f"{args.id}: released {count} lease(s)")


def cmd_reclaim(args: argparse.Namespace) -> None:
    store = store_for(args)
    expired: set[str] = set()
    current_time = datetime.now(timezone.utc)
    for lease in store.leases():
        if current_time - parse_time(
                lease["acquired"], "lease acquired") > timedelta(
                    minutes=lease["ttl_minutes"]):
            expired.add(lease["item"])
    for item_id in sorted(expired):
        versioned = store.queue_item(item_id)
        state = versioned.data["state"]
        if state in (
                "merge-pending", "merging", "merge-conflict",
                "post-merge-verifying"):
            print(
                f"{item_id}: expired merge-side lease retained; finish or "
                "explicitly block the merge")
            continue
        if state in ("building", "verifying", "code-review"):
            item = dict(versioned.data)
            item["state"] = "approved"
            item.setdefault("history", []).append({
                "state": "approved", "at": now(), "bounce": True,
                "reason": f"lease-expired:{state}",
            })
            store.update_queue_item(
                item_id, item, versioned.version, state,
                action="lease-reclaim", detail={"from": state})
            suffix = (
                "; worktree preserved" if item.get("worktree") else "")
            print(f"{item_id}: stale {state} -> approved{suffix}")
        store.force_release_leases(item_id)
    if not expired:
        print("no expired leases")


def cmd_worktree_add(args: argparse.Namespace) -> None:
    store = store_for(args)
    _require_spawning(store, f"create worktree for {args.id}")
    versioned = store.queue_item(args.id)
    item = dict(versioned.data)
    if item["state"] != "approved":
        raise ValueError(
            f"worktree-add requires approved, not {item['state']}")
    if not store.leases(args.id):
        raise ValueError(
            f"worktree-add requires {args.id} to hold a lease")
    if item.get("worktree"):
        path = Path(item["worktree"])
        if not path.exists():
            raise ValueError(
                f"{args.id} records missing worktree {path}")
        print(f"{args.id}: reusing preserved worktree {path}")
        return
    store.paths["worktrees"].mkdir(parents=True, exist_ok=True)
    path = (store.paths["worktrees"] / args.id).resolve()
    branch = f"mc/{args.id}"
    repository = repo_root()
    exists = git(
        repository, ["rev-parse", "--verify", "--quiet", branch],
        check=False).returncode == 0
    git(
        repository,
        ["worktree", "add", str(path), branch] if exists else
        ["worktree", "add", "-b", branch, str(path)],
    )
    item["worktree"] = str(path)
    item.setdefault(
        "base_commit",
        git(repository, ["rev-parse", "HEAD"]).stdout.strip(),
    )
    try:
        store.update_queue_item(
            args.id, item, versioned.version, "approved",
            action="worktree-add",
            detail={"path": str(path), "branch": branch},
        )
    except BaseException:
        git(repository, ["worktree", "remove", "--force", str(path)],
            check=False)
        raise
    print(
        f"{args.id}: worktree {path}; edits happen here, builds run through "
        "sandbox prepare/run")


def cmd_worktree_remove(args: argparse.Namespace) -> None:
    store = store_for(args)
    versioned = store.queue_item(args.id)
    item = dict(versioned.data)
    path_value = item.get("worktree")
    if not path_value:
        raise ValueError(f"{args.id} has no worktree")
    if item["state"] in MERGE_STATES:
        raise ValueError(
            "worktree-remove cannot bypass completion or the merge lifecycle "
            f"for {args.id}")
    if item["state"] not in ("approved", "blocked"):
        raise ValueError(
            f"worktree-remove is unsafe while {item['state']}")
    repository = repo_root()
    branch = f"mc/{args.id}"
    merged = git(
        repository, ["branch", "--merged", "HEAD"], check=False).stdout
    if branch not in [
            value.strip("*+ ") for value in merged.splitlines()] and \
            not args.force:
        raise ValueError(
            f"{branch} is unmerged; pass --force to discard")
    git(repository, ["worktree", "remove", "--force", path_value])
    git(
        repository, ["branch", "-D" if args.force else "-d", branch],
        check=False,
    )
    item.pop("worktree", None)
    item.pop("base_commit", None)
    store.update_queue_item(
        args.id, item, versioned.version, versioned.data["state"],
        action="worktree-remove", detail={"force": args.force})
    print(f"{args.id}: worktree removed")


def cmd_semantic_index(args: argparse.Namespace) -> None:
    index = SemanticRegistry().index_repo(
        repo_root(), args.path, commit=args.commit)
    print(json.dumps(index.public(), indent=2, ensure_ascii=False))


def cmd_sandbox(args: argparse.Namespace) -> None:
    store = store_for(args)
    manager = SandboxManager(store, repo_root())
    if args.action == "prepare":
        item = store.queue_item(args.id).data
        commit = args.commit or item.get("implementation_commit")
        if not commit and item.get("worktree"):
            commit = git(
                Path(item["worktree"]), ["rev-parse", "HEAD"]).stdout.strip()
        if not commit:
            raise ValueError(
                "sandbox prepare needs --commit or item implementation commit")
        result = manager.prepare(args.id, commit, backend=args.backend)
    elif args.action == "run":
        result = manager.run(
            args.id, args.command or None,
            evidence_name=args.evidence_name,
        )
    elif args.action == "status":
        result = manager.status(args.id)
    else:
        manager.destroy(args.id)
        print(f"{args.id}: sandbox destroyed")
        return
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_merge(args: argparse.Namespace) -> None:
    coordinator = MergeCoordinator(store_for(args), repo_root())
    if args.action == "prepare":
        result = coordinator.prepare(args.id)
    elif args.action == "finalize":
        result = coordinator.finalize(args.id)
    elif args.action == "retry":
        result = coordinator.retry(args.id)
    else:
        result = coordinator.status(args.id)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_complete(args: argparse.Namespace) -> None:
    """Deprecated compatibility alias for the final, already-prepared gate."""
    store = store_for(args)
    item = store.queue_item(args.id)
    if item.data["state"] == "ready-to-merge":
        replacement = dict(item.data)
        replacement["state"] = "merge-pending"
        replacement.setdefault("history", []).append({
            "state": "merge-pending", "at": now(),
            "reason": "legacy-ready-to-merge",
        })
        store.update_queue_item(
            args.id, replacement, item.version, "ready-to-merge",
            action="legacy-merge-state", detail={})
        item = store.queue_item(args.id)
    if item.data["state"] == "merge-pending":
        raise ValueError(
            f"{args.id} is not merged: complete cannot perform or bypass the "
            "merge lifecycle; run 'merge prepare', inspect its evidence, then "
            "'merge finalize'")
    if item.data["state"] == "merge-conflict":
        raise ValueError(
            f"{args.id} is not merged: resolve and review "
            "merge-resolution.json, then run 'merge finalize'")
    if item.data["state"] == "done":
        print(f"{args.id}: already complete")
        return
    if item.data["state"] != "post-merge-verifying":
        raise ValueError(
            f"complete requires post-merge-verifying, not "
            f"{item.data['state']}")
    coordinator = MergeCoordinator(store, repo_root())
    result = coordinator.finalize(args.id)
    print(
        f"{args.id}: prepared merge verified and published "
        f"{result['new']}")


def _agenda(store: MissionStore) -> Any:
    return store.document("agenda")


def cmd_agenda(args: argparse.Namespace) -> None:
    store = store_for(args)
    current = _agenda(store)
    agenda = dict(current.data)
    agenda["notes"] = list(agenda.get("notes", []))
    if args.action == "add":
        if not args.text:
            raise ValueError("agenda add requires text")
        note = {
            "n": agenda.get("next_id", 1),
            "text": args.text,
            "added": now(),
            "resolved": None,
        }
        if args.when:
            note["when"] = args.when
        agenda["notes"].append(note)
        agenda["next_id"] = note["n"] + 1
        store.update_document(
            "agenda", agenda, current.version, action="agenda-add")
        print(f"agenda #{note['n']}: {args.text}")
    elif args.action == "resolve":
        if args.n is None:
            raise ValueError("agenda resolve requires --n")
        note = next(
            (value for value in agenda["notes"] if value["n"] == args.n),
            None,
        )
        if note is None:
            raise ValueError(f"no agenda note #{args.n}")
        if note["resolved"]:
            raise ValueError(f"agenda note #{args.n} already resolved")
        note["resolved"] = {
            "at": now(), "note": args.note or args.text or "",
        }
        store.update_document(
            "agenda", agenda, current.version, action="agenda-resolve")
        print(f"agenda #{args.n} resolved")
    else:
        notes = agenda["notes"] if args.all else [
            value for value in agenda["notes"] if not value["resolved"]]
        if not notes:
            print("agenda: empty")
        for note in notes:
            marker = "x" if note["resolved"] else " "
            when = f" [when: {note['when']}]" if note.get("when") else ""
            print(f"[{marker}] #{note['n']} {note['text']}{when}")


def cmd_investigate(args: argparse.Namespace) -> None:
    store = store_for(args)
    current = store.document("investigations")
    value = dict(current.data)
    value["items"] = list(value.get("items", []))
    if args.action == "open":
        validate_id(args.id, "investigation id")
        if not args.issue:
            raise ValueError("investigate open requires issue text")
        if any(item["id"] == args.id for item in value["items"]):
            raise ValueError(f"investigation id exists: {args.id}")
        value["items"].append({
            "id": args.id,
            "issue": args.issue,
            "opened": now(),
            "state": "open",
            "disposition": None,
        })
        store.evidence_dir(args.id).mkdir(parents=True, exist_ok=True)
        store.update_document(
            "investigations", value, current.version,
            action="investigation-open")
        print(f"{args.id}: open; diagnosis -> evidence/{args.id}/diagnosis.md")
        return
    entry = next(
        (item for item in value["items"] if item["id"] == args.id), None)
    if entry is None:
        raise ValueError(f"unknown investigation: {args.id}")
    if entry["state"] != "open":
        raise ValueError(f"{args.id} is already closed")
    validate_diagnosis(store.evidence_dir(args.id), entry)
    if not args.disposition:
        raise ValueError("investigate close requires --disposition")
    if args.disposition == "fix":
        if not args.item:
            raise ValueError("fix disposition requires --item")
        for item_id in args.item:
            backlog = store.backlog_item(item_id).data
            if backlog.get("origin") != f"investigation:{args.id}":
                raise ValueError(
                    "fix disposition requires backlog origin "
                    f"investigation:{args.id}: {item_id}")
    elif not args.note:
        raise ValueError(
            f"{args.disposition} disposition requires --note reasoning")
    entry["state"] = "closed"
    diagnosis = store.evidence_dir(args.id) / "diagnosis.md"
    entry["disposition"] = {
        "kind": args.disposition,
        "items": args.item or [],
        "note": args.note,
        "at": now(),
        "diagnosis_sha256": file_hash(diagnosis),
    }
    store.update_document(
        "investigations", value, current.version,
        action="investigation-close")
    print(f"{args.id}: closed ({args.disposition})")


def cmd_status(args: argparse.Namespace) -> None:
    store = store_for(args)
    mission = store.document("mission").data
    validate_mission(mission)
    backlog = store.rows("backlog_items")
    queue = store.rows("queue_items")
    leases = store.leases()
    by_state: dict[str, list[str]] = {}
    for item in queue:
        by_state.setdefault(item["state"], []).append(item["id"])
    open_items = [item for item in backlog if item["status"] == "open"]
    print(f"goal: {mission['goal']}")
    print("state: SQLite WAL (transactional/CAS)")
    throughput = mission.get("throughput") or {}
    if throughput.get("maximize"):
        print(
            "throughput: maximize "
            f"(decided by {throughput.get('decided_by', 'user')})")
    first = sorted(open_items, key=lambda item: item["priority"])[:5]
    print(
        f"backlog open: {len(open_items)} "
        f"({', '.join(item['id'] for item in first)}"
        f"{'…' if len(open_items) > 5 else ''})")
    for state in TRANSITIONS:
        if by_state.get(state):
            print(f"  {state:>22}: {', '.join(by_state[state])}")
    print(
        f"leases held: {len(leases)} across "
        f"{len({lease['item'] for lease in leases})} item(s)")
    contenders: dict[str, list[dict[str, Any]]] = {}
    for event in store.contention():
        contenders.setdefault(event["item"], []).append(event)
    for item_id, events in contenders.items():
        if len(events) >= 2:
            held = sorted({
                owner for event in events for owner in event["held_by"]})
            print(
                f"SEMANTIC CONTENTION: {item_id} lost {len(events)} "
                f"acquisitions vs {', '.join(held)}; same-symbol contention "
                "serializes, repeated decomposition pressure may justify "
                "an architecture reshape")
    done = set(by_state.get("done", []))
    for item in queue:
        if item["state"] == "blocked" and item.get("blocked_on") in done:
            print(
                f"UNBLOCK CANDIDATE: {item['id']} dependency "
                f"{item['blocked_on']} is done")
        if item["state"] == "merge-pending":
            print(
                f"MERGE CANDIDATE: {item['id']} — run merge prepare/finalize")
        if item["state"] == "merge-conflict":
            print(
                f"MERGE RESOLUTION: {item['id']} — inspect "
                "merge-resolution.json; same-target violations must not be "
                "resolved by guessing")
    investigations = store.document("investigations").data["items"]
    for investigation in investigations:
        if investigation["state"] != "open":
            continue
        report = store.evidence_dir(investigation["id"]) / "diagnosis.md"
        label = "DIAGNOSIS READY" if report.exists() else "INVESTIGATION OPEN"
        print(f"{label}: {investigation['id']} — {investigation['issue']}")
    for note in store.document("agenda").data["notes"]:
        if not note["resolved"]:
            when = f" [when: {note['when']}]" if note.get("when") else ""
            print(f"AGENDA #{note['n']}: {note['text']}{when}")
    for reason in _terminal_stop_reasons(store):
        print(f"TERMINAL CONDITION: {reason} reached — stop spawning")
    open_investigations = any(
        item["state"] == "open" for item in investigations)
    drained = mission["terminal_conditions"].get("backlog_drained") and \
        bool(queue) and not open_items and \
        all(item["state"] == "done" for item in queue) and \
        not open_investigations
    if drained:
        print(
            "MISSION COMPLETE: backlog drained, queue done, "
            "no open investigations")


def cmd_metrics(args: argparse.Namespace) -> None:
    output = []
    for item in store_for(args).rows("queue_items"):
        history = item["history"]
        durations: dict[str, float] = {}
        for left, right in zip(history, history[1:]):
            seconds = (
                parse_time(right["at"], "history timestamp") -
                parse_time(left["at"], "history timestamp")
            ).total_seconds()
            state = left["state"]
            durations[state] = durations.get(state, 0) + seconds
        output.append({
            "id": item["id"],
            "state": item["state"],
            "version": item["version"],
            "bounces": sum(
                bool(row.get("bounce")) for row in history),
            "tokens": sum(row.get("tokens", 0) for row in history),
            "seconds_per_state": {
                key: round(value) for key, value in durations.items()},
        })
    print(json.dumps({"items": output, "generated": now()}, indent=2))


def _history_evidence(
    item: dict[str, Any], filename: str,
) -> dict[str, str] | None:
    direct = sealed_record(item, filename)
    if direct:
        return direct
    for history in reversed(item.get("history", [])):
        for key in ("merge_evidence",):
            value = history.get(key)
            if isinstance(value, dict) and value.get("file") == filename:
                return value
    return None


def _check_hash(
    store: MissionStore, item: dict[str, Any], filename: str,
) -> None:
    record = _history_evidence(item, filename)
    path = store.evidence_dir(item["id"]) / filename
    if record is None:
        raise ValueError(f"queue history has no sealed hash for {filename}")
    if not path.is_file() or file_hash(path) != record.get("sha256"):
        raise ValueError(f"{filename} changed after its gate accepted it")


def _audit_done(
    store: MissionStore, item: dict[str, Any],
) -> None:
    backlog = store.backlog_item(item["id"]).data
    if backlog.get("status") != "done":
        raise ValueError(
            f"backlog status is {backlog.get('status')}, expected done")
    evidence = store.evidence_dir(item["id"])
    fast_track = bool(backlog.get("fast_track"))
    header = {} if fast_track else validate_research(
        evidence, item["id"], item, require_fresh=False)
    blast = header.get("blast_radius", "low")
    mission = store.document("mission").data
    if not fast_track:
        validate_sealed_evidence(item, "research.md", evidence)
        validate_review_json(
            evidence, item["id"], item, "plan-review.json",
            "plan-review", "plan-reviewer", forward=True)
        validate_sealed_evidence(item, "plan-review.json", evidence)
        if BLAST_ORDER.index(blast) >= BLAST_ORDER.index(
                mission["gates"]["orchestrator_approval_min_blast"]):
            validate_review_json(
                evidence, item["id"], item, "approval.json",
                "orchestrator-approval", "orchestrator", forward=True)
            validate_sealed_evidence(item, "approval.json", evidence)
    validate_handoff(evidence, item["id"], item)
    validate_sealed_evidence(item, "handoff.md", evidence)
    validate_verify(evidence, item["id"], item, forward=True)
    validate_sealed_evidence(item, "verify.json", evidence)
    _check_hash(store, item, "sandbox.json")
    validate_sandbox(
        evidence, item["id"], "sandbox.json", require_pass=True)
    _check_hash(store, item, "semantic-scope.json")
    semantic = json.loads(
        (evidence / "semantic-scope.json").read_text(encoding="utf-8"))
    if semantic.get("verdict") != "green" or \
            semantic.get("uncovered_targets"):
        raise ValueError("semantic-scope.json does not prove leased scope")
    if BLAST_ORDER.index(blast) >= BLAST_ORDER.index(
            mission["gates"]["code_review_min_blast"]):
        validate_code_review(
            evidence, item["id"], item, header, forward=True)
        validate_sealed_evidence(item, "code-review.json", evidence)
    base = item.get("base_commit")
    implementation = item.get("implementation_commit")
    if not base or not implementation:
        raise ValueError("missing committed-diff metadata")
    scope = validate_committed_scope(
        repo_root(), base, implementation,
        [{"target": target} for target in item.get("leased_targets", [])],
    )
    if scope["verdict"] != "green":
        raise ValueError("implementation diff no longer matches lease snapshot")
    merge_file = (
        "merge-resolution.json"
        if (evidence / "merge-resolution.json").exists() else "merge.json")
    _check_hash(store, item, merge_file)
    merge_value = json.loads(
        (evidence / merge_file).read_text(encoding="utf-8"))
    validate_merge_artifact(
        evidence,
        item["id"],
        merge_file,
        require_resolved=merge_file == "merge-resolution.json",
    )
    if merge_value.get("semantic_invariant_violation"):
        raise ValueError("published merge records semantic invariant violation")
    if merge_file == "merge-resolution.json":
        review = merge_value.get("code_review") or {}
        if review.get("verdict") != "approve":
            raise ValueError("merge resolution lacks code-review approval")
    _check_hash(store, item, "post-merge-verify.json")
    post = json.loads(
        (evidence / "post-merge-verify.json").read_text(encoding="utf-8"))
    if post.get("verdict") != "green":
        raise ValueError("post-merge verification is not green")
    if post.get("sandbox_evidence_sha256") != file_hash(
            evidence / "post-merge-sandbox.json"):
        raise ValueError("post-merge sandbox evidence is missing/tampered")
    validate_sandbox(
        evidence, item["id"], "post-merge-sandbox.json",
        require_pass=True,
    )
    merge_commit = item.get("merge_commit")
    target_ref = item.get("target_ref")
    if not merge_commit or not target_ref or git(
            repo_root(),
            ["merge-base", "--is-ancestor", merge_commit, target_ref],
            check=False).returncode:
        raise ValueError("published merge commit is not on target ref")
    if item.get("worktree"):
        raise ValueError("done item still records a worktree")


def cmd_audit(args: argparse.Namespace) -> None:
    store = store_for(args)
    validate_mission(store.document("mission").data)
    holes = 0
    done = 0
    for item in store.rows("queue_items"):
        if item["state"] != "done":
            continue
        done += 1
        try:
            _audit_done(store, item)
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            print(f"HOLE {item['id']}: {exc}")
            holes += 1
    investigations = store.document("investigations").data["items"]
    for investigation in investigations:
        if investigation["state"] != "closed":
            print(
                f"HOLE {investigation['id']}: investigation is still open")
            holes += 1
            continue
        try:
            validate_diagnosis(
                store.evidence_dir(investigation["id"]), investigation)
            diagnosis = (
                store.evidence_dir(investigation["id"]) / "diagnosis.md")
            disposition = investigation.get("disposition") or {}
            if disposition.get("diagnosis_sha256") != file_hash(diagnosis):
                raise ValueError(
                    "diagnosis.md changed after disposition")
            kind = disposition.get("kind")
            if kind not in ("fix", "architect", "no-action"):
                raise ValueError("invalid or missing disposition")
            if kind == "fix" and not disposition.get("items"):
                raise ValueError("fix disposition names no backlog item")
            if kind in ("architect", "no-action") and \
                    not disposition.get("note"):
                raise ValueError(f"{kind} disposition has no reasoning")
            for linked in disposition.get("items", []):
                entry = store.backlog_item(linked).data
                if entry.get("origin") != \
                        f"investigation:{investigation['id']}":
                    raise ValueError(
                        f"{linked} has wrong investigation origin")
        except (ValueError, OSError) as exc:
            print(f"HOLE {investigation['id']}: {exc}")
            holes += 1
    print(
        f"audit: {done} done item(s), {len(investigations)} "
        f"investigation(s), {holes} hole(s)")
    raise SystemExit(1 if holes else 0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--root", default=".mission-control")
    commands = parser.add_subparsers(dest="cmd", required=True)

    command = commands.add_parser("init", help="create canonical SQLite state")
    command.add_argument("--goal")
    command.set_defaults(fn=cmd_init)

    command = commands.add_parser(
        "configure", help="transactionally merge mission configuration JSON")
    command.add_argument("--json")
    command.add_argument("--file")
    command.set_defaults(fn=cmd_configure)

    command = commands.add_parser(
        "migrate-state", help="idempotently import legacy JSON state")
    command.set_defaults(fn=cmd_migrate_state)
    command = commands.add_parser(
        "export-json", help="write read-only compatibility snapshots")
    command.add_argument("--force", action="store_true")
    command.set_defaults(fn=cmd_export_json)

    command = commands.add_parser("add-item")
    command.add_argument("id")
    command.add_argument("title")
    command.add_argument("--priority", type=int, default=5)
    command.add_argument("--depends-on", nargs="*")
    command.add_argument("--constraint", action="append")
    command.add_argument("--ui", action="store_true")
    command.add_argument("--fast-track", action="store_true")
    command.add_argument("--origin", default="architect")
    command.set_defaults(fn=cmd_add_item)

    command = commands.add_parser("claim")
    command.add_argument("id")
    command.set_defaults(fn=cmd_claim)

    command = commands.add_parser("transition")
    command.add_argument("id")
    command.add_argument("to")
    command.add_argument("--blocked-on")
    command.add_argument("--tokens", type=int)
    command.add_argument("--note")
    command.set_defaults(fn=cmd_transition)

    command = commands.add_parser(
        "lease", help="atomically acquire file/symbol/synthetic targets")
    command.add_argument("id")
    command.add_argument("--path", action="append")
    command.add_argument(
        "--symbol", action="append", help="PATH::QUALIFIED")
    command.add_argument(
        "--synthetic", action="append", help="PATH::AREA")
    command.add_argument(
        "--target", action="append", help="complete target JSON")
    command.add_argument("--commit", default="HEAD")
    command.set_defaults(fn=cmd_lease)

    command = commands.add_parser("release")
    command.add_argument("id")
    command.set_defaults(fn=cmd_release)
    commands.add_parser("reclaim").set_defaults(fn=cmd_reclaim)

    command = commands.add_parser("worktree-add")
    command.add_argument("id")
    command.set_defaults(fn=cmd_worktree_add)
    command = commands.add_parser("worktree-remove")
    command.add_argument("id")
    command.add_argument("--force", action="store_true")
    command.set_defaults(fn=cmd_worktree_remove)

    command = commands.add_parser(
        "semantic-index", help="inspect stable semantic targets")
    command.add_argument("path")
    command.add_argument("--commit", default="HEAD")
    command.set_defaults(fn=cmd_semantic_index)

    command = commands.add_parser(
        "sandbox", help="private execution workspace lifecycle")
    command.add_argument(
        "action", choices=("prepare", "run", "status", "destroy"))
    command.add_argument("id")
    command.add_argument("--commit")
    command.add_argument(
        "--backend", choices=("auto", "native", "docker", "podman"))
    command.add_argument("--command", action="append")
    command.add_argument("--evidence-name", default="sandbox.json")
    command.set_defaults(fn=cmd_sandbox)

    command = commands.add_parser(
        "merge", help="automated integration and CAS publication")
    command.add_argument(
        "action", choices=("prepare", "status", "finalize", "retry"))
    command.add_argument("id")
    command.set_defaults(fn=cmd_merge)

    command = commands.add_parser(
        "complete", help="compatibility wrapper over merge prepare/finalize")
    command.add_argument("id")
    command.set_defaults(fn=cmd_complete)

    command = commands.add_parser("agenda")
    command.add_argument("action", choices=("add", "resolve", "list"))
    command.add_argument("text", nargs="?")
    command.add_argument("--n", type=int)
    command.add_argument("--note")
    command.add_argument("--when")
    command.add_argument("--all", action="store_true")
    command.set_defaults(fn=cmd_agenda)

    command = commands.add_parser("investigate")
    command.add_argument("action", choices=("open", "close"))
    command.add_argument("id")
    command.add_argument("issue", nargs="?")
    command.add_argument(
        "--disposition", choices=("fix", "architect", "no-action"))
    command.add_argument("--item", action="append")
    command.add_argument("--note")
    command.set_defaults(fn=cmd_investigate)

    commands.add_parser("status").set_defaults(fn=cmd_status)
    commands.add_parser("metrics").set_defaults(fn=cmd_metrics)
    commands.add_parser("audit").set_defaults(fn=cmd_audit)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        args.fn(args)
    except RefCASRetry as exc:
        print(f"merge retry: {exc}", file=sys.stderr)
        raise SystemExit(2)
    except (
            ValueError, KeyError, TypeError, OSError,
            json.JSONDecodeError, StateConflict) as exc:
        die(str(exc))


if __name__ == "__main__":
    main()
