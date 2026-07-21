import contextlib
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
WAIT_IN_LINE = SCRIPTS / "wait-in-line.py"
SCRATCH = HERE / ".tmp"
sys.path.insert(0, str(SCRIPTS))

from mission_control.evidence import validate_sandbox
from mission_control.merge import MergeCoordinator
from mission_control.models import LeaseConflict, StateConflict, now
from mission_control.sandbox import CommandResult, SandboxManager
from mission_control.semantic import (
    SemanticRegistry,
    map_committed_diff,
    targets_conflict,
    validate_committed_scope,
)
from mission_control.store import MissionStore


def mission(execution=None):
    return {
        "goal": "test mission",
        "created": now(),
        "terminal_conditions": {
            "backlog_drained": True,
            "max_items_completed": None,
            "token_budget": None,
            "deadline": None,
        },
        "concurrency": {
            "implementers": 2,
            "scouts": 2,
            "investigators": 1,
        },
        "throughput": {
            "maximize": True,
            "decided_by": "orchestrator",
            "reason": "exercise independent work",
        },
        "lease_ttl_minutes": 90,
        "bounce_limit": 3,
        "repo_oracle": {
            "build": "echo build",
            "test": "echo test",
            "lint": None,
        },
        "execution": execution or {
            "backend": "native",
            "commands": ["echo build", "echo test"],
            "artifact_paths": [],
        },
        "merge": {"target_ref": None, "max_cas_retries": 3},
        "gates": {
            "orchestrator_approval_min_blast": "high",
            "code_review_min_blast": "medium",
        },
    }


def file_target(path):
    return {
        "path": path,
        "type": "file",
        "qualified_symbol": None,
        "node_kind": "file",
        "base_blob": None,
        "base_commit": None,
        "structural_anchor_hash": None,
        "adapter": "test",
    }


class TempCase(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()
        if SCRATCH.exists() and not any(SCRATCH.iterdir()):
            SCRATCH.rmdir()


class MergePublicationTest(TempCase):
    def test_state_conflict_does_not_destroy_worktree_or_branch(self):
        worktree = self.root / "worktree"
        worktree.mkdir()
        verify_path = self.root / "post-merge-verify.json"
        verify_path.write_text("{}\n", encoding="utf-8")
        current = SimpleNamespace(
            data={
                "state": "post-merge-verifying",
                "worktree": str(worktree),
                "history": [],
            },
            version=7,
        )

        class ConflictingStore:
            def queue_item(self, _item_id):
                return current

            def complete_item(self, *_args):
                raise StateConflict("concurrent transition")

        calls = []

        def fake_git(_repo, args, *, check=True):
            calls.append(args)
            if args[:2] == ["rev-parse", "refs/heads/main"]:
                return SimpleNamespace(
                    returncode=0, stdout="expected\n", stderr="")
            if args[:3] == ["symbolic-ref", "-q", "HEAD"]:
                return SimpleNamespace(returncode=1, stdout="", stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        coordinator = MergeCoordinator(ConflictingStore(), self.root)
        record = {
            "target_ref": "refs/heads/main",
            "target_head": "expected",
            "integration_path": str(self.root / "integration"),
        }
        with mock.patch("mission_control.merge.git", side_effect=fake_git):
            with self.assertRaises(StateConflict):
                coordinator._publish(
                    "MC-1", record, "result", verify_path)

        self.assertTrue(worktree.exists())
        self.assertFalse(any(
            args[:2] in (["worktree", "remove"], ["branch", "-D"])
            for args in calls
        ))


class StoreConcurrencyTest(TempCase):
    def make_items(self):
        store = MissionStore.initialize(self.root / ".mc", mission())
        connection = sqlite3.connect(store.db_path)
        try:
            journal_mode = connection.execute(
                "PRAGMA journal_mode").fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(journal_mode.lower(), "wal")
        for item_id in ("MC-A", "MC-B"):
            store.add_backlog_item({
                "id": item_id,
                "title": item_id,
                "priority": 1,
                "depends_on": [],
                "ui": False,
                "fast_track": True,
                "constraints": [],
                "origin": "architect",
                "status": "open",
            })
            backlog = store.backlog_item(item_id)
            store.claim_item(item_id, backlog.version, {
                "id": item_id,
                "state": "approved",
                "history": [{"state": "approved", "at": now()}],
            })
        return store

    def test_concurrent_independent_item_updates_have_no_lost_update(self):
        store = self.make_items()
        barrier = threading.Barrier(2)

        def advance(item_id):
            local = MissionStore(store.root)
            observed = local.queue_item(item_id)
            replacement = dict(observed.data)
            replacement["state"] = "building"
            replacement["marker"] = item_id
            barrier.wait()
            local.update_queue_item(
                item_id,
                replacement,
                observed.version,
                "approved",
                action="concurrency-test",
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(advance, ("MC-A", "MC-B")))
        rows = {row["id"]: row for row in store.rows("queue_items")}
        self.assertEqual(rows["MC-A"]["marker"], "MC-A")
        self.assertEqual(rows["MC-B"]["marker"], "MC-B")
        self.assertEqual(
            {rows["MC-A"]["state"], rows["MC-B"]["state"]}, {"building"})

    def test_same_item_stale_version_is_rejected_by_cas(self):
        store = self.make_items()
        first = store.queue_item("MC-A")
        replacement = dict(first.data)
        replacement["marker"] = "winner"
        store.update_queue_item(
            "MC-A", replacement, first.version, "approved",
            action="cas-winner")
        stale = dict(first.data)
        stale["marker"] = "loser"
        with self.assertRaises(StateConflict):
            store.update_queue_item(
                "MC-A", stale, first.version, "approved",
                action="cas-loser")
        self.assertEqual(store.queue_item("MC-A").data["marker"], "winner")

    def test_concurrent_conflicting_lease_sets_are_atomic(self):
        store = self.make_items()
        barrier = threading.Barrier(2)

        def acquire(item_id):
            local = MissionStore(store.root)
            observed = local.queue_item(item_id)
            barrier.wait()
            try:
                local.acquire_leases(
                    item_id,
                    [file_target("shared.py")],
                    observed.version,
                    90,
                    targets_conflict,
                )
                return "acquired"
            except LeaseConflict:
                return "conflict"

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(acquire, ("MC-A", "MC-B")))
        self.assertCountEqual(results, ["acquired", "conflict"])
        leases = store.leases()
        self.assertEqual(len(leases), 1)
        self.assertIn(leases[0]["item"], ("MC-A", "MC-B"))


class MigrationTest(TempCase):
    def test_migration_backup_idempotence_and_noncanonical_json(self):
        state = self.root / ".mc"
        state.mkdir()
        values = {
            "mission": mission(),
            "backlog": {"items": []},
            "queue": {"items": []},
            "ledger": {"leases": [], "contention": []},
            "agenda": {"next_id": 1, "notes": []},
            "investigations": {"items": []},
        }
        originals = {}
        for name, value in values.items():
            path = state / f"{name}.json"
            path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
            originals[name] = path.read_bytes()

        store = MissionStore(state)
        backup = state / "migration-backup" / "legacy-json-v1"
        self.assertTrue((state / "state.db").is_file())
        for name, content in originals.items():
            self.assertEqual((backup / f"{name}.json").read_bytes(), content)

        second = MissionStore(state)
        self.assertIn("migration_complete", second.migration_info())
        (state / "mission.json").write_text(
            '{"goal":"manual JSON edit"}\n', encoding="utf-8")
        self.assertEqual(store.document("mission").data["goal"], "test mission")
        with self.assertRaisesRegex(ValueError, "read-only compatibility"):
            store.export_json()
        store.export_json(force=True)
        exported = json.loads(
            (state / "mission.json").read_text(encoding="utf-8"))
        self.assertEqual(exported["goal"], "test mission")


class SemanticTest(TempCase):
    def git(self, *args):
        return subprocess.run(
            ["git", *args],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()

    def init_repo(self, source):
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Mission Control Test")
        (self.root / "module.py").write_text(source, encoding="utf-8")
        self.git("add", "module.py")
        self.git("commit", "-qm", "base")
        return self.git("rev-parse", "HEAD")

    def test_semantic_conflict_hierarchy_and_sibling_concurrency(self):
        registry = SemanticRegistry()
        source = (
            b"class Box:\n"
            b"    def left(self): return 1\n"
            b"    def right(self): return 2\n"
            b"\n"
            b"def sibling(): return 3\n"
        )
        index = registry.index_bytes(
            "module.py", source, commit="base")
        targets = {
            target["qualified_symbol"]: target
            for target in index.targets
            if target["type"] == "symbol"
        }
        self.assertFalse(
            targets_conflict(targets["Box.left"], targets["Box.right"]))
        self.assertTrue(
            targets_conflict(targets["Box"], targets["Box.left"]))
        self.assertTrue(
            targets_conflict(targets["Box.left"], targets["Box.left"]))

        synthetics = {
            target["qualified_symbol"]: target
            for target in index.targets
            if target["type"] == "synthetic"
        }
        self.assertTrue(
            targets_conflict(synthetics["imports"], synthetics["imports"]))
        self.assertFalse(
            targets_conflict(synthetics["imports"], targets["sibling"]))
        changed = registry.index_bytes(
            "module.py",
            source.replace(b"return 1", b"return 99"),
            commit="result",
        )
        changed_left = next(
            target for target in changed.targets
            if target.get("qualified_symbol") == "Box.left")
        self.assertEqual(
            targets["Box.left"]["structural_anchor_hash"],
            changed_left["structural_anchor_hash"],
        )

    def test_unsupported_language_falls_back_to_file(self):
        index = SemanticRegistry().index_bytes(
            "asset.xyz", b"not semantically indexed", commit="base")
        self.assertTrue(index.fallback)
        self.assertEqual(index.targets[0]["type"], "file")
        self.assertIn("file lease required", index.diagnostics[0])

    def test_ast_diff_rejects_out_of_lease_symbol(self):
        base = self.init_repo(
            "def left():\n    return 1\n\n"
            "def right():\n    return 2\n")
        registry = SemanticRegistry()
        left = registry.resolve(
            self.root, "module.py", "symbol", "left", commit=base)
        (self.root / "module.py").write_text(
            "def left():\n    return 1\n\n"
            "def right():\n    return 99\n",
            encoding="utf-8",
        )
        self.git("add", "module.py")
        self.git("commit", "-qm", "change right")
        result = self.git("rev-parse", "HEAD")
        report = validate_committed_scope(
            self.root, base, result, [{"target": left}])
        self.assertEqual(report["verdict"], "red")
        self.assertEqual(
            report["uncovered_targets"][0]["qualified_symbol"], "right")

    def test_new_deleted_and_renamed_nodes_are_mapped(self):
        base = self.init_repo("def old():\n    return 1\n")
        (self.root / "module.py").write_text(
            "def renamed():\n    return 1\n\ndef added():\n    return 2\n",
            encoding="utf-8",
        )
        self.git("add", "module.py")
        self.git("commit", "-qm", "rename and add")
        middle = self.git("rev-parse", "HEAD")
        first = map_committed_diff(self.root, base, middle)
        changes = {
            (target["type"], target["qualified_symbol"], target.get("change"))
            for target in first["changed_targets"]
        }
        self.assertIn(("symbol", "old", "renamed"), changes)
        self.assertIn(("synthetic", "module-members", "symbol-added"), changes)

        (self.root / "module.py").write_text(
            "def added():\n    return 2\n", encoding="utf-8")
        self.git("add", "module.py")
        self.git("commit", "-qm", "delete renamed")
        result = self.git("rev-parse", "HEAD")
        second = map_committed_diff(self.root, middle, result)
        deleted = [
            target for target in second["changed_targets"]
            if target.get("change") == "deleted"
        ]
        self.assertEqual(deleted[0]["qualified_symbol"], "renamed")


class FakeAdapter:
    name = "fake"
    degraded_isolation = False

    def prepare(self, paths, config):
        if (paths.source / ".git").exists():
            raise AssertionError("sandbox source must not include .git")
        return {
            "image": "fake:test",
            "image_digest": "sha256:fake",
            "diagnostic": None,
        }

    def run(self, paths, command, config):
        (paths.build / "artifact.bin").write_bytes(b"artifact")
        return CommandResult(command, 0, f"fake ran {command}\n")


class SandboxTest(TempCase):
    def git(self, *args):
        return subprocess.run(
            ["git", *args],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()

    def setUp(self):
        super().setUp()
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Mission Control Test")
        (self.root / "source.txt").write_text("source\n", encoding="utf-8")
        self.git("add", "source.txt")
        self.git("commit", "-qm", "source")
        self.commit = self.git("rev-parse", "HEAD")

    def test_fake_adapter_uses_private_storage_and_writes_evidence(self):
        store = MissionStore.initialize(
            self.root / ".mc",
            mission({
                "backend": "native",
                "commands": ["fake-build", "fake-test"],
                "artifact_paths": ["artifact.bin"],
            }),
        )
        manager = SandboxManager(store, self.root, adapter=FakeAdapter())
        prepared = manager.prepare("MC-FAKE", self.commit)
        paths = manager.paths("MC-FAKE")
        self.assertEqual(prepared["backend"], "fake")
        self.assertFalse(prepared["degraded_isolation"])
        self.assertFalse((paths.source / ".git").exists())
        self.assertEqual(
            len({paths.source, paths.build, paths.cache, paths.packages}), 4)
        evidence = manager.run("MC-FAKE")
        self.assertEqual(len(evidence["commands"]), 2)
        self.assertIn("artifact.bin", evidence["artifact_hashes"])
        validate_sandbox(
            store.evidence_dir("MC-FAKE"),
            "MC-FAKE",
            "sandbox.json",
            require_pass=True,
        )

    def test_native_backend_warns_that_isolation_is_degraded(self):
        store = MissionStore.initialize(
            self.root / ".native", mission())
        manager = SandboxManager(store, self.root)
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            prepared = manager.prepare(
                "MC-NATIVE", self.commit, backend="native")
        self.assertTrue(prepared["degraded_isolation"])
        self.assertIn("degraded isolation", output.getvalue())

    def test_wait_in_line_emits_deprecation_warning(self):
        lock_dir = self.root / "locks"
        env = os.environ.copy()
        env["WAIT_IN_LINE_LOCK_DIR"] = str(lock_dir)
        result = subprocess.run(
            [
                sys.executable,
                str(WAIT_IN_LINE),
                "--name",
                "test-warning",
                "--",
                sys.executable,
                "-c",
                "print('ok')",
            ],
            cwd=self.root,
            env=env,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("DEPRECATED", result.stderr)
        self.assertIn("ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
