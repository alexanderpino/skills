#!/usr/bin/env python3
"""Asset cooker scaffold for an AAA engine content pipeline.

This tool converts source assets (FBX, PNG, WAV, ...) into platform-specific
cooked formats (mesh blobs, BCn-compressed textures, ADPCM streams, ...). It
supports incremental cooking via a content-addressable Derived Data Cache
(DDC): inputs are hashed, and if the hash is present in the DDC the cook is
skipped and the cached artifact is copied to the output.

Layering:
    AssetDescriptor - declarative metadata for a single source asset.
    CookGraph       - DAG of descriptors with dependency edges.
    CookWorker      - executes a topological order, possibly in parallel.

COOKER DEPENDENCY-CONTEXT PSEUDOCODE::

    for asset in ready_topological_level:
        require every dependency succeeded and has a regular cooked artifact
        context = immutable_map(dependency_id -> (artifact_path, output_hash))
        backend.cook(asset, context, temporary_output)
        verify, hash, and atomically publish temporary_output

Usage::

    python asset_cooker_template.py \\
        --platform win64 \\
        --input  .\\content \\
        --output .\\cooked \\
        --ddc    .\\ddc \\
        --incremental

``--output`` is the common root; the cooker appends the platform exactly once
(``.\\cooked\\win64\\...`` in this example).

Exit codes:
    0 - all assets cooked (or cache-hit) successfully
    1 - one or more assets failed
    2 - bad CLI arguments / environment

Requires Python 3.11+ (uses ``enum.StrEnum``).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
import sys
import tempfile
import time
import uuid
from collections.abc import Iterable, Iterator, Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Protocol

try:
    import blake3  # type: ignore[import-not-found]
    _HAS_BLAKE3 = True
except ImportError:  # pragma: no cover - fallback path
    _HAS_BLAKE3 = False


log = logging.getLogger("asset_cooker")
COOKER_IDENTITY = "asset-cooker-template/v2"


# ---------------------------------------------------------------------------
# Platforms
# ---------------------------------------------------------------------------

class Platform(StrEnum):
    """Supported cook targets. Names match engine platform-id strings."""
    WIN64   = "win64"
    MACOS   = "macos"
    LINUX   = "linux"
    PS5     = "ps5"
    XSX     = "xsx"
    SWITCH2 = "switch2"
    IOS     = "ios"
    ANDROID = "android"


def platform_output_path(root: Path, platform: Platform, rel: Path) -> Path:
    """Return the absolute cooked path for `rel` under `root` and `platform`.

    The on-disk layout is ``<root>/<platform>/<rel>.cooked`` with the original
    extension preserved before the ``.cooked`` sentinel so tools can still
    identify source format at a glance.
    """
    if rel.is_absolute() or not rel.parts or any(part in ("", ".", "..") for part in rel.parts):
        raise ValueError(f"asset output path must be relative and contained: {rel}")
    platform_root = (root / platform.value).resolve()
    candidate = platform_root / rel.with_suffix(rel.suffix + ".cooked")
    dest = candidate.resolve()
    if not dest.is_relative_to(platform_root):
        raise ValueError(f"asset output escapes output root: {rel}")
    return dest


# ---------------------------------------------------------------------------
# Content-addressable hashing
# ---------------------------------------------------------------------------

def content_hash(path: Path, *, chunk: int = 1 << 20) -> str:
    """Return a hex digest of the file at `path`.

    Uses BLAKE3 when available (fast, parallelizable) and falls back to
    SHA-256 otherwise. The output is prefixed with the algorithm so mismatched
    DDC entries can be detected and migrated.
    """
    if not path.is_file() or path.is_symlink():
        raise OSError(f"hash input must be a regular, non-symlink file: {path}")

    if _HAS_BLAKE3:
        h = blake3.blake3()
        algo = "blake3"
    else:
        h = hashlib.sha256()
        algo = "sha256"

    with path.open("rb") as f:
        while True:
            buf = f.read(chunk)
            if not buf:
                break
            h.update(buf)
    return f"{algo}:{h.hexdigest()}"


def combined_hash(parts: Iterable[str]) -> str:
    """Produce a stable digest from an ordered iterable of hex strings.

    Used to fold descriptor-side parameters (compression settings, platform
    tag, tool version) into the DDC key so a cook-option change invalidates
    the cache without touching the source file.
    """
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x00")
    return f"sha256:{h.hexdigest()}"


# ---------------------------------------------------------------------------
# Derived Data Cache
# ---------------------------------------------------------------------------

class Ddc:
    """Content-addressable store. Layout: <root>/<ab>/<cd>/<full-hash>.bin"""

    def __init__(self, root: Path) -> None:
        """Create the DDC rooted at `root`. Directory is created on demand."""
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, key: str) -> Path:
        """Return the on-disk path for a given content hash key."""
        # Strip the algorithm prefix for the sharding (not its content).
        try:
            _, hex_ = key.split(":", 1)
        except ValueError as ex:
            raise ValueError("malformed DDC key") from ex
        if len(hex_) != 64 or any(c not in "0123456789abcdef" for c in hex_):
            raise ValueError("malformed DDC digest")
        path = (self.root / hex_[:2] / hex_[2:4] / f"{hex_}.bin").resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("DDC key escapes cache root")
        return path

    def get(self, key: str, dest: Path) -> str | None:
        """Atomically publish a verified DDC entry, returning its output hash."""
        src = self.path_for(key)
        digest_path = src.with_suffix(".hash")
        try:
            expected = digest_path.read_text(encoding="ascii").strip()
        except (OSError, UnicodeError):
            return None
        if not src.is_file() or src.is_symlink():
            return None
        try:
            return _atomic_copy_verified(src, dest, expected)
        except (OSError, ValueError):
            log.warning("discarding corrupt DDC entry: %s", key)
            return None

    def put(self, key: str, src: Path, expected_hash: str) -> None:
        """Atomically insert `src` into the cache under `key`.

        Uses a per-writer-unique temp name so concurrent cooks of the *same*
        key (the ThreadPoolExecutor below can produce these) never write the
        same temp file and corrupt each other. The final rename is atomic on
        the same filesystem (POSIX rename / NTFS MoveFileEx); since content is
        addressed by hash, whichever writer wins the rename is equivalent.
        """
        if not src.is_file() or src.is_symlink():
            raise OSError("DDC source must be a regular file")
        dest = self.path_for(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        actual = _atomic_copy_verified(src, dest, expected_hash)
        digest_path = dest.with_suffix(".hash")
        tmp = digest_path.with_name(
            f"{digest_path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
        try:
            tmp.write_text(actual + "\n", encoding="ascii")
            if tmp.read_text(encoding="ascii").strip() != actual:
                raise OSError("failed to verify DDC hash metadata")
            os.replace(tmp, digest_path)
        finally:
            tmp.unlink(missing_ok=True)


def _atomic_copy_verified(src: Path, dest: Path, expected_hash: str) -> str:
    """Copy to a same-directory temporary, verify bytes, then atomically publish."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f"{dest.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        shutil.copy2(src, tmp)
        actual = content_hash(tmp)
        if actual != expected_hash:
            raise ValueError(f"content hash mismatch: expected {expected_hash}, got {actual}")
        os.replace(tmp, dest)
        return actual
    finally:
        tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Asset descriptors & cook graph
# ---------------------------------------------------------------------------

class AssetKind(StrEnum):
    """High-level asset category; drives which backend cooker runs."""
    TEXTURE = "texture"
    MESH    = "mesh"
    AUDIO   = "audio"
    SHADER  = "shader"
    LEVEL   = "level"
    RAW     = "raw"


@dataclass(slots=True)
class AssetDescriptor:
    """Declarative record for a single source asset.

    Attributes
    ----------
    source:
        Absolute path to the source file.
    rel:
        Path relative to the content root; determines output layout.
    kind:
        Asset category selecting the cook backend.
    options:
        Backend-specific parameters (compression, mip count, ...). Must be
        JSON-serializable so they can participate in the DDC key.
    dependencies:
        Other descriptors this asset consumes at cook time (e.g. a material
        referencing its textures). Resolved by CookGraph into edges.
    """
    source: Path
    rel: Path
    kind: AssetKind
    options: dict[str, object] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.rel.is_absolute() or not self.rel.parts or ".." in self.rel.parts:
            raise ValueError(f"invalid relative asset path: {self.rel}")
        if len(self.dependencies) != len(set(self.dependencies)):
            raise ValueError(f"duplicate dependencies for {self.rel.as_posix()}")
        if self.rel.as_posix() in self.dependencies:
            raise ValueError(f"asset depends on itself: {self.rel.as_posix()}")

    @property
    def id(self) -> str:
        """Stable identifier: the POSIX form of the relative path."""
        return self.rel.as_posix()


class CookGraph:
    """DAG of AssetDescriptors with dependency edges.

    Edges point from a descriptor to the descriptors it depends on. A
    topological sort yields a cook order that guarantees dependencies are
    cooked before dependents.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, AssetDescriptor] = {}

    def add(self, d: AssetDescriptor) -> None:
        """Insert a descriptor. Raises ValueError if the id already exists."""
        if d.id in self._nodes:
            raise ValueError(f"duplicate asset id: {d.id}")
        if len(d.dependencies) != len(set(d.dependencies)):
            raise ValueError(f"duplicate dependencies for {d.id}")
        if d.id in d.dependencies:
            raise ValueError(f"asset depends on itself: {d.id}")
        self._nodes[d.id] = d

    def __contains__(self, asset_id: str) -> bool:
        return asset_id in self._nodes

    def __iter__(self) -> Iterator[AssetDescriptor]:
        return iter(self._nodes.values())

    def descriptor(self, asset_id: str) -> AssetDescriptor:
        return self._nodes[asset_id]

    def topo_order(self) -> list[AssetDescriptor]:
        """Kahn's algorithm. Raises ValueError on cycle or missing dep."""
        indeg: dict[str, int] = {n: 0 for n in self._nodes}
        for d in self._nodes.values():
            for dep in d.dependencies:
                if dep not in self._nodes:
                    raise ValueError(f"missing dependency: {dep} (from {d.id})")
                indeg[d.id] += 1

        ready = [n for n, k in indeg.items() if k == 0]
        order: list[AssetDescriptor] = []
        while ready:
            n = ready.pop(0)
            order.append(self._nodes[n])
            for d in self._nodes.values():
                if n in d.dependencies:
                    indeg[d.id] -= 1
                    if indeg[d.id] == 0:
                        ready.append(d.id)

        if len(order) != len(self._nodes):
            raise ValueError("cycle detected in cook graph")
        return order


# ---------------------------------------------------------------------------
# Cook backends
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CookContext:
    """Read-only inputs made available to a backend for one asset."""
    platform: Platform
    output_root: Path
    dependency_artifacts: Mapping[str, Path]
    dependency_hashes: Mapping[str, str]


class CookBackend(Protocol):
    """Implementers convert one source file to one cooked file."""

    cache_identity: str

    def cook(self, d: AssetDescriptor, context: CookContext, dest: Path) -> None:
        ...


class PassthroughBackend:
    """Copies the source byte-for-byte. Useful for raw data and stand-in cookers."""

    cache_identity = "passthrough/shutil-copy/v1"

    def cook(self, d: AssetDescriptor, context: CookContext, dest: Path) -> None:  # noqa: ARG002
        """Copy d.source to dest. Parent directory is created on demand."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(d.source, dest)


def default_backends() -> dict[AssetKind, CookBackend]:
    """Return the default backend registry.

    Real backends (texture BCn, mesh meshoptimizer, etc.) replace the
    passthrough entries at integration time. They MUST produce deterministic
    output for a given (source-hash, options, platform) triple, otherwise the
    DDC will thrash.
    """
    pt = PassthroughBackend()
    return {k: pt for k in AssetKind}


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class CookResult:
    """Per-asset outcome reported by CookWorker."""
    asset_id: str
    ok: bool
    cache_hit: bool
    seconds: float
    output_hash: str | None = None
    error: str | None = None


class CookWorker:
    """Executes a CookGraph against a platform, using a DDC for incrementality."""

    def __init__(
        self,
        *,
        platform: Platform,
        output_root: Path,
        ddc: Ddc | None,
        backends: dict[AssetKind, CookBackend] | None = None,
        max_workers: int = 8,
    ) -> None:
        """Wire the worker. `ddc=None` disables incremental cooking."""
        self.platform     = platform
        self.output_root  = output_root.resolve()
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.ddc          = ddc
        self.backends     = backends or default_backends()
        self.max_workers  = max(1, max_workers)

    def run(self, graph: CookGraph) -> list[CookResult]:
        """Cook every asset in `graph` in topological order.

        Parallelism is bounded by `max_workers`; dependencies are honored by
        executing levels of the DAG sequentially. Returns one CookResult per
        descriptor.
        """
        order = graph.topo_order()
        results: list[CookResult] = []

        # Simple level-by-level parallelism: within a level all assets have no
        # unsatisfied deps. A production pipeline would use a work-stealing
        # scheduler; this scaffold favors clarity.
        done: dict[str, CookResult] = {}
        pending = list(order)
        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            while pending:
                level = [d for d in pending if all(dep in done for dep in d.dependencies)]
                if not level:
                    raise RuntimeError("cook graph stalled; dependency bug?")
                futures: list[tuple[AssetDescriptor, Future[CookResult]]] = []
                for d in level:
                    failed = [dep for dep in d.dependencies if not done[dep].ok]
                    if failed:
                        r = CookResult(
                            d.id, ok=False, cache_hit=False, seconds=0.0,
                            error=f"blocked by failed dependencies: {', '.join(failed)}")
                        results.append(r)
                        done[d.id] = r
                        continue
                    dependency_hashes: dict[str, str] = {}
                    dependency_artifacts: dict[str, Path] = {}
                    for dep in d.dependencies:
                        digest = done[dep].output_hash
                        if digest is None:
                            raise RuntimeError("successful dependency has no output hash")
                        artifact = platform_output_path(
                            self.output_root, self.platform, graph.descriptor(dep).rel)
                        if not artifact.is_file() or artifact.is_symlink():
                            raise RuntimeError(
                                f"successful dependency has no regular artifact: {dep}")
                        dependency_hashes[dep] = digest
                        dependency_artifacts[dep] = artifact
                    futures.append((
                        d,
                        ex.submit(
                            self._cook_one, d, dependency_hashes, dependency_artifacts),
                    ))
                for d, fut in futures:
                    r = fut.result()
                    results.append(r)
                    done[d.id] = r
                pending = [d for d in pending if d.id not in done]

        return results

    # ------------------------------------------------------------------ #

    def _ddc_key(
        self,
        d: AssetDescriptor,
        dependency_hashes: dict[str, str],
        source_hash: str,
    ) -> str:
        """Fold all output-affecting inputs and tool identities into the key."""
        options_blob = json.dumps(d.options, sort_keys=True, separators=(",", ":"))
        backend_identity = self.backends[d.kind].cache_identity
        if not backend_identity:
            raise ValueError(f"backend has no cache identity: {d.kind}")
        dependency_blob = json.dumps(
            [(dep, dependency_hashes[dep]) for dep in d.dependencies],
            separators=(",", ":"),
        )
        return combined_hash([
            source_hash,
            dependency_blob,
            options_blob,
            self.platform.value,
            d.kind.value,
            backend_identity,
            COOKER_IDENTITY,
        ])

    def _cook_one(
        self,
        d: AssetDescriptor,
        dependency_hashes: dict[str, str],
        dependency_artifacts: dict[str, Path],
    ) -> CookResult:
        """Cook a single descriptor. Never raises; errors are captured in the result."""
        start = time.perf_counter()
        temp: Path | None = None
        key: str | None = None
        try:
            dest = platform_output_path(self.output_root, self.platform, d.rel)
            dest.parent.mkdir(parents=True, exist_ok=True)
            # Resolve again after parent creation so a pre-existing symlink
            # component cannot redirect publication outside the platform root.
            if platform_output_path(self.output_root, self.platform, d.rel) != dest:
                raise OSError(f"output path changed during validation: {d.rel}")
            temp = dest.with_name(f"{dest.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
            assert temp is not None
            source_hash = content_hash(d.source)

            if self.ddc is not None:
                key = self._ddc_key(d, dependency_hashes, source_hash)
                output_hash = self.ddc.get(key, dest)
                if output_hash is not None:
                    return CookResult(d.id, ok=True, cache_hit=True,
                                      seconds=time.perf_counter() - start,
                                      output_hash=output_hash)

            backend = self.backends[d.kind]
            # Backends consume immutable verified snapshots, not mutable source/DDC
            # paths. This prevents a concurrent source replacement from publishing
            # version-B output under version-A's content key.
            # d.id is a relative asset path and may contain separators; never use
            # it as a TemporaryDirectory prefix.
            with tempfile.TemporaryDirectory(prefix="asset-cook-") as snapshot_dir:
                snapshot_root = Path(snapshot_dir)
                source_snapshot = snapshot_root / f"source{d.source.suffix}"
                shutil.copyfile(d.source, source_snapshot)
                if content_hash(source_snapshot) != source_hash:
                    raise OSError(f"source changed while snapshotting: {d.source}")

                dependency_snapshots: dict[str, Path] = {}
                for dep, artifact in dependency_artifacts.items():
                    snapshot = snapshot_root / "dependencies" / dep / artifact.name
                    snapshot.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(artifact, snapshot)
                    if content_hash(snapshot) != dependency_hashes[dep]:
                        raise OSError(f"dependency changed while snapshotting: {dep}")
                    dependency_snapshots[dep] = snapshot

                context = CookContext(
                    platform=self.platform,
                    output_root=self.output_root,
                    dependency_artifacts=MappingProxyType(dependency_snapshots),
                    dependency_hashes=MappingProxyType(dict(dependency_hashes)),
                )
                backend.cook(replace(d, source=source_snapshot), context, temp)
            if not temp.is_file() or temp.is_symlink():
                raise OSError("backend did not produce a regular output file")
            output_hash = content_hash(temp)

            if self.ddc is not None:
                assert key is not None
                self.ddc.put(key, temp, output_hash)

            os.replace(temp, dest)

            return CookResult(d.id, ok=True, cache_hit=False,
                              seconds=time.perf_counter() - start,
                              output_hash=output_hash)

        except Exception as ex:  # noqa: BLE001 - we report, we don't crash the pool
            log.exception("cook failed: %s", d.id)
            return CookResult(d.id, ok=False, cache_hit=False,
                              seconds=time.perf_counter() - start,
                              error=f"{type(ex).__name__}: {ex}")
        finally:
            if temp is not None:
                try:
                    temp.unlink(missing_ok=True)
                except OSError:
                    log.warning("failed to remove temporary output: %s", temp)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _discover(input_root: Path) -> CookGraph:
    """Walk `input_root` and produce a trivial CookGraph for the scaffold.

    Production pipelines parse .asset descriptor files or query a scene DB;
    this helper simply classifies by extension so the scaffold runs end-to-end.
    """
    ext_to_kind = {
        ".png": AssetKind.TEXTURE, ".tga": AssetKind.TEXTURE, ".exr": AssetKind.TEXTURE,
        ".fbx": AssetKind.MESH,    ".gltf": AssetKind.MESH,
        ".wav": AssetKind.AUDIO,   ".ogg": AssetKind.AUDIO,
        ".hlsl": AssetKind.SHADER, ".glsl": AssetKind.SHADER,
        ".level": AssetKind.LEVEL,
    }
    input_root = input_root.resolve(strict=True)
    graph = CookGraph()
    for path in input_root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"symlinked content is not allowed: {path}")
        if not path.is_file():
            continue
        source = path.resolve(strict=True)
        if not source.is_relative_to(input_root):
            raise ValueError(f"source escapes input root: {path}")
        kind = ext_to_kind.get(path.suffix.lower(), AssetKind.RAW)
        graph.add(AssetDescriptor(
            source=source,
            rel=path.relative_to(input_root),
            kind=kind,
        ))
    return graph


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse and validate CLI arguments."""
    p = argparse.ArgumentParser(description="Engine asset cooker")
    p.add_argument("--platform", required=True, choices=[p.value for p in Platform])
    p.add_argument("--input",    required=True, type=Path, help="content source root")
    p.add_argument("--output",   required=True, type=Path, help="cooked output root")
    p.add_argument("--ddc",      type=Path, default=None, help="derived-data cache root")
    p.add_argument("--incremental", action="store_true", help="enable DDC-backed skipping")
    p.add_argument("--jobs",     type=int, default=8, help="max parallel cook jobs")
    p.add_argument("--verbose",  action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if not args.input.is_dir():
        log.error("input root does not exist: %s", args.input)
        return 2

    try:
        ddc: Ddc | None = None
        if args.incremental:
            if args.ddc is None:
                log.error("--incremental requires --ddc <path>")
                return 2
            ddc = Ddc(args.ddc)
        graph = _discover(args.input)
        worker = CookWorker(
            platform=Platform(args.platform),
            output_root=args.output,
            ddc=ddc,
            max_workers=args.jobs,
        )
        wall_start = time.perf_counter()
        results = worker.run(graph)
        wall_s = time.perf_counter() - wall_start
    except (OSError, ValueError, RuntimeError) as ex:
        log.error("cook setup failed: %s: %s", type(ex).__name__, ex)
        return 2

    failures = [r for r in results if not r.ok]
    hits     = sum(1 for r in results if r.cache_hit)
    worker_s = sum(r.seconds for r in results)
    log.info("cooked %d assets (%d cache hits, %d failures) in %.2fs wall "
             "(%.2fs aggregate worker time)",
             len(results), hits, len(failures), wall_s, worker_s)

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
