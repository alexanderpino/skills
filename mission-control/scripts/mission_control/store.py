"""Transactional SQLite state store.

Queue items and backlog items are independent versioned rows.  All mutations use
short ``BEGIN IMMEDIATE`` transactions and compare-and-swap the observed row
version.  Filesystem, Git, AST, container, and evidence work belongs outside
these transactions.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator

from .models import (
    LeaseConflict,
    SCHEMA_VERSION,
    StateConflict,
    file_hash,
    json_text,
    normalize_path,
    now,
    public_record,
    validate_id,
)


LEGACY_NAMES = (
    "mission", "backlog", "queue", "ledger", "agenda", "investigations",
)


@dataclass(frozen=True)
class Versioned:
    data: dict[str, Any]
    version: int


class MissionStore:
    """Canonical mission state with migration and compatibility export."""

    def __init__(self, root: str | os.PathLike[str], *, auto_migrate: bool = True):
        self.root = Path(root)
        self.db_path = self.root / "state.db"
        self.paths = {
            name: self.root / f"{name}.json" for name in LEGACY_NAMES
        }
        self.paths.update({
            "evidence": self.root / "evidence",
            "worktrees": self.root / "worktrees",
            "sandboxes": self.root / "sandboxes",
            "integration": self.root / "integration",
        })
        if not self.db_path.exists():
            if auto_migrate and self.paths["mission"].is_file():
                self.migrate_legacy()
            else:
                raise ValueError(
                    f"{self.root} is not initialized; run 'init' first")
        self._verify_schema()

    @classmethod
    def initialize(
        cls, root: str | os.PathLike[str], mission: dict[str, Any],
    ) -> "MissionStore":
        root_path = Path(root)
        db_path = root_path / "state.db"
        if db_path.exists() or (root_path / "mission.json").exists():
            raise ValueError(f"{root_path} already initialized — use status to resume")
        root_path.mkdir(parents=True, exist_ok=True)
        (root_path / "evidence").mkdir(parents=True, exist_ok=True)
        store = cls.__new__(cls)
        store.root = root_path
        store.db_path = db_path
        store.paths = {
            name: root_path / f"{name}.json" for name in LEGACY_NAMES
        }
        store.paths.update({
            "evidence": root_path / "evidence",
            "worktrees": root_path / "worktrees",
            "sandboxes": root_path / "sandboxes",
            "integration": root_path / "integration",
        })
        store._create_database()
        with store.write() as db:
            store._put_document(db, "mission", mission)
            store._put_document(db, "agenda", {"next_id": 1, "notes": []})
            store._put_document(db, "investigations", {"items": []})
            store._meta_set(db, "created_at", now())
            store._audit(db, None, "init", {"schema": SCHEMA_VERSION})
        store.export_json(force=True)
        return store

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(
            self.db_path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA busy_timeout = 10000")
        return db

    def _create_database(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        db = self._connect()
        try:
            db.execute("PRAGMA journal_mode = WAL")
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS documents (
                    name TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS backlog_items (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS queue_items (
                    id TEXT PRIMARY KEY REFERENCES backlog_items(id)
                        ON DELETE RESTRICT,
                    state TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS leases (
                    lease_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id TEXT NOT NULL REFERENCES queue_items(id)
                        ON DELETE CASCADE,
                    target_key TEXT NOT NULL,
                    target_json TEXT NOT NULL,
                    acquired_at TEXT NOT NULL,
                    ttl_minutes REAL NOT NULL,
                    UNIQUE(item_id, target_key)
                );
                CREATE INDEX IF NOT EXISTS leases_item_idx ON leases(item_id);
                CREATE TABLE IF NOT EXISTS contention (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id TEXT NOT NULL,
                    held_by_json TEXT NOT NULL,
                    targets_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS contention_item_idx
                    ON contention(item_id);
                CREATE TABLE IF NOT EXISTS evidence_seals (
                    item_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    file TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    accepted_at TEXT NOT NULL,
                    PRIMARY KEY(item_id, kind, file)
                );
                CREATE TABLE IF NOT EXISTS sandboxes (
                    item_id TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS merge_jobs (
                    item_id TEXT PRIMARY KEY REFERENCES queue_items(id)
                        ON DELETE CASCADE,
                    data_json TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_log (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id TEXT,
                    action TEXT NOT NULL,
                    detail_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            db.execute(
                "INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)",
                ("schema_version", str(SCHEMA_VERSION)),
            )
        finally:
            db.close()

    def _verify_schema(self) -> None:
        with self.read() as db:
            row = db.execute(
                "SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if row is None or int(row["value"]) != SCHEMA_VERSION:
            raise ValueError(
                f"unsupported state.db schema; expected {SCHEMA_VERSION}")

    @contextmanager
    def read(self) -> Iterator[sqlite3.Connection]:
        db = self._connect()
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def write(self) -> Iterator[sqlite3.Connection]:
        db = self._connect()
        db.execute("BEGIN IMMEDIATE")
        try:
            yield db
        except BaseException:
            db.rollback()
            raise
        else:
            db.commit()
        finally:
            db.close()

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        return json.loads(row["data_json"])

    @staticmethod
    def _meta_set(db: sqlite3.Connection, key: str, value: str) -> None:
        db.execute(
            "INSERT INTO meta(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    @staticmethod
    def _audit(
        db: sqlite3.Connection, item_id: str | None, action: str,
        detail: dict[str, Any],
    ) -> None:
        db.execute(
            "INSERT INTO audit_log(item_id,action,detail_json,created_at) "
            "VALUES(?,?,?,?)",
            (item_id, action, json_text(detail), now()),
        )

    @staticmethod
    def _put_document(
        db: sqlite3.Connection, name: str, data: dict[str, Any],
    ) -> None:
        db.execute(
            "INSERT INTO documents(name,data_json,version,updated_at) "
            "VALUES(?,?,1,?) ON CONFLICT(name) DO UPDATE SET "
            "data_json=excluded.data_json, version=documents.version+1, "
            "updated_at=excluded.updated_at",
            (name, json_text(data), now()),
        )

    def migrate_legacy(self) -> None:
        """Import the six JSON files once, preserving an immutable backup."""
        missing = [
            name for name in LEGACY_NAMES if not self.paths[name].is_file()
        ]
        if missing:
            raise ValueError(
                "legacy migration requires all JSON state files; missing "
                + ", ".join(f"{name}.json" for name in missing))
        backup = self.root / "migration-backup" / "legacy-json-v1"
        backup.mkdir(parents=True, exist_ok=True)
        values: dict[str, dict[str, Any]] = {}
        hashes: dict[str, str] = {}
        for name in LEGACY_NAMES:
            source = self.paths[name]
            values[name] = json.loads(source.read_text(encoding="utf-8"))
            hashes[name] = file_hash(source)
            destination = backup / source.name
            if destination.exists():
                if file_hash(destination) != hashes[name]:
                    raise ValueError(
                        f"migration backup differs from {source.name}; "
                        "refusing to overwrite either copy")
            else:
                shutil.copy2(source, destination)
        try:
            self._create_database()
            with self.write() as db:
                self._put_document(db, "mission", values["mission"])
                self._put_document(
                    db, "agenda", values.get("agenda") or
                    {"next_id": 1, "notes": []})
                self._put_document(
                    db, "investigations", values.get("investigations") or
                    {"items": []})
                for entry in values["backlog"].get("items", []):
                    validate_id(entry["id"], "backlog id")
                    clean = dict(entry)
                    clean.pop("version", None)
                    db.execute(
                        "INSERT INTO backlog_items"
                        "(id,status,data_json,version,updated_at) VALUES(?,?,?,?,?)",
                        (clean["id"], clean.get("status", "open"),
                         json_text(clean), 1, now()),
                    )
                for item in values["queue"].get("items", []):
                    clean = dict(item)
                    clean.pop("version", None)
                    if clean.get("state") == "ready-to-merge":
                        clean["state"] = "merge-pending"
                        clean.setdefault("history", []).append({
                            "state": "merge-pending",
                            "at": now(),
                            "reason": "state-schema-migration",
                        })
                    db.execute(
                        "INSERT INTO queue_items"
                        "(id,state,data_json,version,updated_at) VALUES(?,?,?,?,?)",
                        (clean["id"], clean["state"], json_text(clean), 1, now()),
                    )
                for lease in values["ledger"].get("leases", []):
                    path = normalize_path(lease["path"])
                    target = {
                        "path": path,
                        "type": "file",
                        "qualified_symbol": None,
                        "node_kind": "file",
                        "base_blob": None,
                        "base_commit": None,
                        "structural_anchor_hash": None,
                        "adapter": "legacy-file-fallback",
                    }
                    db.execute(
                        "INSERT INTO leases"
                        "(item_id,target_key,target_json,acquired_at,ttl_minutes) "
                        "VALUES(?,?,?,?,?)",
                        (lease["item"], f"file:{path}", json_text(target),
                         lease.get("acquired", now()),
                         lease.get("ttl_minutes", 90)),
                    )
                for event in values["ledger"].get("contention", []):
                    db.execute(
                        "INSERT INTO contention"
                        "(item_id,held_by_json,targets_json,created_at) "
                        "VALUES(?,?,?,?)",
                        (event["item"], json_text(event.get("held_by", [])),
                         "[]", event.get("at", now())),
                    )
                self._meta_set(db, "migration_complete", now())
                self._meta_set(db, "migration_backup", str(backup))
                for name, digest in hashes.items():
                    self._meta_set(db, f"export_hash:{name}", digest)
                self._audit(
                    db, None, "migrate-json",
                    {"backup": str(backup), "hashes": hashes},
                )
        except BaseException:
            for suffix in ("", "-wal", "-shm"):
                candidate = Path(str(self.db_path) + suffix)
                if candidate.exists():
                    candidate.unlink()
            raise

    def migration_info(self) -> dict[str, Any]:
        with self.read() as db:
            rows = db.execute(
                "SELECT key,value FROM meta WHERE key LIKE 'migration_%' "
                "OR key='schema_version'").fetchall()
        return {row["key"]: row["value"] for row in rows}

    def document(self, name: str) -> Versioned:
        with self.read() as db:
            row = db.execute(
                "SELECT data_json,version FROM documents WHERE name=?", (name,)
            ).fetchone()
        if row is None:
            raise ValueError(f"state document is missing: {name}")
        return Versioned(self._decode(row), row["version"])

    def update_document(
        self, name: str, replacement: dict[str, Any], expected_version: int,
        *, action: str,
    ) -> int:
        with self.write() as db:
            result = db.execute(
                "UPDATE documents SET data_json=?,version=version+1,"
                "updated_at=? WHERE name=? AND version=?",
                (json_text(replacement), now(), name, expected_version),
            )
            if result.rowcount != 1:
                raise StateConflict(
                    f"{name} changed concurrently; reload and retry")
            self._audit(db, None, action, {"document": name})
            return expected_version + 1

    def backlog_item(self, item_id: str) -> Versioned:
        with self.read() as db:
            row = db.execute(
                "SELECT data_json,version FROM backlog_items WHERE id=?",
                (item_id,),
            ).fetchone()
        if row is None:
            raise ValueError(f"not in backlog: {item_id}")
        return Versioned(self._decode(row), row["version"])

    def queue_item(self, item_id: str) -> Versioned:
        with self.read() as db:
            row = db.execute(
                "SELECT data_json,version FROM queue_items WHERE id=?",
                (item_id,),
            ).fetchone()
        if row is None:
            raise ValueError(f"unknown item: {item_id}")
        return Versioned(self._decode(row), row["version"])

    def add_backlog_item(self, entry: dict[str, Any]) -> None:
        validate_id(entry["id"], "backlog id")
        clean = dict(entry)
        clean.pop("version", None)
        with self.write() as db:
            try:
                db.execute(
                    "INSERT INTO backlog_items"
                    "(id,status,data_json,version,updated_at) VALUES(?,?,?,?,?)",
                    (clean["id"], clean["status"], json_text(clean), 1, now()),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(f"backlog id exists: {clean['id']}") from exc
            self._audit(db, clean["id"], "add-item", clean)

    def claim_item(
        self, item_id: str, expected_backlog_version: int,
        queue_item: dict[str, Any],
    ) -> None:
        clean = dict(queue_item)
        clean.pop("version", None)
        with self.write() as db:
            row = db.execute(
                "SELECT status,version,data_json FROM backlog_items WHERE id=?",
                (item_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"not in backlog: {item_id}")
            if row["version"] != expected_backlog_version:
                raise StateConflict(
                    f"{item_id} backlog entry changed concurrently")
            if row["status"] != "open":
                raise StateConflict(
                    f"{item_id} is {row['status']}, not open")
            backlog = self._decode(row)
            unmet = []
            for dependency in backlog.get("depends_on", []):
                done = db.execute(
                    "SELECT 1 FROM queue_items WHERE id=? AND state='done'",
                    (dependency,),
                ).fetchone()
                if done is None:
                    unmet.append(dependency)
            if unmet:
                raise ValueError(
                    f"{item_id} has unmet dependencies: {', '.join(unmet)}")
            backlog["status"] = "claimed"
            db.execute(
                "UPDATE backlog_items SET status='claimed',data_json=?,"
                "version=version+1,updated_at=? WHERE id=? AND version=?",
                (json_text(backlog), now(), item_id, expected_backlog_version),
            )
            try:
                db.execute(
                    "INSERT INTO queue_items"
                    "(id,state,data_json,version,updated_at) VALUES(?,?,?,?,?)",
                    (item_id, clean["state"], json_text(clean), 1, now()),
                )
            except sqlite3.IntegrityError as exc:
                raise StateConflict(f"{item_id} was already claimed") from exc
            self._audit(db, item_id, "claim", {"state": clean["state"]})

    def update_queue_item(
        self, item_id: str, replacement: dict[str, Any],
        expected_version: int, expected_state: str, *, action: str,
        detail: dict[str, Any] | None = None,
    ) -> int:
        clean = dict(replacement)
        clean.pop("version", None)
        with self.write() as db:
            result = db.execute(
                "UPDATE queue_items SET state=?,data_json=?,version=version+1,"
                "updated_at=? WHERE id=? AND version=? AND state=?",
                (clean["state"], json_text(clean), now(), item_id,
                 expected_version, expected_state),
            )
            if result.rowcount != 1:
                row = db.execute(
                    "SELECT state,version FROM queue_items WHERE id=?",
                    (item_id,),
                ).fetchone()
                observed = "missing" if row is None else (
                    f"{row['state']}@v{row['version']}")
                raise StateConflict(
                    f"{item_id} changed concurrently; expected "
                    f"{expected_state}@v{expected_version}, observed {observed}")
            self._audit(db, item_id, action, detail or {})
            return expected_version + 1

    def complete_item(
        self, item_id: str, replacement: dict[str, Any],
        expected_version: int, expected_state: str,
    ) -> None:
        clean = dict(replacement)
        clean.pop("version", None)
        with self.write() as db:
            result = db.execute(
                "UPDATE queue_items SET state='done',data_json=?,"
                "version=version+1,updated_at=? "
                "WHERE id=? AND version=? AND state=?",
                (json_text(clean), now(), item_id, expected_version,
                 expected_state),
            )
            if result.rowcount != 1:
                raise StateConflict(
                    f"{item_id} changed while finalizing merge")
            row = db.execute(
                "SELECT data_json FROM backlog_items WHERE id=?",
                (item_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"{item_id} has no backlog entry")
            backlog = self._decode(row)
            backlog["status"] = "done"
            db.execute(
                "UPDATE backlog_items SET status='done',data_json=?,"
                "version=version+1,updated_at=? WHERE id=?",
                (json_text(backlog), now(), item_id),
            )
            db.execute("DELETE FROM leases WHERE item_id=?", (item_id,))
            db.execute("DELETE FROM contention WHERE item_id=?", (item_id,))
            self._audit(db, item_id, "complete", {})

    def rows(self, table: str) -> list[dict[str, Any]]:
        if table not in ("backlog_items", "queue_items"):
            raise ValueError(f"unsupported row table: {table}")
        with self.read() as db:
            result = db.execute(
                f"SELECT data_json,version FROM {table} ORDER BY rowid"
            ).fetchall()
        return [public_record(self._decode(row), row["version"]) for row in result]

    @staticmethod
    def target_key(target: dict[str, Any]) -> str:
        target_type = target["type"]
        path = normalize_path(target["path"])
        symbol = target.get("qualified_symbol") or ""
        return f"{target_type}:{path}:{symbol}"

    def leases(self, item_id: str | None = None) -> list[dict[str, Any]]:
        sql = (
            "SELECT item_id,target_json,acquired_at,ttl_minutes "
            "FROM leases"
        )
        params: tuple[Any, ...] = ()
        if item_id is not None:
            sql += " WHERE item_id=?"
            params = (item_id,)
        sql += " ORDER BY lease_id"
        with self.read() as db:
            rows = db.execute(sql, params).fetchall()
        output = []
        for row in rows:
            target = json.loads(row["target_json"])
            output.append({
                "item": row["item_id"],
                "target": target,
                "path": target["path"],
                "acquired": row["acquired_at"],
                "ttl_minutes": row["ttl_minutes"],
            })
        return output

    def acquire_leases(
        self, item_id: str, targets: list[dict[str, Any]],
        expected_item_version: int, ttl_minutes: float,
        conflicts: Callable[[dict[str, Any], dict[str, Any]], bool],
    ) -> None:
        """Atomically acquire all targets or record one contention event."""
        with self.write() as db:
            item = db.execute(
                "SELECT state,version FROM queue_items WHERE id=?", (item_id,)
            ).fetchone()
            if item is None:
                raise ValueError(f"unknown item: {item_id}")
            if item["version"] != expected_item_version:
                raise StateConflict(
                    f"{item_id} changed before lease acquisition")
            if item["state"] not in ("approved", "building"):
                raise ValueError(
                    f"{item_id} cannot lease while {item['state']}")
            existing_rows = db.execute(
                "SELECT item_id,target_json FROM leases WHERE item_id<>?",
                (item_id,),
            ).fetchall()
            clashes: list[tuple[dict[str, Any], dict[str, Any]]] = []
            held_by: set[str] = set()
            for requested in targets:
                for row in existing_rows:
                    held = json.loads(row["target_json"])
                    if conflicts(requested, held):
                        held_with_owner = dict(held)
                        held_with_owner["item"] = row["item_id"]
                        clashes.append((requested, held_with_owner))
                        held_by.add(row["item_id"])
            if clashes:
                db.execute(
                    "INSERT INTO contention"
                    "(item_id,held_by_json,targets_json,created_at) "
                    "VALUES(?,?,?,?)",
                    (item_id, json_text(sorted(held_by)),
                     json_text([pair[0] for pair in clashes]), now()),
                )
                self._audit(
                    db, item_id, "lease-conflict",
                    {"held_by": sorted(held_by),
                     "targets": [pair[0] for pair in clashes]},
                )
            else:
                acquired = now()
                for target in targets:
                    db.execute(
                        "INSERT INTO leases"
                        "(item_id,target_key,target_json,acquired_at,ttl_minutes) "
                        "VALUES(?,?,?,?,?) ON CONFLICT(item_id,target_key) "
                        "DO NOTHING",
                        (item_id, self.target_key(target), json_text(target),
                         acquired, ttl_minutes),
                    )
                db.execute("DELETE FROM contention WHERE item_id=?", (item_id,))
                self._audit(
                    db, item_id, "lease-acquire", {"targets": targets})
        if clashes:
            raise LeaseConflict(clashes)

    def release_leases(self, item_id: str) -> int:
        with self.write() as db:
            row = db.execute(
                "SELECT state FROM queue_items WHERE id=?", (item_id,)
            ).fetchone()
            if row is None:
                raise ValueError(f"unknown item: {item_id}")
            if row["state"] in (
                    "building", "verifying", "code-review",
                    "merge-pending", "merging", "merge-conflict",
                    "post-merge-verifying"):
                raise ValueError(
                    f"cannot release {item_id} while {row['state']}; "
                    "block or finish it")
            count = db.execute(
                "SELECT count(*) AS n FROM leases WHERE item_id=?", (item_id,)
            ).fetchone()["n"]
            db.execute("DELETE FROM leases WHERE item_id=?", (item_id,))
            db.execute("DELETE FROM contention WHERE item_id=?", (item_id,))
            self._audit(db, item_id, "lease-release", {"count": count})
        return count

    def force_release_leases(self, item_id: str) -> int:
        with self.write() as db:
            count = db.execute(
                "SELECT count(*) AS n FROM leases WHERE item_id=?", (item_id,)
            ).fetchone()["n"]
            db.execute("DELETE FROM leases WHERE item_id=?", (item_id,))
            db.execute("DELETE FROM contention WHERE item_id=?", (item_id,))
            self._audit(db, item_id, "lease-release-forced", {"count": count})
        return count

    def contention(self) -> list[dict[str, Any]]:
        with self.read() as db:
            rows = db.execute(
                "SELECT item_id,held_by_json,targets_json,created_at "
                "FROM contention ORDER BY event_id").fetchall()
        return [{
            "item": row["item_id"],
            "held_by": json.loads(row["held_by_json"]),
            "targets": json.loads(row["targets_json"]),
            "at": row["created_at"],
        } for row in rows]

    def seal_evidence(
        self, item_id: str, kind: str, path: Path,
    ) -> dict[str, str]:
        digest = file_hash(path)
        with self.write() as db:
            db.execute(
                "INSERT INTO evidence_seals"
                "(item_id,kind,file,sha256,accepted_at) VALUES(?,?,?,?,?) "
                "ON CONFLICT(item_id,kind,file) DO UPDATE SET "
                "sha256=excluded.sha256,accepted_at=excluded.accepted_at",
                (item_id, kind, path.name, digest, now()),
            )
            self._audit(
                db, item_id, "evidence-seal",
                {"kind": kind, "file": path.name, "sha256": digest},
            )
        return {"file": path.name, "sha256": digest}

    def evidence_seals(self, item_id: str) -> list[dict[str, Any]]:
        with self.read() as db:
            rows = db.execute(
                "SELECT kind,file,sha256,accepted_at FROM evidence_seals "
                "WHERE item_id=? ORDER BY kind,file", (item_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def put_runtime_record(
        self, table: str, item_id: str, data: dict[str, Any],
        expected_version: int | None = None,
    ) -> int:
        if table not in ("sandboxes", "merge_jobs"):
            raise ValueError(f"unsupported runtime table: {table}")
        with self.write() as db:
            row = db.execute(
                f"SELECT version FROM {table} WHERE item_id=?", (item_id,)
            ).fetchone()
            if row is None:
                if expected_version not in (None, 0):
                    raise StateConflict(
                        f"{table} record for {item_id} disappeared")
                db.execute(
                    f"INSERT INTO {table}"
                    "(item_id,data_json,version,updated_at) VALUES(?,?,1,?)",
                    (item_id, json_text(data), now()),
                )
                version = 1
            else:
                if expected_version is not None and \
                        row["version"] != expected_version:
                    raise StateConflict(
                        f"{table} record for {item_id} changed concurrently")
                db.execute(
                    f"UPDATE {table} SET data_json=?,version=version+1,"
                    "updated_at=? WHERE item_id=?",
                    (json_text(data), now(), item_id),
                )
                version = row["version"] + 1
            self._audit(db, item_id, f"{table}-update", {"version": version})
        return version

    def runtime_record(self, table: str, item_id: str) -> Versioned | None:
        if table not in ("sandboxes", "merge_jobs"):
            raise ValueError(f"unsupported runtime table: {table}")
        with self.read() as db:
            row = db.execute(
                f"SELECT data_json,version FROM {table} WHERE item_id=?",
                (item_id,),
            ).fetchone()
        return None if row is None else Versioned(
            self._decode(row), row["version"])

    def delete_runtime_record(self, table: str, item_id: str) -> None:
        if table not in ("sandboxes", "merge_jobs"):
            raise ValueError(f"unsupported runtime table: {table}")
        with self.write() as db:
            db.execute(f"DELETE FROM {table} WHERE item_id=?", (item_id,))
            self._audit(db, item_id, f"{table}-delete", {})

    def snapshot(self, name: str) -> dict[str, Any]:
        if name == "backlog":
            return {"items": self.rows("backlog_items")}
        if name == "queue":
            return {"items": self.rows("queue_items")}
        if name == "ledger":
            return {"leases": self.leases(), "contention": self.contention()}
        if name in ("mission", "agenda", "investigations"):
            value = self.document(name).data
            return value
        raise ValueError(f"unknown snapshot: {name}")

    def export_json(self, *, force: bool = False) -> list[Path]:
        """Write human-readable snapshots without accepting edits as state."""
        snapshots = {name: self.snapshot(name) for name in LEGACY_NAMES}
        with self.read() as db:
            expected = {
                row["key"].split(":", 1)[1]: row["value"]
                for row in db.execute(
                    "SELECT key,value FROM meta WHERE key LIKE 'export_hash:%'"
                ).fetchall()
            }
        for name, path in self.paths.items():
            if name not in LEGACY_NAMES or not path.exists() or force:
                continue
            previous = expected.get(name)
            if previous is not None and file_hash(path) != previous:
                raise ValueError(
                    f"{path} was edited after its last export; JSON is a "
                    "read-only compatibility snapshot. Use export-json --force "
                    "only after preserving the manual changes.")
        written: list[Path] = []
        hashes: dict[str, str] = {}
        for name, value in snapshots.items():
            path = self.paths[name]
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps(value, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            tmp.replace(path)
            hashes[name] = file_hash(path)
            written.append(path)
        with self.write() as db:
            for name, digest in hashes.items():
                self._meta_set(db, f"export_hash:{name}", digest)
            self._meta_set(db, "last_export_at", now())
            self._audit(db, None, "export-json", {"hashes": hashes})
        return written

    def evidence_dir(self, item_id: str) -> Path:
        validate_id(item_id, "item/evidence id")
        return self.paths["evidence"] / item_id

    def audit_log(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.read() as db:
            rows = db.execute(
                "SELECT sequence,item_id,action,detail_json,created_at "
                "FROM audit_log ORDER BY sequence DESC LIMIT ?", (limit,)
            ).fetchall()
        return [{
            "sequence": row["sequence"],
            "item_id": row["item_id"],
            "action": row["action"],
            "detail": json.loads(row["detail_json"]),
            "created_at": row["created_at"],
        } for row in rows]
