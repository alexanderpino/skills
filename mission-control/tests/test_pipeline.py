import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "pipeline.py"
SCRATCH = HERE / ".tmp"


class PipelineTest(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.repo = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Mission Control Test")
        (self.repo / "seed.txt").write_text("seed\n", encoding="utf-8")
        self.git("add", "seed.txt")
        self.git("commit", "-qm", "seed")
        self.run_cli("init", "--goal", "test mission")
        self.run_cli(
            "configure", "--json",
            json.dumps({
                "repo_oracle": {
                    "build": "echo build",
                    "test": "echo test",
                    "lint": None,
                },
                "execution": {
                    "backend": "native",
                    "commands": ["echo build", "echo test"],
                },
            }),
        )

    def tearDown(self):
        self.temp.cleanup()
        if SCRATCH.exists() and not any(SCRATCH.iterdir()):
            SCRATCH.rmdir()

    def git(self, *args, cwd=None, check=True):
        return subprocess.run(
            ["git", *args], cwd=cwd or self.repo, text=True,
            capture_output=True, check=check
        )

    def run_cli(self, *args, ok=True):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", ".mc", *args],
            cwd=self.repo, text=True, capture_output=True
        )
        if ok and result.returncode:
            self.fail(
                f"command failed: {' '.join(args)}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def path(self, name):
        return self.repo / ".mc" / f"{name}.json"

    def load(self, name):
        self.run_cli("export-json", "--force")
        return json.loads(self.path(name).read_text(encoding="utf-8"))

    def save(self, name, value):
        database = self.repo / ".mc" / "state.db"
        connection = sqlite3.connect(database)
        try:
            if name in ("mission", "agenda", "investigations"):
                connection.execute(
                    "UPDATE documents SET data_json=?, version=version+1 "
                    "WHERE name=?",
                    (json.dumps(value, separators=(",", ":")), name),
                )
            elif name in ("queue", "backlog"):
                table = "queue_items" if name == "queue" else "backlog_items"
                state_column = "state" if name == "queue" else "status"
                for item in value["items"]:
                    clean = dict(item)
                    clean.pop("version", None)
                    connection.execute(
                        f"UPDATE {table} SET {state_column}=?, data_json=?, "
                        "version=version+1 WHERE id=?",
                        (
                            clean[state_column],
                            json.dumps(clean, separators=(",", ":")),
                            clean["id"],
                        ),
                    )
            elif name == "ledger":
                for lease in value["leases"]:
                    connection.execute(
                        "UPDATE leases SET acquired_at=?, ttl_minutes=? "
                        "WHERE item_id=? AND target_key=?",
                        (
                            lease["acquired"],
                            lease["ttl_minutes"],
                            lease["item"],
                            self._target_key(lease["target"]),
                        ),
                    )
            else:
                raise AssertionError(f"unsupported test fixture save: {name}")
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _target_key(target):
        return (
            f"{target['type']}:{target['path']}:"
            f"{target.get('qualified_symbol') or ''}"
        )

    def evidence(self, item, filename):
        return self.repo / ".mc" / "evidence" / item / filename

    @staticmethod
    def stamp():
        return datetime.now(timezone.utc).isoformat(timespec="microseconds")

    def add_and_claim(self, item="MC-1", blast="low", fast=False,
                      concurrency=False):
        args = ["add-item", item, "Test item"]
        if fast:
            args.append("--fast-track")
        self.run_cli(*args)
        self.run_cli("claim", item)
        if not fast:
            self.write_research(item, blast, concurrency)

    def write_research(self, item="MC-1", blast="low", concurrency=False):
        self.evidence(item, "research.md").write_text(
            f"""---
item: {item}
complexity: low
blast_radius: {blast}
touch_list:
  - change.txt
ui: false
splittable: false
concurrency: {'true' if concurrency else 'false'}
---

# Problem
Change the test file, grounded in `seed.txt:1`.

# Approach
Create the leased file and test it.

# Acceptance criteria
1. The file exists — check `test -f change.txt`.

# Risks & unknowns
None.
""",
            encoding="utf-8",
        )

    def write_plan(self, item="MC-1", verdict="sign-off"):
        checks = {
            "soundness": "pass",
            "testability": "pass",
            "routing_honesty": "pass",
            "scope": "pass",
        }
        if verdict == "bounce":
            checks["soundness"] = "fail: approach does not solve the item"
        self.evidence(item, "plan-review.json").write_text(
            json.dumps({
                "item": item,
                "reviewer": "plan-reviewer",
                "verdict": verdict,
                "checks": checks,
                "notes": "" if verdict == "sign-off" else "Fix the plan.",
                "timestamp": self.stamp(),
            }),
            encoding="utf-8",
        )

    def write_approval(self, item="MC-1", verdict="sign-off"):
        self.evidence(item, "approval.json").write_text(
            json.dumps({
                "item": item,
                "reviewer": "orchestrator",
                "verdict": verdict,
                "checks": {
                    "soundness": "pass",
                    "testability": "pass",
                    "routing_honesty": "pass",
                    "scope": "pass",
                },
                "notes": "High-blast reasoning is sound.",
                "timestamp": self.stamp(),
            }),
            encoding="utf-8",
        )

    def approve(self, item="MC-1", blast="low"):
        self.run_cli("transition", item, "plan-review")
        self.write_plan(item)
        if blast in ("high", "critical"):
            self.run_cli("transition", item, "orchestrator-approval")
            self.write_approval(item)
        self.run_cli("transition", item, "approved")

    def enter_build(self, item="MC-1", path="change.txt"):
        self.run_cli("lease", item, "--path", path)
        self.run_cli("worktree-add", item)
        self.run_cli("transition", item, "building")
        queue_item = next(
            x for x in self.load("queue")["items"] if x["id"] == item
        )
        worktree = Path(queue_item["worktree"])
        self.assertTrue(worktree.is_absolute())
        self.assertTrue(worktree.is_relative_to(self.repo))
        (worktree / path).parent.mkdir(parents=True, exist_ok=True)
        (worktree / path).write_text(f"changed by {item}\n", encoding="utf-8")
        self.git("add", path, cwd=worktree)
        self.git("commit", "-qm", f"implement {item}", cwd=worktree)
        self.evidence(item, "handoff.md").write_text(
            f"""---
item: {item}
implementer: senior
---

# Changed
Added `{path}`.

# Criteria status
1. pass — file exists.

# Judgment calls
None.

# Backlog suggestions
None.
""",
            encoding="utf-8",
        )
        self.run_cli("transition", item, "verifying")
        return worktree

    def write_verify(self, item="MC-1", verdict="green"):
        passed = verdict == "green"
        sandbox_hash = None
        if passed:
            self.run_cli("sandbox", "prepare", item, "--backend", "native")
            self.run_cli(
                "sandbox", "run", item,
                "--command", "echo build",
                "--command", "echo test",
            )
            sandbox_hash = hashlib.sha256(
                self.evidence(item, "sandbox.json").read_bytes()
            ).hexdigest()
        self.evidence(item, "verify.json").write_text(
            json.dumps({
                "item": item,
                "verdict": verdict,
                "build": {"command": "echo build", "pass": passed},
                "tests": {
                    "command": "echo test", "pass": passed,
                    "failures": [] if passed else ["failed"],
                },
                "criteria": [{
                    "n": 1, "pass": passed, "command": "test -f change.txt",
                    "output_excerpt": "ok" if passed else "missing",
                }],
                "diff_in_scope": True,
                "out_of_scope_paths": [],
                "oracle_tampering": False,
                "sandbox_evidence_sha256": sandbox_hash,
                "timestamp": self.stamp(),
            }),
            encoding="utf-8",
        )

    def write_code_review(self, item="MC-1", verdict="approve",
                          concurrency_reviewed=False):
        self.evidence(item, "code-review.json").write_text(
            json.dumps({
                "item": item,
                "verdict": verdict,
                "concurrency_reviewed": concurrency_reviewed,
                "findings": [],
                "judgment_calls_audited": True,
                "timestamp": self.stamp(),
            }),
            encoding="utf-8",
        )

    def finish(self, item="MC-1", blast="low",
               concurrency_reviewed=False):
        self.write_verify(item)
        if blast in ("medium", "high", "critical"):
            self.run_cli("transition", item, "code-review")
            self.write_code_review(item, concurrency_reviewed=concurrency_reviewed)
        self.run_cli("transition", item, "ready-to-merge")
        self.run_cli("merge", "prepare", item)
        self.run_cli("merge", "finalize", item)

    def valid_flow(self, blast="low", fast=False, concurrency=False):
        self.add_and_claim(blast=blast, fast=fast, concurrency=concurrency)
        if not fast:
            self.approve(blast=blast)
        self.enter_build()
        self.finish(blast=blast, concurrency_reviewed=concurrency)

    def prepare_python_merge(
        self, base_source, item_source, target_source, symbol,
        item="MC-1",
    ):
        module = self.repo / "module.py"
        module.write_text(base_source, encoding="utf-8")
        self.git("add", "module.py")
        self.git("commit", "-qm", "python base")
        self.add_and_claim(item, fast=True)
        self.run_cli("lease", item, "--symbol", f"module.py::{symbol}")
        self.run_cli("worktree-add", item)
        self.run_cli("transition", item, "building")
        queue_item = next(
            value for value in self.load("queue")["items"]
            if value["id"] == item
        )
        worktree = Path(queue_item["worktree"])
        (worktree / "module.py").write_text(item_source, encoding="utf-8")
        self.git("add", "module.py", cwd=worktree)
        self.git("commit", "-qm", f"implement {item}", cwd=worktree)
        self.evidence(item, "handoff.md").write_text(
            f"""---
item: {item}
implementer: senior
---

# Changed
Changed `{symbol}` in `module.py`.

# Criteria status
1. pass — Python source committed.

# Judgment calls
None.

# Backlog suggestions
None.
""",
            encoding="utf-8",
        )
        module.write_text(target_source, encoding="utf-8")
        self.git("add", "module.py")
        self.git("commit", "-qm", "advance target")
        self.run_cli("transition", item, "verifying")
        self.write_verify(item)
        self.run_cli("transition", item, "ready-to-merge")
        return worktree

    def test_valid_low_medium_high_and_fast_track_flows(self):
        for index, (blast, fast, concurrency) in enumerate([
                ("low", False, False), ("medium", False, False),
                ("high", False, True), ("low", True, False)], 1):
            with self.subTest(blast=blast, fast=fast):
                item = f"MC-{index}"
                self.add_and_claim(item, blast, fast, concurrency)
                if not fast:
                    self.approve(item, blast)
                self.enter_build(item)
                self.finish(item, blast, concurrency)
        audit = self.run_cli("audit")
        self.assertIn("0 hole(s)", audit.stdout)

    def test_plan_bounce_cannot_advance(self):
        self.add_and_claim()
        self.run_cli("transition", "MC-1", "plan-review")
        self.write_plan(verdict="bounce")
        result = self.run_cli("transition", "MC-1", "approved", ok=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("verdict must be sign-off", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_red_verification_cannot_advance(self):
        self.add_and_claim()
        self.approve()
        self.enter_build()
        self.write_verify(verdict="red")
        result = self.run_cli(
            "transition", "MC-1", "ready-to-merge", ok=False
        )
        self.assertIn("verdict must be green", result.stderr)

    def test_stale_evidence_is_rejected(self):
        self.add_and_claim()
        research = self.evidence("MC-1", "research.md")
        stale = time.time() - 30
        os.utime(research, (stale, stale))
        result = self.run_cli(
            "transition", "MC-1", "plan-review", ok=False
        )
        self.assertIn("stale", result.stderr)

    def test_unchanged_evidence_cannot_be_reused_after_bounce(self):
        self.add_and_claim()
        self.run_cli("transition", "MC-1", "plan-review")
        self.write_plan(verdict="bounce")
        self.run_cli("transition", "MC-1", "researching")
        result = self.run_cli(
            "transition", "MC-1", "plan-review", ok=False
        )
        self.assertIn("unchanged from the previous gate attempt", result.stderr)

    def test_malformed_blast_metadata_fails_cleanly(self):
        self.add_and_claim()
        research = self.evidence("MC-1", "research.md")
        research.write_text(
            research.read_text(encoding="utf-8").replace(
                "blast_radius: low", "blast_radius: enormous"
            ),
            encoding="utf-8",
        )
        result = self.run_cli(
            "transition", "MC-1", "plan-review", ok=False
        )
        self.assertIn("blast_radius", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_build_requires_lease_and_worktree(self):
        self.add_and_claim(fast=True)
        missing_lease = self.run_cli(
            "transition", "MC-1", "building", ok=False
        )
        self.assertIn("hold leases", missing_lease.stderr)
        self.run_cli("lease", "MC-1", "--path", "change.txt")
        missing_tree = self.run_cli(
            "transition", "MC-1", "building", ok=False
        )
        self.assertIn("must have a worktree", missing_tree.stderr)

    def test_path_normalization_traversal_and_directory_conflict(self):
        self.add_and_claim("MC-1", fast=True)
        self.add_and_claim("MC-2", fast=True)
        traversal = self.run_cli(
            "lease", "MC-1", "--path", "../outside", ok=False
        )
        self.assertIn("traverse", traversal.stderr)
        absolute = self.run_cli(
            "lease", "MC-1", "--path", str(self.repo / "x"), ok=False
        )
        self.assertIn("absolute", absolute.stderr)
        self.run_cli("lease", "MC-1", "--path", "src/./shared")
        collision = self.run_cli(
            "lease", "MC-2", "--path", "src/shared/child.py", ok=False
        )
        self.assertEqual(collision.returncode, 2)
        self.assertIn("conflict", collision.stderr)

    def test_concurrent_independent_cli_transitions_do_not_lose_updates(self):
        for item in ("MC-1", "MC-2"):
            self.add_and_claim(item)
            self.run_cli("transition", item, "plan-review")
            self.run_cli("transition", item, "blocked")
        barrier = threading.Barrier(2)

        def resume(item):
            barrier.wait()
            return subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--root",
                    ".mc",
                    "transition",
                    item,
                    "researching",
                ],
                cwd=self.repo,
                text=True,
                capture_output=True,
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(resume, ("MC-1", "MC-2")))
        self.assertEqual([result.returncode for result in results], [0, 0])
        states = {
            item["id"]: item["state"] for item in self.load("queue")["items"]
        }
        self.assertEqual(states, {"MC-1": "researching", "MC-2": "researching"})

    def test_sibling_python_symbol_leases_can_coexist(self):
        (self.repo / "module.py").write_text(
            "def left(): return 1\n"
            "def right(): return 2\n",
            encoding="utf-8",
        )
        self.git("add", "module.py")
        self.git("commit", "-qm", "add sibling functions")
        self.add_and_claim("MC-1", fast=True)
        self.add_and_claim("MC-2", fast=True)
        self.run_cli("lease", "MC-1", "--symbol", "module.py::left")
        self.run_cli("lease", "MC-2", "--symbol", "module.py::right")
        leases = self.load("ledger")["leases"]
        self.assertEqual(len(leases), 2)
        self.assertEqual(
            {lease["target"]["qualified_symbol"] for lease in leases},
            {"left", "right"},
        )

    def test_build_requires_full_touch_list_lease(self):
        self.add_and_claim()
        research = self.evidence("MC-1", "research.md")
        research.write_text(
            research.read_text(encoding="utf-8").replace(
                "  - change.txt", "  - change.txt\n  - second.txt"
            ),
            encoding="utf-8",
        )
        self.approve()
        self.run_cli("lease", "MC-1", "--path", "change.txt")
        self.run_cli("worktree-add", "MC-1")
        result = self.run_cli(
            "transition", "MC-1", "building", ok=False
        )
        self.assertIn("does not hold leases covering its touch_list", result.stderr)
        self.assertIn("second.txt", result.stderr)

    def test_active_build_lease_cannot_be_released(self):
        self.add_and_claim(fast=True)
        self.run_cli("lease", "MC-1", "--path", "change.txt")
        self.run_cli("worktree-add", "MC-1")
        self.run_cli("transition", "MC-1", "building")
        result = self.run_cli("release", "MC-1", ok=False)
        self.assertIn("cannot release", result.stderr)
        self.assertEqual(len(self.load("ledger")["leases"]), 1)

    def test_committed_diff_must_stay_inside_lease(self):
        self.add_and_claim(fast=True)
        self.run_cli("lease", "MC-1", "--path", "change.txt")
        self.run_cli("worktree-add", "MC-1")
        self.run_cli("transition", "MC-1", "building")
        item = self.load("queue")["items"][0]
        worktree = Path(item["worktree"])
        (worktree / "other.txt").write_text("outside\n", encoding="utf-8")
        self.git("add", "other.txt", cwd=worktree)
        self.git("commit", "-qm", "out of scope", cwd=worktree)
        self.evidence("MC-1", "handoff.md").write_text(
            """---
item: MC-1
implementer: senior
---

# Changed
Changed an unleased path.

# Criteria status
1. pass.

# Judgment calls
None.

# Backlog suggestions
None.
""",
            encoding="utf-8",
        )
        result = self.run_cli(
            "transition", "MC-1", "verifying", ok=False
        )
        self.assertIn("outside the lease", result.stderr)
        self.assertIn("other.txt", result.stderr)

    def test_complete_requires_merge_and_updates_backlog(self):
        self.add_and_claim(fast=True)
        self.enter_build()
        self.write_verify()
        self.run_cli("transition", "MC-1", "ready-to-merge")
        premature = self.run_cli("complete", "MC-1", ok=False)
        self.assertIn("not merged", premature.stderr)
        self.run_cli("merge", "prepare", "MC-1")
        self.run_cli("merge", "finalize", "MC-1")
        self.assertEqual(self.load("queue")["items"][0]["state"], "done")
        self.assertEqual(self.load("backlog")["items"][0]["status"], "done")
        self.assertNotIn("worktree", self.load("queue")["items"][0])

    def test_ready_to_merge_cannot_discard_worktree(self):
        self.add_and_claim(fast=True)
        self.enter_build()
        self.write_verify()
        self.run_cli("transition", "MC-1", "ready-to-merge")
        result = self.run_cli(
            "worktree-remove", "MC-1", "--force", ok=False
        )
        self.assertIn("cannot bypass completion", result.stderr)

    def test_verification_requires_committed_diff(self):
        self.add_and_claim(fast=True)
        self.run_cli("lease", "MC-1", "--path", "change.txt")
        self.run_cli("worktree-add", "MC-1")
        self.run_cli("transition", "MC-1", "building")
        self.evidence("MC-1", "handoff.md").write_text(
            """---
item: MC-1
implementer: senior
---
# Changed
Nothing.
# Criteria status
1. pass.
# Judgment calls
# Backlog suggestions
""",
            encoding="utf-8",
        )
        result = self.run_cli(
            "transition", "MC-1", "verifying", ok=False
        )
        self.assertIn("committed diff", result.stderr)

    def test_token_budget_and_deadline_terminal_signals(self):
        self.add_and_claim(fast=True)
        queue = self.load("queue")
        queue["items"][0]["history"][0]["tokens"] = 12
        self.save("queue", queue)
        mission = self.load("mission")
        mission["terminal_conditions"]["token_budget"] = 10
        mission["terminal_conditions"]["deadline"] = (
            datetime.now(timezone.utc) - timedelta(minutes=1)
        ).isoformat()
        self.save("mission", mission)
        status = self.run_cli("status")
        self.assertIn("token_budget reached", status.stdout)
        self.assertIn("deadline reached", status.stdout)
        self.assertNotIn("MISSION COMPLETE", status.stdout)
        blocked = self.run_cli(
            "add-item", "MC-2", "Must not spawn", ok=True
        )
        self.assertEqual(blocked.returncode, 0)
        claim = self.run_cli("claim", "MC-2", ok=False)
        self.assertIn("terminal condition reached", claim.stderr)

    def test_empty_initialized_pipeline_is_not_complete(self):
        status = self.run_cli("status")
        self.assertNotIn("MISSION COMPLETE", status.stdout)

    def test_plan_side_block_cannot_resume_at_approved(self):
        self.add_and_claim()
        self.run_cli("transition", "MC-1", "plan-review")
        self.run_cli("transition", "MC-1", "blocked")
        result = self.run_cli(
            "transition", "MC-1", "approved", ok=False
        )
        self.assertIn("plan-side blocks must return to researching", result.stderr)

    def diagnosis(self, inv="INV-1"):
        self.evidence(inv, "diagnosis.md").write_text(
            f"""---
investigation: {inv}
verdict: root-cause-found
root_cause_items: []
recommended_disposition: fix
---

# Symptom
A symptom.

# Reproduction
Reproduced with a command.

# Root cause
Found at `seed.txt:1`.

# Recommended disposition
Create a fix item.
""",
            encoding="utf-8",
        )

    def test_audit_fails_for_open_investigation(self):
        self.run_cli("investigate", "open", "INV-1", "broken")
        result = self.run_cli("audit", ok=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("investigation is still open", result.stdout)

    def test_investigation_fix_requires_matching_origin(self):
        self.run_cli("investigate", "open", "INV-1", "broken")
        self.diagnosis()
        self.run_cli("add-item", "MC-1", "Fix", "--origin", "architect")
        result = self.run_cli(
            "investigate", "close", "INV-1", "--disposition", "fix",
            "--item", "MC-1", ok=False
        )
        self.assertIn("requires backlog origin", result.stderr)

    def test_audit_detects_evidence_tampering(self):
        self.valid_flow()
        verify = self.evidence("MC-1", "verify.json")
        value = json.loads(verify.read_text(encoding="utf-8"))
        value["build"]["command"] = "tampered build"
        verify.write_text(json.dumps(value), encoding="utf-8")
        result = self.run_cli("audit", ok=False)
        self.assertIn("changed after its gate accepted it", result.stdout)

    def test_reclaim_preserves_and_reuses_unmerged_worktree(self):
        self.add_and_claim(fast=True)
        self.run_cli("lease", "MC-1", "--path", "change.txt")
        self.run_cli("worktree-add", "MC-1")
        self.run_cli("transition", "MC-1", "building")
        queue = self.load("queue")
        worktree = queue["items"][0]["worktree"]
        ledger = self.load("ledger")
        ledger["leases"][0]["acquired"] = (
            datetime.now(timezone.utc) - timedelta(hours=2)
        ).isoformat()
        self.save("ledger", ledger)
        reclaimed = self.run_cli("reclaim")
        self.assertIn("worktree preserved", reclaimed.stdout)
        self.assertTrue(Path(worktree).exists())
        self.assertEqual(self.load("queue")["items"][0]["state"], "approved")
        self.run_cli("lease", "MC-1", "--path", "change.txt")
        reused = self.run_cli("worktree-add", "MC-1")
        self.assertIn("reusing preserved worktree", reused.stdout)

    def test_concurrency_review_only_for_flagged_items(self):
        self.valid_flow(blast="medium", concurrency=False)
        self.assertEqual(self.run_cli("audit").returncode, 0)

    def test_code_review_approval_rejects_blocking_findings(self):
        self.add_and_claim(blast="medium")
        self.approve(blast="medium")
        self.enter_build()
        self.write_verify()
        self.run_cli("transition", "MC-1", "code-review")
        self.write_code_review()
        review = self.evidence("MC-1", "code-review.json")
        value = json.loads(review.read_text(encoding="utf-8"))
        value["findings"] = [{
            "severity": "blocking",
            "location": "change.txt:1",
            "defect": "A blocking defect remains.",
            "standard_violated": "Acceptance criterion 1",
        }]
        review.write_text(json.dumps(value), encoding="utf-8")
        result = self.run_cli(
            "transition", "MC-1", "ready-to-merge", ok=False
        )
        self.assertIn("cannot contain blocking findings", result.stderr)

    def test_clean_merge_records_evidence_and_publishes(self):
        self.valid_flow()
        merge = json.loads(
            self.evidence("MC-1", "merge.json").read_text(encoding="utf-8"))
        self.assertEqual(merge["kind"], "clean")
        self.assertEqual(merge["scope_validation"]["verdict"], "green")
        self.assertTrue(
            self.evidence("MC-1", "post-merge-verify.json").is_file())
        queue = self.load("queue")["items"][0]
        self.assertEqual(queue["state"], "done")
        self.assertEqual(
            self.git("rev-parse", queue["target_ref"]).stdout.strip(),
            queue["merge_commit"],
        )

    def test_disjoint_symbols_in_textual_conflict_are_combined_and_reviewed(self):
        self.prepare_python_merge(
            'def left(): return "base-left"\n'
            'def right(): return "base-right"\n',
            'def left(): return "base-left"\n'
            'def right(): return "item-right"\n',
            'def left(): return "target-left"\n'
            'def right(): return "base-right"\n',
            "right",
        )
        prepared = self.run_cli("merge", "prepare", "MC-1")
        artifact = json.loads(prepared.stdout)
        self.assertFalse(artifact["semantic_invariant_violation"])
        self.assertTrue(artifact["resolution_allowed"])
        self.assertIsNotNone(artifact["resolution_commit"])
        self.assertEqual(
            self.load("queue")["items"][0]["state"], "merge-conflict")
        artifact["code_review"] = {
            "verdict": "approve",
            "reviewer": "code-reviewer",
            "findings": [],
            "timestamp": self.stamp(),
        }
        self.evidence("MC-1", "merge-resolution.json").write_text(
            json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
        self.run_cli("merge", "finalize", "MC-1")
        result = (self.repo / "module.py").read_text(encoding="utf-8")
        self.assertIn("target-left", result)
        self.assertIn("item-right", result)

    def test_same_symbol_merge_is_rejected_and_analysis_is_immutable(self):
        self.prepare_python_merge(
            'def shared():\n    return "base"\n',
            'def shared():\n    return "item"\n',
            'def shared():\n    return "target"\n',
            "shared",
        )
        prepared = self.run_cli("merge", "prepare", "MC-1")
        artifact = json.loads(prepared.stdout)
        self.assertTrue(artifact["semantic_invariant_violation"])
        self.assertFalse(artifact["resolution_allowed"])
        rejected = self.run_cli("merge", "finalize", "MC-1", ok=False)
        self.assertIn("must not guess", rejected.stderr)

        artifact["semantic_invariant_violation"] = False
        artifact["resolution_allowed"] = True
        artifact["resolution_commit"] = self.git(
            "-C",
            str(self.repo / ".mc" / "integration" / "MC-1"),
            "rev-parse",
            "HEAD",
        ).stdout.strip()
        artifact["code_review"] = {
            "verdict": "approve",
            "reviewer": "code-reviewer",
            "findings": [],
            "timestamp": self.stamp(),
        }
        self.evidence("MC-1", "merge-resolution.json").write_text(
            json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
        tampered = self.run_cli("merge", "finalize", "MC-1", ok=False)
        self.assertIn("conflict analysis was tampered", tampered.stderr)
        self.assertEqual(
            self.load("queue")["items"][0]["state"], "merge-conflict")

    def test_post_merge_failure_does_not_publish_and_requires_resolution(self):
        self.add_and_claim(fast=True)
        self.enter_build()
        self.write_verify()
        self.run_cli("transition", "MC-1", "ready-to-merge")
        before = self.git("rev-parse", "HEAD").stdout.strip()
        self.run_cli("merge", "prepare", "MC-1")
        failing = f'"{sys.executable}" -c "import sys;sys.exit(7)"'
        self.run_cli(
            "configure",
            "--json",
            json.dumps({"execution": {"commands": [failing]}}),
        )
        result = self.run_cli("merge", "finalize", "MC-1", ok=False)
        self.assertIn("post-merge verification failed", result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), before)
        self.assertEqual(
            self.load("queue")["items"][0]["state"], "merge-conflict")
        post = json.loads(
            self.evidence("MC-1", "post-merge-verify.json").read_text(
                encoding="utf-8"))
        self.assertEqual(post["verdict"], "red")
        resolution = json.loads(
            self.evidence("MC-1", "merge-resolution.json").read_text(
                encoding="utf-8"))
        self.assertTrue(resolution["resolution_allowed"])
        self.assertFalse(resolution["semantic_invariant_violation"])

    def test_target_ref_cas_loss_requeues_then_retries(self):
        self.add_and_claim(fast=True)
        self.enter_build()
        self.write_verify()
        self.run_cli("transition", "MC-1", "ready-to-merge")
        self.run_cli("merge", "prepare", "MC-1")
        (self.repo / "advance.txt").write_text("advance\n", encoding="utf-8")
        self.git("add", "advance.txt")
        self.git("commit", "-qm", "advance while merge verifies")
        advanced = self.git("rev-parse", "HEAD").stdout.strip()
        lost = self.run_cli("merge", "finalize", "MC-1", ok=False)
        self.assertEqual(lost.returncode, 2)
        self.assertIn("target ref advanced", lost.stderr)
        item = self.load("queue")["items"][0]
        self.assertEqual(item["state"], "merge-pending")
        self.assertEqual(item["merge_cas_retries"], 1)
        self.assertEqual(
            self.git("rev-parse", "HEAD").stdout.strip(), advanced)
        self.run_cli("merge", "retry", "MC-1")
        self.run_cli("merge", "finalize", "MC-1")
        self.assertEqual(self.load("queue")["items"][0]["state"], "done")

    def test_audit_detects_semantic_sandbox_and_merge_tampering(self):
        self.valid_flow()
        for filename in (
            "semantic-scope.json", "sandbox.json", "merge.json",
        ):
            with self.subTest(filename=filename):
                path = self.evidence("MC-1", filename)
                original = path.read_bytes()
                value = json.loads(original)
                value["tampered"] = True
                path.write_text(json.dumps(value), encoding="utf-8")
                try:
                    result = self.run_cli("audit", ok=False)
                    self.assertIn("HOLE MC-1", result.stdout)
                    self.assertIn(filename, result.stdout)
                finally:
                    path.write_bytes(original)
        self.assertEqual(self.run_cli("audit").returncode, 0)


if __name__ == "__main__":
    unittest.main()
