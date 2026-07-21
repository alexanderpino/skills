"""Private execution workspace and native/container adapter seam."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Protocol

from .models import file_hash, normalize_path, now, remove_tree, validate_id
from .store import MissionStore


@dataclass(frozen=True)
class SandboxPaths:
    root: Path
    source: Path
    build: Path
    cache: Path
    packages: Path


@dataclass
class CommandResult:
    command: str
    exit_code: int
    output: str


class ExecutionAdapter(Protocol):
    name: str
    degraded_isolation: bool

    def prepare(
        self, paths: SandboxPaths, config: dict[str, Any],
    ) -> dict[str, Any]: ...

    def run(
        self, paths: SandboxPaths, command: str,
        config: dict[str, Any],
    ) -> CommandResult: ...


class NativeAdapter:
    """Explicit degraded fallback using the private exported source tree."""

    name = "native"
    degraded_isolation = True

    def prepare(
        self, paths: SandboxPaths, config: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "image": None,
            "image_digest": None,
            "diagnostic": (
                "native backend: source/build/cache are private, but process, "
                "kernel, credentials, and network isolation are not enforced"),
        }

    def run(
        self, paths: SandboxPaths, command: str,
        config: dict[str, Any],
    ) -> CommandResult:
        env = os.environ.copy()
        env.update({
            "HOME": str(paths.cache),
            "USERPROFILE": str(paths.cache),
            "XDG_CACHE_HOME": str(paths.cache),
            "PIP_CACHE_DIR": str(paths.packages / "pip"),
            "NPM_CONFIG_CACHE": str(paths.packages / "npm"),
            "CARGO_HOME": str(paths.packages / "cargo"),
            "MC_BUILD_DIR": str(paths.build),
        })
        result = subprocess.run(
            command, cwd=paths.source, env=env, shell=True,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        return CommandResult(command, result.returncode, result.stdout)


class ContainerAdapter:
    """Docker/Podman adapter with hardened portable defaults."""

    degraded_isolation = False

    def __init__(self, backend: str):
        if backend not in ("docker", "podman"):
            raise ValueError("container backend must be docker or podman")
        executable = shutil.which(backend)
        if executable is None:
            raise ValueError(
                f"{backend} backend requested but '{backend}' is not on PATH")
        self.name = backend
        self.executable = executable

    def _invoke(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [self.executable, *args], text=True, capture_output=True)
        if result.returncode:
            raise ValueError(
                f"{self.name} {' '.join(args[:3])} failed "
                f"(exit {result.returncode}): {result.stderr.strip()}")
        return result

    def prepare(
        self, paths: SandboxPaths, config: dict[str, Any],
    ) -> dict[str, Any]:
        image = config.get("image")
        if not isinstance(image, str) or not image.strip():
            raise ValueError(
                f"{self.name} backend requires mission.execution.image")
        result = self._invoke([
            "image", "inspect", "--format",
            "{{json .RepoDigests}}|{{.Id}}", image,
        ])
        line = result.stdout.strip()
        digest = line
        if "|" in line:
            repo_digests, image_id = line.split("|", 1)
            try:
                values = json.loads(repo_digests)
            except json.JSONDecodeError:
                values = []
            digest = values[0] if values else image_id
        if not digest:
            raise ValueError(
                f"{self.name} could not resolve a digest for image {image}")
        return {
            "image": image,
            "image_digest": digest,
            "diagnostic": None,
        }

    @staticmethod
    def _mount(path: Path, target: str) -> str:
        return f"{path.resolve()}:{target}"

    def run(
        self, paths: SandboxPaths, command: str,
        config: dict[str, Any],
    ) -> CommandResult:
        resources = config.get("resources") or {}
        network = config.get("network", "none")
        args = [
            "run", "--rm", "--init",
            "--security-opt", "no-new-privileges",
            "--cap-drop", "ALL",
            "--network", network,
            "--pids-limit", str(resources.get("pids", 256)),
            "--memory", str(resources.get("memory", "2g")),
            "--cpus", str(resources.get("cpus", 2)),
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=256m",
            "-v", self._mount(paths.source, "/workspace"),
            "-v", self._mount(paths.build, "/build"),
            "-v", self._mount(paths.cache, "/cache"),
            "-v", self._mount(paths.packages, "/packages"),
            "-e", "HOME=/cache",
            "-e", "XDG_CACHE_HOME=/cache",
            "-e", "PIP_CACHE_DIR=/packages/pip",
            "-e", "NPM_CONFIG_CACHE=/packages/npm",
            "-e", "CARGO_HOME=/packages/cargo",
            "-e", "MC_BUILD_DIR=/build",
            "-w", "/workspace",
        ]
        if config.get("read_only_root", True):
            args.append("--read-only")
        args.extend([config["image"], "sh", "-lc", command])
        result = subprocess.run(
            [self.executable, *args], text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        return CommandResult(command, result.returncode, result.stdout)


def _safe_extract(archive: Path, destination: Path) -> None:
    with tarfile.open(archive, "r") as tar:
        members = tar.getmembers()
        for member in members:
            name = PurePosixPath(member.name)
            if name.is_absolute() or ".." in name.parts:
                raise ValueError(
                    f"git archive contains unsafe path: {member.name}")
            if member.issym() or member.islnk():
                link = PurePosixPath(member.linkname)
                combined = name.parent / link
                depth = 0
                for part in combined.parts:
                    if part == "..":
                        depth -= 1
                    elif part not in ("", "."):
                        depth += 1
                    if depth < 0:
                        raise ValueError(
                            f"git archive link escapes source: {member.name}")
        tar.extractall(destination)


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda value: value.as_posix()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8") + b"\0")
        if path.is_symlink():
            digest.update(os.readlink(path).encode("utf-8") + b"\0")
        elif path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


class SandboxManager:
    """Prepare, run, inspect, and destroy per-item isolated workspaces."""

    def __init__(
        self, store: MissionStore, repo: Path,
        *, adapter: ExecutionAdapter | None = None,
    ):
        self.store = store
        self.repo = repo.resolve()
        self.injected_adapter = adapter

    def _config(self) -> dict[str, Any]:
        mission = self.store.document("mission").data
        execution = dict(mission.get("execution") or {})
        execution.setdefault("backend", "auto")
        execution.setdefault("native_fallback", True)
        execution.setdefault("network", "none")
        execution.setdefault("read_only_root", True)
        execution.setdefault(
            "resources", {"cpus": 2, "memory": "2g", "pids": 256})
        return execution

    def _select(self, requested: str | None = None) -> ExecutionAdapter:
        if self.injected_adapter is not None:
            return self.injected_adapter
        config = self._config()
        backend = requested or config["backend"]
        if backend == "native":
            return NativeAdapter()
        if backend in ("docker", "podman"):
            return ContainerAdapter(backend)
        # Auto mode only selects a container when an image was configured.
        # Otherwise native fallback is explicit in evidence rather than
        # guessing an image or pulling one behind the user's back.
        if config.get("image"):
            for candidate in ("docker", "podman"):
                if shutil.which(candidate):
                    return ContainerAdapter(candidate)
        if config.get("native_fallback", True):
            return NativeAdapter()
        raise ValueError(
            "no Docker/Podman backend is available and native_fallback=false")

    def paths(self, item_id: str) -> SandboxPaths:
        validate_id(item_id, "sandbox item id")
        root = (self.store.paths["sandboxes"] / item_id).resolve()
        try:
            root.relative_to(self.store.root.resolve())
        except ValueError as exc:
            raise ValueError("sandbox path escaped mission state") from exc
        return SandboxPaths(
            root, root / "source", root / "build",
            root / "cache", root / "packages",
        )

    def prepare(
        self, item_id: str, commit: str, *,
        backend: str | None = None,
    ) -> dict[str, Any]:
        paths = self.paths(item_id)
        resolved = subprocess.run(
            ["git", "-C", str(self.repo), "rev-parse", commit],
            text=True, capture_output=True,
        )
        if resolved.returncode:
            raise ValueError(
                f"cannot resolve sandbox commit {commit}: "
                f"{resolved.stderr.strip()}")
        source_commit = resolved.stdout.strip()
        if paths.root.exists():
            remove_tree(paths.root)
        for directory in (
                paths.source, paths.build, paths.cache, paths.packages):
            directory.mkdir(parents=True, exist_ok=True)
        archive = paths.root / "source.tar"
        result = subprocess.run([
            "git", "-C", str(self.repo), "archive", "--format=tar",
            f"--output={archive}", source_commit,
        ], text=True, capture_output=True)
        if result.returncode:
            raise ValueError(
                f"git archive failed: {result.stderr.strip()}")
        _safe_extract(archive, paths.source)
        archive.unlink()
        adapter = self._select(backend)
        config = self._config()
        details = adapter.prepare(paths, config)
        record = {
            "item": item_id,
            "state": "prepared",
            "backend": adapter.name,
            "degraded_isolation": adapter.degraded_isolation,
            "source_commit": source_commit,
            "source_tree_sha256": _tree_hash(paths.source),
            "workspace": str(paths.root),
            "storage": {
                "source": str(paths.source),
                "build": str(paths.build),
                "cache": str(paths.cache),
                "packages": str(paths.packages),
            },
            "resource_policy": {
                **config.get("resources", {}),
                "network": config.get("network", "none"),
                "no_new_privileges": adapter.name != "native",
                "cap_drop": "ALL" if adapter.name != "native" else None,
                "private_tmp": True,
            },
            "prepared_at": now(),
            **details,
        }
        self.store.put_runtime_record("sandboxes", item_id, record)
        if adapter.degraded_isolation:
            print(
                "warning: native sandbox is degraded isolation; "
                + details["diagnostic"],
                file=sys.stderr,
            )
        return record

    def _adapter_from_record(
        self, record: dict[str, Any],
    ) -> ExecutionAdapter:
        if self.injected_adapter is not None:
            if self.injected_adapter.name != record["backend"]:
                raise ValueError("injected adapter does not match sandbox record")
            return self.injected_adapter
        if record["backend"] == "native":
            return NativeAdapter()
        return ContainerAdapter(record["backend"])

    def default_commands(self) -> list[str]:
        mission = self.store.document("mission").data
        configured = (mission.get("execution") or {}).get("commands")
        if configured:
            if not isinstance(configured, list) or not all(
                    isinstance(command, str) and command.strip()
                    for command in configured):
                raise ValueError("mission.execution.commands must be strings")
            return configured
        oracle = mission["repo_oracle"]
        return [
            oracle[name] for name in ("build", "test", "lint")
            if oracle.get(name)
        ]

    def run(
        self, item_id: str, commands: Iterable[str] | None = None, *,
        evidence_name: str = "sandbox.json",
    ) -> dict[str, Any]:
        versioned = self.store.runtime_record("sandboxes", item_id)
        if versioned is None:
            raise ValueError(
                f"{item_id} has no prepared sandbox; run sandbox prepare")
        record = versioned.data
        paths = self.paths(item_id)
        if record.get("state") not in ("prepared", "failed", "passed"):
            raise ValueError(
                f"{item_id} sandbox is in state {record.get('state')}")
        if not paths.source.is_dir():
            raise ValueError(
                f"{item_id} private source is missing; prepare again")
        selected = list(commands or self.default_commands())
        if not selected:
            raise ValueError("sandbox run has no configured commands")
        if not all(isinstance(command, str) and command.strip()
                   for command in selected):
            raise ValueError("sandbox commands must be non-empty strings")
        adapter = self._adapter_from_record(record)
        config = self._config()
        evidence_dir = self.store.evidence_dir(item_id)
        evidence_dir.mkdir(parents=True, exist_ok=True)
        command_records = []
        phase = evidence_name.removesuffix(".json").replace("/", "-")
        for index, command in enumerate(selected, 1):
            outcome = adapter.run(paths, command, config)
            log_name = f"{phase}-{index}.log"
            log_path = evidence_dir / log_name
            log_path.write_text(outcome.output, encoding="utf-8")
            command_records.append({
                "command": command,
                "exit_code": outcome.exit_code,
                "log": log_name,
                "log_sha256": file_hash(log_path),
            })
            if outcome.exit_code:
                break
        artifact_hashes: dict[str, str] = {}
        for raw in config.get("artifact_paths", []):
            relative = normalize_path(raw)
            candidates = [paths.build / relative, paths.source / relative]
            artifact = next((path for path in candidates if path.is_file()), None)
            if artifact is None:
                raise ValueError(
                    f"configured sandbox artifact is missing: {relative}")
            artifact_hashes[relative] = file_hash(artifact)
        evidence = {
            "item": item_id,
            "backend": record["backend"],
            "degraded_isolation": record["degraded_isolation"],
            "image": record.get("image"),
            "image_digest": record.get("image_digest"),
            "source_commit": record["source_commit"],
            "source_tree_sha256": record["source_tree_sha256"],
            "resource_policy": record["resource_policy"],
            "commands": command_records,
            "artifact_hashes": artifact_hashes,
            "timestamp": now(),
        }
        evidence_path = evidence_dir / evidence_name
        temp = evidence_path.with_suffix(".json.tmp")
        temp.write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temp.replace(evidence_path)
        record["state"] = (
            "passed" if all(row["exit_code"] == 0 for row in command_records)
            else "failed")
        record["last_evidence"] = {
            "file": evidence_name,
            "sha256": file_hash(evidence_path),
        }
        record["ran_at"] = now()
        self.store.put_runtime_record(
            "sandboxes", item_id, record, versioned.version)
        return evidence

    def status(self, item_id: str) -> dict[str, Any]:
        record = self.store.runtime_record("sandboxes", item_id)
        if record is None:
            raise ValueError(f"{item_id} has no sandbox")
        return {**record.data, "version": record.version}

    def destroy(self, item_id: str) -> None:
        paths = self.paths(item_id)
        if paths.root.exists():
            remove_tree(paths.root)
        self.store.delete_runtime_record("sandboxes", item_id)
