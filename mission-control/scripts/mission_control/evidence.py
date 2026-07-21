"""Strict artifact schemas, freshness checks, and content sealing."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .models import (
    BLAST_ORDER,
    COMPLEXITIES,
    GATE_EVIDENCE,
    file_hash,
    normalize_path,
    parse_bool,
    parse_time,
)
from .semantic import parse_target_json


FRESHNESS_TOLERANCE_SECONDS = 1.0


def load_llm_json(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^```\s*$", "", text, flags=re.MULTILINE)
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            raise
        value = json.loads(text[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def markdown(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"{path.name} is empty")
    return text


def require_headings(text: str, filename: str, headings: Iterable[str]) -> None:
    for heading in headings:
        match = re.search(
            rf"(?ims)^#\s+{re.escape(heading)}\s*$"
            rf"([\s\S]*?)(?=^#\s+|\Z)",
            text,
        )
        if not match or not match.group(1).strip():
            raise ValueError(
                f"{filename} requires a non-empty '# {heading}' section")


def required_string(
    obj: dict[str, Any], field: str, filename: str,
    *, allow_empty: bool = False,
) -> str:
    value = obj.get(field)
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ValueError(f"{filename}.{field} must be a non-empty string")
    return value


def state_entered(item: dict[str, Any], state: str) -> datetime:
    records = [
        history for history in item.get("history", [])
        if history.get("state") == state
    ]
    if not records:
        raise ValueError(f"queue history has no entry for state {state}")
    return parse_time(records[-1].get("at"), f"{state} history timestamp")


def fresh(path: Path, entered: datetime, contract_time: datetime | None = None) -> None:
    if path.stat().st_mtime + FRESHNESS_TOLERANCE_SECONDS < entered.timestamp():
        raise ValueError(
            f"{path.name} is stale: update it after entering the current gate")
    if contract_time is not None and \
            contract_time.timestamp() + FRESHNESS_TOLERANCE_SECONDS < \
            entered.timestamp():
        raise ValueError(
            f"{path.name} timestamp is stale: it must be from the current "
            "gate attempt")


def frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = markdown(path)
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path.name} must start with a YAML header")
    header: dict[str, Any] = {}
    current: str | None = None
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if stripped.startswith("- ") and current:
            if not isinstance(header.get(current), list):
                header[current] = []
            header[current].append(stripped[2:].strip())
        elif ":" in stripped:
            key, value = stripped.split(":", 1)
            current = key.strip()
            header[current] = value.strip() if value.strip() else []
    return header, text


def research_header(evidence_dir: Path) -> dict[str, Any]:
    path = evidence_dir / "research.md"
    if not path.exists():
        return {}
    return frontmatter(path)[0]


def record_gate_baseline(
    item: dict[str, Any], state: str, evidence_dir: Path,
) -> None:
    filename = GATE_EVIDENCE.get(state)
    if filename is None:
        return
    path = evidence_dir / filename
    item.setdefault("evidence_baselines", {})[state] = (
        file_hash(path) if path.is_file() else None)


def require_new_gate_evidence(
    item: dict[str, Any], state: str, path: Path,
) -> None:
    baselines = item.get("evidence_baselines", {})
    if state in baselines and baselines[state] == file_hash(path):
        raise ValueError(
            f"{path.name} is unchanged from the previous gate attempt")


def seal_gate_evidence(
    item: dict[str, Any], state: str, history_entry: dict[str, Any],
    evidence_dir: Path,
) -> list[dict[str, str]]:
    filename = GATE_EVIDENCE.get(state)
    if filename is None:
        return []
    path = evidence_dir / filename
    if not path.is_file():
        return []
    seal = {"file": filename, "sha256": file_hash(path)}
    history_entry["evidence"] = seal
    return [seal]


def sealed_record(
    item: dict[str, Any], filename: str,
) -> dict[str, str] | None:
    for history in reversed(item.get("history", [])):
        value = history.get("evidence")
        if isinstance(value, dict) and value.get("file") == filename:
            return value
        for extra in history.get("additional_evidence", []):
            if extra.get("file") == filename:
                return extra
    return None


def validate_sealed_evidence(
    item: dict[str, Any], filename: str, evidence_dir: Path,
) -> None:
    record = sealed_record(item, filename)
    if record is None:
        raise ValueError(f"queue history has no sealed hash for {filename}")
    path = evidence_dir / filename
    if not path.is_file() or file_hash(path) != record.get("sha256"):
        raise ValueError(f"{filename} changed after its gate accepted it")


def validate_mission(mission: dict[str, Any]) -> None:
    if not isinstance(mission, dict):
        raise ValueError("mission must contain an object")
    required_string(mission, "goal", "mission")
    terminal = mission.get("terminal_conditions")
    if not isinstance(terminal, dict):
        raise ValueError("mission.terminal_conditions must be an object")
    if terminal.get("backlog_drained") not in (True, False, None):
        raise ValueError("terminal_conditions.backlog_drained must be boolean")
    for field in ("max_items_completed", "token_budget"):
        value = terminal.get(field)
        if value is not None and (
                not isinstance(value, int) or isinstance(value, bool) or
                value <= 0):
            raise ValueError(
                f"terminal_conditions.{field} must be positive integer/null")
    if terminal.get("deadline") is not None:
        parse_time(terminal["deadline"], "terminal_conditions.deadline")
    if not any((
            terminal.get("backlog_drained"),
            terminal.get("max_items_completed"),
            terminal.get("token_budget"),
            terminal.get("deadline"))):
        raise ValueError("mission must enable at least one terminal condition")
    gates = mission.get("gates")
    if not isinstance(gates, dict):
        raise ValueError("mission.gates must be an object")
    for field in (
            "orchestrator_approval_min_blast", "code_review_min_blast"):
        if gates.get(field) not in BLAST_ORDER:
            raise ValueError(f"mission.gates.{field} has invalid blast enum")
    if not isinstance(mission.get("repo_oracle"), dict):
        raise ValueError("mission.repo_oracle must be an object")
    if not isinstance(mission.get("lease_ttl_minutes"), (int, float)) or \
            mission["lease_ttl_minutes"] <= 0:
        raise ValueError("mission.lease_ttl_minutes must be positive")
    if not isinstance(mission.get("bounce_limit"), int) or \
            mission["bounce_limit"] <= 0:
        raise ValueError("mission.bounce_limit must be a positive integer")
    execution = mission.get("execution", {})
    if not isinstance(execution, dict):
        raise ValueError("mission.execution must be an object")
    if execution.get("backend", "auto") not in (
            "auto", "native", "docker", "podman"):
        raise ValueError(
            "mission.execution.backend must be auto/native/docker/podman")
    if not isinstance(execution.get("native_fallback", True), bool):
        raise ValueError("mission.execution.native_fallback must be boolean")
    merge = mission.get("merge", {})
    if not isinstance(merge, dict):
        raise ValueError("mission.merge must be an object")
    if merge.get("max_cas_retries", 3) < 1:
        raise ValueError("mission.merge.max_cas_retries must be positive")


def validate_research(
    evidence_dir: Path, item_id: str, item: dict[str, Any],
    *, require_fresh: bool = True,
) -> dict[str, Any]:
    path = evidence_dir / "research.md"
    if not path.is_file():
        raise ValueError(f"researching gate requires {path}")
    require_new_gate_evidence(item, "researching", path)
    header, text = frontmatter(path)
    if header.get("item") != item_id:
        raise ValueError(f"research.md item must be {item_id}")
    if header.get("complexity") not in COMPLEXITIES:
        raise ValueError("research.md complexity must be low, medium, or high")
    if header.get("blast_radius") not in BLAST_ORDER:
        raise ValueError(
            "research.md blast_radius must be low, medium, high, or critical")
    paths = header.get("touch_list")
    if not isinstance(paths, list) or not paths:
        raise ValueError("research.md touch_list must be a non-empty list")
    normalized = [normalize_path(value) for value in paths]
    if len(set(normalized)) != len(normalized):
        raise ValueError(
            "research.md touch_list contains equivalent duplicate paths")
    parse_bool(header.get("ui"), "research.md ui")
    parse_bool(header.get("splittable", "false"), "research.md splittable")
    parse_bool(header.get("concurrency"), "research.md concurrency")
    lease_targets = header.get("lease_targets", [])
    if lease_targets:
        if not isinstance(lease_targets, list):
            raise ValueError("research.md lease_targets must be a list")
        for raw in lease_targets:
            parse_target_json(raw)
    require_headings(
        text, "research.md",
        ("Problem", "Approach", "Acceptance criteria", "Risks & unknowns"),
    )
    if require_fresh:
        fresh(path, state_entered(item, "researching"))
    return header


def validate_review_json(
    evidence_dir: Path, item_id: str, item: dict[str, Any],
    filename: str, state_name: str, expected_reviewer: str,
    *, forward: bool,
) -> dict[str, Any]:
    path = evidence_dir / filename
    if not path.is_file():
        raise ValueError(f"{state_name} gate requires {path}")
    require_new_gate_evidence(item, state_name, path)
    value = load_llm_json(path)
    if value.get("item") != item_id:
        raise ValueError(f"{filename}.item must be {item_id}")
    if value.get("reviewer") != expected_reviewer:
        raise ValueError(f"{filename}.reviewer must be {expected_reviewer}")
    wanted = "sign-off" if forward else "bounce"
    if value.get("verdict") != wanted:
        raise ValueError(
            f"{filename}.verdict must be {wanted} for this transition")
    checks = value.get("checks")
    if not isinstance(checks, dict):
        raise ValueError(f"{filename}.checks must be an object")
    names = ("soundness", "testability", "routing_honesty", "scope")
    for check in names:
        required_string(checks, check, f"{filename}.checks")
    if forward and any(checks[name].strip() != "pass" for name in names):
        raise ValueError(
            f"{filename} sign-off requires every check to equal 'pass'")
    if not forward and not any(
            checks[name].strip().startswith("fail:") for name in names):
        raise ValueError(
            f"{filename} bounce requires at least one 'fail: reason' check")
    notes = required_string(value, "notes", filename, allow_empty=True)
    if expected_reviewer == "orchestrator" and forward and not notes.strip():
        raise ValueError(
            "approval.json.notes must explain high-blast approval")
    stamp = parse_time(value.get("timestamp"), f"{filename}.timestamp")
    fresh(path, state_entered(item, state_name), stamp)
    return value


def validate_handoff(
    evidence_dir: Path, item_id: str, item: dict[str, Any],
) -> None:
    path = evidence_dir / "handoff.md"
    if not path.is_file():
        raise ValueError(f"building gate requires {path}")
    require_new_gate_evidence(item, "building", path)
    header, text = frontmatter(path)
    if header.get("item") != item_id:
        raise ValueError(f"handoff.md item must be {item_id}")
    if header.get("implementer") not in ("senior", "junior"):
        raise ValueError("handoff.md implementer must be senior or junior")
    require_headings(text, "handoff.md", ("Changed", "Criteria status"))
    for heading in ("Judgment calls", "Backlog suggestions"):
        if not re.search(rf"(?im)^#\s+{re.escape(heading)}\s*$", text):
            raise ValueError(f"handoff.md requires a '# {heading}' section")
    fresh(path, state_entered(item, "building"))


def validate_sandbox(
    evidence_dir: Path, item_id: str, filename: str,
    *, require_pass: bool,
) -> dict[str, Any]:
    path = evidence_dir / filename
    if not path.is_file():
        raise ValueError(f"isolated execution requires {path}")
    value = load_llm_json(path)
    if value.get("item") != item_id:
        raise ValueError(f"{filename}.item must be {item_id}")
    if value.get("backend") not in ("native", "docker", "podman", "fake"):
        raise ValueError(f"{filename}.backend has invalid enum")
    if not isinstance(value.get("degraded_isolation"), bool):
        raise ValueError(f"{filename}.degraded_isolation must be boolean")
    required_string(value, "source_commit", filename)
    if not isinstance(value.get("resource_policy"), dict):
        raise ValueError(f"{filename}.resource_policy must be an object")
    commands = value.get("commands")
    if not isinstance(commands, list) or not commands:
        raise ValueError(f"{filename}.commands must be a non-empty list")
    for index, command in enumerate(commands):
        if not isinstance(command, dict):
            raise ValueError(f"{filename}.commands[{index}] must be object")
        required_string(command, "command", f"{filename}.commands[{index}]")
        if not isinstance(command.get("exit_code"), int):
            raise ValueError(
                f"{filename}.commands[{index}].exit_code must be integer")
        log_name = required_string(
            command, "log", f"{filename}.commands[{index}]")
        log_path = (evidence_dir / log_name).resolve()
        try:
            log_path.relative_to(evidence_dir.resolve())
        except ValueError as exc:
            raise ValueError(
                f"{filename}.commands[{index}].log traverses evidence dir"
            ) from exc
        if not log_path.is_file() or file_hash(log_path) != \
                command.get("log_sha256"):
            raise ValueError(
                f"{filename} command log is missing or tampered: {log_name}")
    artifacts = value.get("artifact_hashes")
    if not isinstance(artifacts, dict):
        raise ValueError(f"{filename}.artifact_hashes must be an object")
    for artifact, digest in artifacts.items():
        normalize_path(artifact)
        if not isinstance(digest, str) or not re.fullmatch(
                r"[0-9a-f]{64}", digest):
            raise ValueError(
                f"{filename}.artifact_hashes values must be SHA-256")
    stamp = parse_time(value.get("timestamp"), f"{filename}.timestamp")
    if require_pass and any(command["exit_code"] != 0 for command in commands):
        raise ValueError(f"{filename} contains a failed command")
    return value


def validate_merge_artifact(
    evidence_dir: Path,
    item_id: str,
    filename: str,
    *,
    require_resolved: bool,
) -> dict[str, Any]:
    path = evidence_dir / filename
    if not path.is_file():
        raise ValueError(f"merge lifecycle requires {path}")
    value = load_llm_json(path)
    if value.get("item") != item_id:
        raise ValueError(f"{filename}.item must be {item_id}")
    for field in ("base", "ours", "theirs", "target_ref"):
        required_string(value, field, filename)
    conflict_paths = value.get("conflict_paths")
    if not isinstance(conflict_paths, list) or not all(
            isinstance(entry, str) and entry for entry in conflict_paths):
        raise ValueError(f"{filename}.conflict_paths must be a string list")
    parse_time(value.get("timestamp"), f"{filename}.timestamp")
    if filename == "merge.json":
        if value.get("kind") not in ("clean", "already-integrated"):
            raise ValueError(f"{filename}.kind has an invalid enum")
        if conflict_paths:
            raise ValueError(f"{filename} clean evidence cannot list conflicts")
        required_string(value, "result_commit", filename)
        scope = value.get("scope_validation")
        if not isinstance(scope, dict) or scope.get("verdict") != "green" or \
                scope.get("uncovered_targets"):
            raise ValueError(
                f"{filename}.scope_validation must prove green leased scope")
        return value
    if filename != "merge-resolution.json":
        raise ValueError(f"unsupported merge evidence filename: {filename}")
    for field in (
            "conflict_hunks",
            "ours_semantic_targets",
            "theirs_semantic_targets",
            "overlapping_semantic_targets"):
        if not isinstance(value.get(field), list):
            raise ValueError(f"{filename}.{field} must be a list")
    for field in ("semantic_invariant_violation", "resolution_allowed"):
        if not isinstance(value.get(field), bool):
            raise ValueError(f"{filename}.{field} must be boolean")
    if value["resolution_allowed"] == value["semantic_invariant_violation"]:
        raise ValueError(
            f"{filename} invariant and resolution flags are inconsistent")
    required_string(value, "reasoning", filename)
    if require_resolved:
        required_string(value, "resolution_commit", filename)
        review = value.get("code_review")
        if not isinstance(review, dict) or review.get("verdict") != "approve":
            raise ValueError(
                f"{filename}.code_review.verdict must be approve")
        if review.get("reviewer") != "code-reviewer":
            raise ValueError(
                f"{filename}.code_review.reviewer must be code-reviewer")
        findings = review.get("findings")
        if not isinstance(findings, list):
            raise ValueError(
                f"{filename}.code_review.findings must be a list")
        if any(
                isinstance(finding, dict) and
                finding.get("severity") == "blocking"
                for finding in findings):
            raise ValueError(
                f"{filename} approved review has blocking findings")
        parse_time(
            review.get("timestamp"),
            f"{filename}.code_review.timestamp",
        )
        scope = value.get("scope_validation")
        if not isinstance(scope, dict) or scope.get("verdict") != "green" or \
                scope.get("uncovered_targets"):
            raise ValueError(
                f"{filename}.scope_validation must prove green leased scope")
    return value


def validate_verify(
    evidence_dir: Path, item_id: str, item: dict[str, Any],
    *, forward: bool,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    path = evidence_dir / "verify.json"
    if not path.is_file():
        raise ValueError(f"verifying gate requires {path}")
    require_new_gate_evidence(item, "verifying", path)
    value = load_llm_json(path)
    if value.get("item") != item_id:
        raise ValueError(f"verify.json.item must be {item_id}")
    allowed = ("green",) if forward else ("red", "oracle-broken")
    if value.get("verdict") not in allowed:
        raise ValueError(
            "verify.json.verdict must be "
            f"{'green' if forward else 'red or oracle-broken'} for transition")
    for field in ("build", "tests"):
        record = value.get(field)
        if not isinstance(record, dict):
            raise ValueError(f"verify.json.{field} must be an object")
        required_string(record, "command", f"verify.json.{field}")
        if not isinstance(record.get("pass"), bool):
            raise ValueError(f"verify.json.{field}.pass must be boolean")
    if not isinstance(value["tests"].get("failures"), list):
        raise ValueError("verify.json.tests.failures must be a list")
    criteria = value.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("verify.json.criteria must be a non-empty list")
    for index, criterion in enumerate(criteria, 1):
        if not isinstance(criterion, dict) or \
                not isinstance(criterion.get("n"), int) or \
                not isinstance(criterion.get("pass"), bool):
            raise ValueError(
                f"verify.json.criteria entry {index} requires integer n "
                "and boolean pass")
        required_string(
            criterion, "command", f"verify.json.criteria[{index}]")
        required_string(
            criterion, "output_excerpt",
            f"verify.json.criteria[{index}]", allow_empty=True)
    for field in ("diff_in_scope", "oracle_tampering"):
        if not isinstance(value.get(field), bool):
            raise ValueError(f"verify.json.{field} must be boolean")
    if not isinstance(value.get("out_of_scope_paths"), list):
        raise ValueError("verify.json.out_of_scope_paths must be a list")
    if forward and (
            not value["build"]["pass"] or not value["tests"]["pass"] or
            not all(criterion["pass"] for criterion in criteria) or
            not value["diff_in_scope"] or value["out_of_scope_paths"] or
            value["oracle_tampering"]):
        raise ValueError(
            "green verification requires passing build/tests/criteria, "
            "in-scope diff, no out-of-scope paths, and no oracle tampering")
    stamp = parse_time(value.get("timestamp"), "verify.json.timestamp")
    fresh(path, state_entered(item, "verifying"), stamp)
    sandbox = None
    if forward:
        sandbox = validate_sandbox(
            evidence_dir, item_id, "sandbox.json", require_pass=True)
        if value.get("sandbox_evidence_sha256") != file_hash(
                evidence_dir / "sandbox.json"):
            raise ValueError(
                "verify.json.sandbox_evidence_sha256 does not seal sandbox.json")
    return value, sandbox


def validate_code_review(
    evidence_dir: Path, item_id: str, item: dict[str, Any],
    header: dict[str, Any], *, forward: bool,
) -> dict[str, Any]:
    path = evidence_dir / "code-review.json"
    if not path.is_file():
        raise ValueError(f"code-review gate requires {path}")
    require_new_gate_evidence(item, "code-review", path)
    value = load_llm_json(path)
    if value.get("item") != item_id:
        raise ValueError(f"code-review.json.item must be {item_id}")
    wanted = "approve" if forward else "bounce"
    if value.get("verdict") != wanted:
        raise ValueError(
            f"code-review.json.verdict must be {wanted} for transition")
    if not isinstance(value.get("concurrency_reviewed"), bool):
        raise ValueError(
            "code-review.json.concurrency_reviewed must be boolean")
    if parse_bool(
            header.get("concurrency", "false"),
            "research.md concurrency") and not value["concurrency_reviewed"]:
        raise ValueError(
            "code-review.json.concurrency_reviewed must be true for a "
            "concurrency-flagged item")
    findings = value.get("findings")
    if not isinstance(findings, list):
        raise ValueError("code-review.json.findings must be a list")
    for index, finding in enumerate(findings, 1):
        if not isinstance(finding, dict) or finding.get("severity") not in (
                "blocking", "advisory"):
            raise ValueError(
                f"code-review.json.findings[{index}] has invalid severity")
        for field in ("location", "defect", "standard_violated"):
            required_string(
                finding, field, f"code-review.json.findings[{index}]")
    blocking = [
        finding for finding in findings if finding["severity"] == "blocking"
    ]
    if forward and blocking:
        raise ValueError(
            "code-review approval cannot contain blocking findings")
    if not forward and not blocking:
        raise ValueError(
            "code-review bounce requires at least one blocking finding")
    if not isinstance(value.get("judgment_calls_audited"), bool):
        raise ValueError(
            "code-review.json.judgment_calls_audited must be boolean")
    stamp = parse_time(value.get("timestamp"), "code-review.json.timestamp")
    fresh(path, state_entered(item, "code-review"), stamp)
    return value


def validate_diagnosis(
    evidence_dir: Path, entry: dict[str, Any],
) -> dict[str, Any]:
    path = evidence_dir / "diagnosis.md"
    if not path.is_file():
        raise ValueError(f"closing {entry['id']} requires {path}")
    header, text = frontmatter(path)
    if header.get("investigation") != entry["id"]:
        raise ValueError(
            f"diagnosis.md investigation must be {entry['id']}")
    if header.get("verdict") not in (
            "root-cause-found", "no-defect", "cannot-reproduce"):
        raise ValueError("diagnosis.md verdict has an invalid enum")
    if header.get("recommended_disposition") not in (
            "fix", "architect", "no-action"):
        raise ValueError(
            "diagnosis.md recommended_disposition has an invalid enum")
    require_headings(
        text, "diagnosis.md",
        ("Symptom", "Reproduction", "Root cause",
         "Recommended disposition"),
    )
    fresh(path, parse_time(entry["opened"], "investigation opened"))
    return header
