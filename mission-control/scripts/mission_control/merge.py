"""Automated merge coordination with semantic conflict and ref-CAS gates."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .evidence import (
    load_llm_json,
    required_string,
    validate_merge_artifact,
)
from .models import (
    StateConflict,
    bytes_hash,
    file_hash,
    json_text,
    now,
    parse_time,
    remove_tree,
)
from .sandbox import SandboxManager
from .semantic import (
    map_committed_diff,
    replace_disjoint_python_symbols,
    targets_overlap,
    validate_committed_scope,
)
from .store import MissionStore


class RefCASRetry(ValueError):
    """The target ref advanced; caller should reintegrate."""


def git(
    repo: Path, args: list[str], *, check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True, capture_output=True,
    )
    if check and result.returncode:
        raise ValueError(
            f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result


def current_target_ref(repo: Path) -> str:
    result = git(repo, ["symbolic-ref", "-q", "HEAD"], check=False)
    if result.returncode:
        raise ValueError(
            "detached HEAD: configure mission.merge.target_ref explicitly")
    return result.stdout.strip()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _targets_for_path(
    report: dict[str, Any], path: str,
) -> list[dict[str, Any]]:
    return [
        target for target in report.get("changed_targets", [])
        if target["path"] == path
    ]


def _map_or_empty(
    repo: Path, base: str, result: str,
) -> dict[str, Any]:
    if base == result:
        return {
            "base_commit": base, "result_commit": result,
            "changed_paths": [], "changed_targets": [], "diagnostics": [],
        }
    diff = git(repo, ["diff", "--quiet", base, result], check=False)
    if diff.returncode == 0:
        return {
            "base_commit": base, "result_commit": result,
            "changed_paths": [], "changed_targets": [], "diagnostics": [],
        }
    return map_committed_diff(repo, base, result)


CONFLICT_ANALYSIS_FIELDS = (
    "item",
    "base",
    "ours",
    "theirs",
    "target_ref",
    "conflict_paths",
    "conflict_hunks",
    "ours_semantic_targets",
    "theirs_semantic_targets",
    "overlapping_semantic_targets",
    "semantic_invariant_violation",
    "resolution_allowed",
    "reasoning",
)


def _conflict_analysis_hash(artifact: dict[str, Any]) -> str:
    analysis = {
        field: artifact.get(field) for field in CONFLICT_ANALYSIS_FIELDS
    }
    return bytes_hash(json_text(analysis).encode("utf-8"))


class MergeCoordinator:
    """Own an item's integration clone from preparation through CAS publish."""

    def __init__(self, store: MissionStore, repo: Path):
        self.store = store
        self.repo = repo.resolve()

    def _config(self) -> dict[str, Any]:
        mission = self.store.document("mission").data
        config = dict(mission.get("merge") or {})
        config.setdefault("target_ref", None)
        config.setdefault("max_cas_retries", 3)
        return config

    def _target_ref(self) -> str:
        return self._config().get("target_ref") or current_target_ref(self.repo)

    def _integration_path(self, item_id: str) -> Path:
        return (self.store.paths["integration"] / item_id).resolve()

    def _transition(
        self, versioned: Any, state: str, reason: str,
        *, detail: dict[str, Any] | None = None,
    ) -> int:
        item = dict(versioned.data)
        previous = item["state"]
        item["state"] = state
        history = {"state": state, "at": now(), "reason": reason}
        item.setdefault("history", []).append(history)
        return self.store.update_queue_item(
            item["id"], item, versioned.version, previous,
            action="merge-state", detail=detail or {
                "from": previous, "to": state, "reason": reason},
        )

    def prepare(self, item_id: str) -> dict[str, Any]:
        versioned = self.store.queue_item(item_id)
        item = versioned.data
        if item["state"] == "ready-to-merge":
            item["state"] = "merge-pending"
            versioned = type(versioned)(item, versioned.version)
        if item["state"] != "merge-pending":
            raise ValueError(
                f"merge prepare requires merge-pending, not {item['state']}")
        implementation = item.get("implementation_commit")
        if not implementation:
            worktree = item.get("worktree")
            if not worktree:
                raise ValueError(
                    f"{item_id} has no implementation commit/worktree")
            implementation = git(
                Path(worktree), ["rev-parse", "HEAD"]).stdout.strip()
        target_ref = self._target_ref()
        target_head = git(
            self.repo, ["rev-parse", target_ref]).stdout.strip()
        item = dict(item)
        item.update({
            "implementation_commit": implementation,
            "target_ref": target_ref,
            "target_head": target_head,
            "state": "merging",
        })
        item.setdefault("history", []).append({
            "state": "merging", "at": now(),
            "target_ref": target_ref, "target_head": target_head,
        })
        merging_version = self.store.update_queue_item(
            item_id, item, versioned.version, "merge-pending",
            action="merge-prepare",
            detail={"target_ref": target_ref, "target_head": target_head},
        )

        integration = self._integration_path(item_id)
        if integration.exists():
            remove_tree(integration)
        integration.parent.mkdir(parents=True, exist_ok=True)
        clone = subprocess.run([
            "git", "clone", "--quiet", "--no-hardlinks", "--no-checkout",
            str(self.repo), str(integration),
        ], text=True, capture_output=True)
        if clone.returncode:
            self._recover_prepare_failure(
                item_id, merging_version, item,
                f"integration clone failed: {clone.stderr.strip()}")
            raise ValueError(
                f"integration clone failed: {clone.stderr.strip()}")
        git(integration, ["config", "user.email", "mission-control@invalid"])
        git(integration, ["config", "user.name", "Mission Control Merge"])
        git(integration, ["config", "commit.gpgSign", "false"])
        git(integration, ["checkout", "--quiet", "--detach", target_head])
        # Local clone copies all branch objects, but a commit held only by a
        # linked-worktree branch may still require an explicit object fetch.
        if git(
                integration, ["cat-file", "-e", f"{implementation}^{{commit}}"],
                check=False).returncode:
            git(integration, ["fetch", "--quiet", str(self.repo), implementation])
        base = git(
            integration, ["merge-base", target_head, implementation]
        ).stdout.strip()
        ours_report = _map_or_empty(integration, base, target_head)
        theirs_report = _map_or_empty(integration, base, implementation)

        already = git(
            integration,
            ["merge-base", "--is-ancestor", implementation, target_head],
            check=False,
        ).returncode == 0
        if already:
            result_commit = target_head
            scope = {
                "base_commit": target_head,
                "result_commit": target_head,
                "changed_paths": [],
                "changed_targets": [],
                "leased_targets": [
                    lease["target"] for lease in self.store.leases(item_id)
                ],
                "uncovered_targets": [],
                "verdict": "green",
                "diagnostics": ["implementation already present in target"],
            }
            artifact = {
                "item": item_id,
                "kind": "already-integrated",
                "base": base,
                "ours": target_head,
                "theirs": implementation,
                "target_ref": target_ref,
                "result_commit": result_commit,
                "conflict_paths": [],
                "scope_validation": scope,
                "timestamp": now(),
            }
            return self._record_clean(
                item_id, merging_version, item, integration, artifact)

        overlap = targets_overlap(
            ours_report.get("changed_targets", []),
            theirs_report.get("changed_targets", []),
        )
        if overlap:
            overlap_paths = sorted({
                left["path"] for left, _ in overlap
            } | {
                right["path"] for _, right in overlap
            })
            artifact = self._conflict_artifact(
                item_id, base, target_head, implementation, target_ref,
                overlap_paths, ours_report, theirs_report,
                semantic_invariant=True,
                reasoning=(
                    "target and implementation histories touch the same or "
                    "hierarchical semantic target; Merge Agent resolution is "
                    "forbidden even when Git could merge the text"),
                overlap=overlap,
            )
            return self._record_conflict(
                item_id, merging_version, item, integration, artifact)

        merge = git(
            integration,
            ["merge", "--no-ff", "--no-commit", implementation],
            check=False,
        )
        if merge.returncode == 0:
            git(integration, [
                "commit", "--quiet", "-m",
                f"Merge mission-control item {item_id}",
            ])
            result_commit = git(
                integration, ["rev-parse", "HEAD"]).stdout.strip()
            scope = validate_committed_scope(
                integration, target_head, result_commit,
                self.store.leases(item_id),
            )
            if scope["verdict"] != "green":
                artifact = self._conflict_artifact(
                    item_id, base, target_head, implementation, target_ref,
                    [], ours_report, theirs_report,
                    semantic_invariant=True,
                    reasoning=(
                        "clean merge produced targets outside the item lease"),
                    result_commit=result_commit, scope=scope,
                )
                return self._record_conflict(
                    item_id, merging_version, item, integration, artifact)
            artifact = {
                "item": item_id,
                "kind": "clean",
                "base": base,
                "ours": target_head,
                "theirs": implementation,
                "target_ref": target_ref,
                "result_commit": result_commit,
                "conflict_paths": [],
                "scope_validation": scope,
                "timestamp": now(),
            }
            return self._record_clean(
                item_id, merging_version, item, integration, artifact)

        conflict_paths = [
            line for line in git(
                integration,
                ["diff", "--name-only", "--diff-filter=U"],
            ).stdout.splitlines() if line
        ]
        overlap = []
        for path in conflict_paths:
            overlap.extend(targets_overlap(
                _targets_for_path(ours_report, path),
                _targets_for_path(theirs_report, path),
            ))
        if overlap:
            artifact = self._conflict_artifact(
                item_id, base, target_head, implementation, target_ref,
                conflict_paths, ours_report, theirs_report,
                semantic_invariant=True,
                reasoning=(
                    "conflicting branches touch the same or hierarchical "
                    "semantic target; Merge Agent resolution is forbidden"),
                overlap=overlap,
            )
            return self._record_conflict(
                item_id, merging_version, item, integration, artifact)

        auto_result = self._try_disjoint_resolution(
            integration, base, target_head, implementation,
            conflict_paths, ours_report, theirs_report,
        )
        if auto_result is not None:
            scope = validate_committed_scope(
                integration, target_head, auto_result,
                self.store.leases(item_id),
            )
            artifact = self._conflict_artifact(
                item_id, base, target_head, implementation, target_ref,
                conflict_paths, ours_report, theirs_report,
                semantic_invariant=scope["verdict"] != "green",
                reasoning=(
                    "mechanically combined semantically disjoint Python "
                    "sibling symbols; code-review approval is still required"),
                result_commit=auto_result, scope=scope,
            )
            return self._record_conflict(
                item_id, merging_version, item, integration, artifact)

        artifact = self._conflict_artifact(
            item_id, base, target_head, implementation, target_ref,
            conflict_paths, ours_report, theirs_report,
            semantic_invariant=False,
            reasoning=(
                "textual conflict is semantically disjoint but not mechanically "
                "resolvable; Merge Agent must resolve in the integration clone"),
        )
        return self._record_conflict(
            item_id, merging_version, item, integration, artifact)

    def _recover_prepare_failure(
        self, item_id: str, version: int, item: dict[str, Any], reason: str,
    ) -> None:
        current = self.store.queue_item(item_id)
        if current.version != version or current.data["state"] != "merging":
            return
        replacement = dict(current.data)
        replacement["state"] = "merge-pending"
        replacement.setdefault("history", []).append({
            "state": "merge-pending", "at": now(), "reason": reason,
        })
        self.store.update_queue_item(
            item_id, replacement, current.version, "merging",
            action="merge-prepare-failed", detail={"reason": reason})

    def _record_clean(
        self, item_id: str, merging_version: int, item: dict[str, Any],
        integration: Path, artifact: dict[str, Any],
    ) -> dict[str, Any]:
        evidence_path = self.store.evidence_dir(item_id) / "merge.json"
        _write_json(evidence_path, artifact)
        record = {
            "item": item_id,
            "state": "prepared",
            "kind": artifact["kind"],
            "integration_path": str(integration),
            "target_ref": artifact["target_ref"],
            "target_head": artifact["ours"],
            "implementation_commit": artifact["theirs"],
            "result_commit": artifact["result_commit"],
            "artifact": "merge.json",
            "artifact_sha256": file_hash(evidence_path),
            "prepared_at": now(),
        }
        self.store.put_runtime_record("merge_jobs", item_id, record)
        current = self.store.queue_item(item_id)
        if current.version != merging_version or \
                current.data["state"] != "merging":
            raise StateConflict(
                f"{item_id} changed while mechanical merge was running")
        replacement = dict(current.data)
        replacement["state"] = "post-merge-verifying"
        replacement["merge_result_commit"] = artifact["result_commit"]
        replacement.setdefault("history", []).append({
            "state": "post-merge-verifying", "at": now(),
            "merge_evidence": {
                "file": "merge.json", "sha256": file_hash(evidence_path),
            },
        })
        self.store.update_queue_item(
            item_id, replacement, current.version, "merging",
            action="merge-clean",
            detail={"result_commit": artifact["result_commit"]},
        )
        return artifact

    def _conflict_hunks(
        self, integration: Path, paths: list[str],
    ) -> list[dict[str, Any]]:
        records = []
        for path in paths:
            file_path = integration / path
            text = file_path.read_text(
                encoding="utf-8", errors="replace") if file_path.is_file() else ""
            marker_lines = [
                line[:500] for line in text.splitlines()
                if line.startswith(("<<<<<<<", "=======", ">>>>>>>"))
            ]
            records.append({
                "path": path,
                "conflict_file_sha256": (
                    file_hash(file_path) if file_path.is_file() else None),
                "markers": marker_lines,
            })
        return records

    def _conflict_artifact(
        self, item_id: str, base: str, ours: str, theirs: str,
        target_ref: str, conflict_paths: list[str],
        ours_report: dict[str, Any], theirs_report: dict[str, Any],
        *, semantic_invariant: bool, reasoning: str,
        overlap: list[tuple[dict[str, Any], dict[str, Any]]] | None = None,
        result_commit: str | None = None,
        scope: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        integration = self._integration_path(item_id)
        return {
            "item": item_id,
            "base": base,
            "ours": ours,
            "theirs": theirs,
            "target_ref": target_ref,
            "conflict_paths": conflict_paths,
            "conflict_hunks": self._conflict_hunks(
                integration, conflict_paths),
            "ours_semantic_targets": ours_report.get("changed_targets", []),
            "theirs_semantic_targets": theirs_report.get("changed_targets", []),
            "overlapping_semantic_targets": [
                {"ours": left, "theirs": right}
                for left, right in (overlap or [])
            ],
            "semantic_invariant_violation": semantic_invariant,
            "resolution_allowed": not semantic_invariant,
            "reasoning": reasoning,
            "resolution_commit": result_commit,
            "scope_validation": scope,
            "code_review": {
                "verdict": "pending",
                "reviewer": "code-reviewer",
                "findings": [],
                "timestamp": None,
            },
            "timestamp": now(),
        }

    def _record_conflict(
        self, item_id: str, merging_version: int, item: dict[str, Any],
        integration: Path, artifact: dict[str, Any],
    ) -> dict[str, Any]:
        path = self.store.evidence_dir(item_id) / "merge-resolution.json"
        _write_json(path, artifact)
        record = {
            "item": item_id,
            "state": "conflict",
            "kind": "conflict",
            "integration_path": str(integration),
            "target_ref": artifact["target_ref"],
            "target_head": artifact["ours"],
            "implementation_commit": artifact["theirs"],
            "result_commit": artifact.get("resolution_commit"),
            "artifact": "merge-resolution.json",
            "artifact_sha256": file_hash(path),
            "conflict_analysis_sha256": _conflict_analysis_hash(artifact),
            "initial_resolution_commit": artifact.get("resolution_commit"),
            "prepared_at": now(),
        }
        self.store.put_runtime_record("merge_jobs", item_id, record)
        current = self.store.queue_item(item_id)
        if current.version != merging_version or \
                current.data["state"] != "merging":
            raise StateConflict(
                f"{item_id} changed while conflict analysis was running")
        replacement = dict(current.data)
        replacement["state"] = "merge-conflict"
        replacement.setdefault("history", []).append({
            "state": "merge-conflict", "at": now(),
            "semantic_invariant_violation":
                artifact["semantic_invariant_violation"],
        })
        self.store.update_queue_item(
            item_id, replacement, current.version, "merging",
            action="merge-conflict",
            detail={
                "paths": artifact["conflict_paths"],
                "semantic_invariant_violation":
                    artifact["semantic_invariant_violation"],
            },
        )
        return artifact

    def _try_disjoint_resolution(
        self, integration: Path, base: str, ours: str, theirs: str,
        conflict_paths: list[str], ours_report: dict[str, Any],
        theirs_report: dict[str, Any],
    ) -> str | None:
        if not conflict_paths or any(
                Path(path).suffix.lower() not in (".py", ".pyi")
                for path in conflict_paths):
            return None
        resolved: dict[str, str] = {}
        for path in conflict_paths:
            ours_targets = _targets_for_path(ours_report, path)
            theirs_targets = _targets_for_path(theirs_report, path)
            if not ours_targets or not theirs_targets or any(
                    target["type"] != "symbol"
                    for target in ours_targets + theirs_targets):
                return None
            ours_names = {
                target["qualified_symbol"] for target in ours_targets}
            theirs_names = {
                target["qualified_symbol"] for target in theirs_targets}
            values: list[str] = []
            for commit in (base, ours, theirs):
                shown = git(
                    integration, ["show", f"{commit}:{path}"], check=False)
                if shown.returncode:
                    return None
                values.append(shown.stdout)
            try:
                resolved[path] = replace_disjoint_python_symbols(
                    values[0], values[1], values[2], path,
                    ours_names, theirs_names,
                )
            except (SyntaxError, ValueError):
                return None
        for path, text in resolved.items():
            destination = integration / path
            destination.write_text(text, encoding="utf-8")
            git(integration, ["add", "--", path])
        if git(
                integration, ["diff", "--name-only", "--diff-filter=U"]
                ).stdout.strip():
            return None
        git(integration, [
            "commit", "--quiet", "-m",
            "Resolve semantically disjoint Python merge conflict",
        ])
        return git(integration, ["rev-parse", "HEAD"]).stdout.strip()

    def _validate_resolution(
        self, item_id: str, record: dict[str, Any],
    ) -> tuple[dict[str, Any], str, dict[str, Any]]:
        path = self.store.evidence_dir(item_id) / "merge-resolution.json"
        value = load_llm_json(path)
        if value.get("item") != item_id:
            raise ValueError("merge-resolution.json.item mismatch")
        analysis_hash = record.get("conflict_analysis_sha256")
        if not analysis_hash:
            raise ValueError(
                "merge conflict analysis predates immutable sealing; run "
                "'merge retry' before accepting a resolution")
        if _conflict_analysis_hash(value) != analysis_hash:
            raise ValueError(
                "merge-resolution.json conflict analysis was tampered; only "
                "resolution_commit and code_review may be completed")
        if value.get("semantic_invariant_violation"):
            raise ValueError(
                "semantic lease invariant violation: Merge Agent must not "
                "guess; retry after serialization or architect reshape")
        validate_merge_artifact(
            self.store.evidence_dir(item_id),
            item_id,
            "merge-resolution.json",
            require_resolved=False,
        )
        if value.get("resolution_allowed") is not True:
            raise ValueError("merge-resolution.json does not allow resolution")
        required_string(value, "reasoning", "merge-resolution.json")
        result_commit = required_string(
            value, "resolution_commit", "merge-resolution.json")
        initial_resolution = record.get("initial_resolution_commit")
        if initial_resolution is not None and result_commit != initial_resolution:
            raise ValueError(
                "mechanical conflict resolution commit was replaced")
        review = value.get("code_review")
        if not isinstance(review, dict) or review.get("verdict") != "approve":
            raise ValueError(
                "conflict resolution requires code_review.verdict=approve")
        if review.get("reviewer") != "code-reviewer":
            raise ValueError(
                "merge resolution code_review.reviewer must be code-reviewer")
        if not isinstance(review.get("findings"), list) or any(
                finding.get("severity") == "blocking"
                for finding in review.get("findings", [])
                if isinstance(finding, dict)):
            raise ValueError(
                "merge resolution approval cannot contain blocking findings")
        parse_time(
            review.get("timestamp"), "merge-resolution.json.code_review.timestamp")
        integration = Path(record["integration_path"])
        head = git(integration, ["rev-parse", "HEAD"]).stdout.strip()
        if head != result_commit:
            raise ValueError(
                "merge-resolution.json.resolution_commit is not integration HEAD")
        unresolved = git(
            integration, ["diff", "--name-only", "--diff-filter=U"]
        ).stdout.strip()
        if unresolved:
            raise ValueError(
                "integration clone still has unresolved paths: " + unresolved)
        scope = validate_committed_scope(
            integration, record["target_head"], result_commit,
            self.store.leases(item_id),
        )
        if scope["verdict"] != "green":
            raise ValueError(
                "merge resolution changes semantic targets outside the lease")
        # Recompute rather than trusting an agent-authored scope claim.
        value["scope_validation"] = scope
        _write_json(path, value)
        validate_merge_artifact(
            self.store.evidence_dir(item_id),
            item_id,
            "merge-resolution.json",
            require_resolved=True,
        )
        return value, result_commit, scope

    def finalize(self, item_id: str) -> dict[str, Any]:
        versioned = self.store.queue_item(item_id)
        item = versioned.data
        runtime = self.store.runtime_record("merge_jobs", item_id)
        if runtime is None:
            raise ValueError(
                f"{item_id} has no merge preparation; run merge prepare")
        record = runtime.data
        if item["state"] == "merge-conflict":
            resolution, result_commit, scope = self._validate_resolution(
                item_id, record)
            replacement = dict(item)
            replacement["state"] = "post-merge-verifying"
            replacement["merge_result_commit"] = result_commit
            replacement.setdefault("history", []).append({
                "state": "post-merge-verifying",
                "at": now(),
                "merge_evidence": {
                    "file": "merge-resolution.json",
                    "sha256": file_hash(
                        self.store.evidence_dir(item_id) /
                        "merge-resolution.json"),
                },
            })
            next_version = self.store.update_queue_item(
                item_id, replacement, versioned.version, "merge-conflict",
                action="merge-resolution-approved",
                detail={"result_commit": result_commit},
            )
            item, versioned = replacement, type(versioned)(
                replacement, next_version)
            record["result_commit"] = result_commit
            record["artifact_sha256"] = file_hash(
                self.store.evidence_dir(item_id) / "merge-resolution.json")
            record["state"] = "resolved"
            self.store.put_runtime_record(
                "merge_jobs", item_id, record, runtime.version)
        elif item["state"] == "post-merge-verifying":
            result_commit = record.get("result_commit")
            if not result_commit:
                raise ValueError("merge job has no result commit")
        else:
            raise ValueError(
                "merge finalize requires post-merge-verifying or an approved "
                f"merge-conflict, not {item['state']}")

        integration = Path(record["integration_path"])
        manager = SandboxManager(self.store, integration)
        manager.prepare(item_id, result_commit)
        sandbox = manager.run(
            item_id, evidence_name="post-merge-sandbox.json")
        passed = all(
            command["exit_code"] == 0 for command in sandbox["commands"])
        verification = {
            "item": item_id,
            "verdict": "green" if passed else "red",
            "result_commit": result_commit,
            "target_head": record["target_head"],
            "sandbox_evidence_sha256": file_hash(
                self.store.evidence_dir(item_id) /
                "post-merge-sandbox.json"),
            "timestamp": now(),
        }
        verify_path = (
            self.store.evidence_dir(item_id) / "post-merge-verify.json")
        _write_json(verify_path, verification)
        if not passed:
            current = self.store.queue_item(item_id)
            failure_artifact = self._post_merge_failure_artifact(
                item_id, record, result_commit)
            artifact_path = (
                self.store.evidence_dir(item_id) /
                "merge-resolution.json")
            _write_json(artifact_path, failure_artifact)
            runtime = self.store.runtime_record("merge_jobs", item_id)
            if runtime is None:
                raise StateConflict(
                    f"{item_id} merge runtime disappeared after verification")
            failed_record = dict(runtime.data)
            failed_record.update({
                "state": "conflict",
                "kind": "post-merge-failure",
                "artifact": "merge-resolution.json",
                "artifact_sha256": file_hash(artifact_path),
                "conflict_analysis_sha256":
                    _conflict_analysis_hash(failure_artifact),
                "initial_resolution_commit": None,
                "result_commit": None,
            })
            self.store.put_runtime_record(
                "merge_jobs", item_id, failed_record, runtime.version)
            replacement = dict(current.data)
            replacement["state"] = "merge-conflict"
            replacement.setdefault("history", []).append({
                "state": "merge-conflict", "at": now(),
                "reason": "post-merge verification failed",
                "evidence": {
                    "file": "post-merge-verify.json",
                    "sha256": file_hash(verify_path),
                },
            })
            self.store.update_queue_item(
                item_id, replacement, current.version,
                "post-merge-verifying",
                action="post-merge-verification-failed", detail={})
            raise ValueError(
                "post-merge verification failed; target ref was not published")

        return self._publish(
            item_id, record, result_commit, verify_path)

    def _post_merge_failure_artifact(
        self, item_id: str, record: dict[str, Any], result_commit: str,
    ) -> dict[str, Any]:
        integration = Path(record["integration_path"])
        base = git(
            integration,
            ["merge-base", record["target_head"],
             record["implementation_commit"]],
        ).stdout.strip()
        ours_report = _map_or_empty(
            integration, base, record["target_head"])
        theirs_report = _map_or_empty(
            integration, base, record["implementation_commit"])
        return self._conflict_artifact(
            item_id,
            base,
            record["target_head"],
            record["implementation_commit"],
            record["target_ref"],
            [],
            ours_report,
            theirs_report,
            semantic_invariant=False,
            reasoning=(
                "post-merge sandbox verification failed; the target ref was "
                "not published. Merge Agent may amend only item-leased "
                "semantic targets and must obtain Code Reviewer approval"),
            result_commit=None,
            scope=validate_committed_scope(
                integration,
                record["target_head"],
                result_commit,
                self.store.leases(item_id),
            ),
        )

    def _publish(
        self, item_id: str, record: dict[str, Any],
        result_commit: str, verify_path: Path,
    ) -> dict[str, Any]:
        target_ref = record["target_ref"]
        expected = record["target_head"]
        current_head = git(
            self.repo, ["rev-parse", target_ref]).stdout.strip()
        if current_head != expected:
            self._cas_retry(item_id, current_head)
            raise RefCASRetry(
                f"target ref advanced from {expected} to {current_head}; "
                "item returned to merge-pending")
        symbolic = git(
            self.repo, ["symbolic-ref", "-q", "HEAD"], check=False)
        checked_out_target = (
            symbolic.returncode == 0 and symbolic.stdout.strip() == target_ref)
        if checked_out_target and (
                git(self.repo, ["diff", "--quiet"], check=False).returncode or
                git(self.repo, ["diff", "--cached", "--quiet"],
                    check=False).returncode):
            raise ValueError(
                "target worktree has tracked modifications; refusing atomic "
                "ref publication because it could desynchronize the checkout")
        integration = Path(record["integration_path"])
        git(self.repo, ["fetch", "--quiet", str(integration), result_commit])
        update = git(
            self.repo,
            ["update-ref", target_ref, result_commit, expected],
            check=False,
        )
        if update.returncode:
            current_head = git(
                self.repo, ["rev-parse", target_ref]).stdout.strip()
            self._cas_retry(item_id, current_head)
            raise RefCASRetry(
                "git update-ref compare-and-swap lost; item returned to "
                "merge-pending")
        if checked_out_target:
            git(self.repo, ["reset", "--hard", "--quiet", result_commit])
        current = self.store.queue_item(item_id)
        if current.data["state"] != "post-merge-verifying":
            raise StateConflict(
                f"{item_id} changed immediately after ref publication; "
                "audit/manual recovery required")
        replacement = dict(current.data)
        worktree = replacement.get("worktree")
        replacement.pop("worktree", None)
        replacement["state"] = "done"
        replacement["merge_commit"] = result_commit
        replacement.setdefault("history", []).append({
            "state": "done", "at": now(),
            "target_ref": target_ref,
            "expected_old": expected,
            "published_commit": result_commit,
            "evidence": {
                "file": "post-merge-verify.json",
                "sha256": file_hash(verify_path),
            },
        })
        self.store.complete_item(
            item_id, replacement, current.version,
            "post-merge-verifying")
        if worktree and Path(worktree).exists():
            git(self.repo, ["worktree", "remove", "--force", worktree])
        git(
            self.repo, ["branch", "-D", f"mc/{item_id}"], check=False)
        record["state"] = "published"
        record["published_at"] = now()
        record["published_commit"] = result_commit
        runtime = self.store.runtime_record("merge_jobs", item_id)
        if runtime is not None:
            self.store.put_runtime_record(
                "merge_jobs", item_id, record, runtime.version)
        return {
            "item": item_id,
            "target_ref": target_ref,
            "old": expected,
            "new": result_commit,
            "state": "done",
        }

    def _cas_retry(self, item_id: str, observed: str) -> None:
        current = self.store.queue_item(item_id)
        if current.data["state"] != "post-merge-verifying":
            return
        replacement = dict(current.data)
        retries = int(replacement.get("merge_cas_retries", 0)) + 1
        maximum = self._config()["max_cas_retries"]
        replacement["merge_cas_retries"] = retries
        replacement["state"] = "merge-pending"
        replacement.setdefault("history", []).append({
            "state": "merge-pending", "at": now(),
            "reason": "target-ref-cas-lost",
            "observed_target_head": observed,
            "retry": retries,
        })
        self.store.update_queue_item(
            item_id, replacement, current.version,
            "post-merge-verifying", action="merge-cas-retry",
            detail={"observed": observed, "retry": retries,
                    "retry_limit_reached": retries >= maximum})

    def retry(self, item_id: str) -> dict[str, Any]:
        current = self.store.queue_item(item_id)
        if current.data["state"] == "merge-conflict":
            replacement = dict(current.data)
            replacement["state"] = "merge-pending"
            replacement.setdefault("history", []).append({
                "state": "merge-pending", "at": now(),
                "reason": "explicit merge retry",
            })
            self.store.update_queue_item(
                item_id, replacement, current.version, "merge-conflict",
                action="merge-retry", detail={})
        elif current.data["state"] != "merge-pending":
            raise ValueError(
                f"merge retry requires merge-pending/conflict, not "
                f"{current.data['state']}")
        return self.prepare(item_id)

    def status(self, item_id: str) -> dict[str, Any]:
        item = self.store.queue_item(item_id)
        runtime = self.store.runtime_record("merge_jobs", item_id)
        return {
            "item": item_id,
            "queue_state": item.data["state"],
            "item_version": item.version,
            "merge_job": None if runtime is None else {
                **runtime.data, "version": runtime.version,
            },
        }
