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

Usage::

    python asset_cooker_template.py \\
        --platform win64 \\
        --input  ./content \\
        --output ./cooked/win64 \\
        --ddc    ./ddc \\
        --incremental

Exit codes:
    0 - all assets cooked (or cache-hit) successfully
    1 - one or more assets failed
    2 - bad CLI arguments / environment
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import logging
import shutil
import sys
import time
from collections.abc import Iterable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Protocol

try:
    import blake3  # type: ignore[import-not-found]
    _HAS_BLAKE3 = True
except ImportError:  # pragma: no cover - fallback path
    _HAS_BLAKE3 = False


log = logging.getLogger("asset_cooker")


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
    return root / platform.value / rel.with_suffix(rel.suffix + ".cooked")


# ---------------------------------------------------------------------------
# Content-addressable hashing
# ---------------------------------------------------------------------------

def content_hash(path: Path, *, chunk: int = 1 << 20) -> str:
    """Return a hex digest of the file at `path`.

    Uses BLAKE3 when available (fast, parallelizable) and falls back to
    SHA-256 otherwise. The output is prefixed with the algorithm so mismatched
    DDC entries can be detected and migrated.
    """
    if _HAS_BLAKE3:
        h = blake3.blake3()
        algo = "b3"
    else:
        h = hashlib.sha256()
        algo = "s2"

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
    return f"s2:{h.hexdigest()}"


# ---------------------------------------------------------------------------
# Derived Data Cache
# ---------------------------------------------------------------------------

class Ddc:
    """Content-addressable store. Layout: <root>/<ab>/<cd>/<full-hash>.bin"""

    def __init__(self, root: Path) -> None:
        """Create the DDC rooted at `root`. Directory is created on demand."""
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, key: str) -> Path:
        """Return the on-disk path for a given content hash key."""
        # Strip the algorithm prefix for the sharding (not its content).
        _, hex_ = key.split(":", 1)
        return self.root / hex_[:2] / hex_[2:4] / f"{hex_}.bin"

    def get(self, key: str, dest: Path) -> bool:
        """Copy the DDC entry for `key` to `dest`. Returns False on miss."""
        src = self.path_for(key)
        if not src.exists():
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return True

    def put(self, key: str, src: Path) -> None:
        """Atomically insert `src` into the cache under `key`."""
        dest = self.path_for(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".tmp")
        shutil.copy2(src, tmp)
        tmp.replace(dest)  # atomic on POSIX and NTFS


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
        self._nodes[d.id] = d

    def __contains__(self, asset_id: str) -> bool:
        return asset_id in self._nodes

    def __iter__(self) -> Iterator[AssetDescriptor]:
        return iter(self._nodes.values())

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

class CookBackend(Protocol):
    """Implementers convert one source file to one cooked file."""

    def cook(self, d: AssetDescriptor, platform: Platform, dest: Path) -> None:
        ...


class PassthroughBackend:
    """Copies the source byte-for-byte. Useful for raw data and stand-in cookers."""

    def cook(self, d: AssetDescriptor, platform: Platform, dest: Path) -> None:  # noqa: ARG002
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
        self.output_root  = output_root
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
        done: set[str] = set()
        pending = list(order)
        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            while pending:
                level = [d for d in pending if all(dep in done for dep in d.dependencies)]
                if not level:
                    raise RuntimeError("cook graph stalled; dependency bug?")
                futures: list[tuple[AssetDescriptor, Future[CookResult]]] = [
                    (d, ex.submit(self._cook_one, d)) for d in level
                ]
                for d, fut in futures:
                    r = fut.result()
                    results.append(r)
                    done.add(d.id)
                pending = [d for d in pending if d.id not in done]

        return results

    # ------------------------------------------------------------------ #

    def _ddc_key(self, d: AssetDescriptor) -> str:
        """Fold source hash, options, and platform into a stable cache key."""
        options_blob = json.dumps(d.options, sort_keys=True, separators=(",", ":"))
        return combined_hash([
            content_hash(d.source),
            options_blob,
            self.platform.value,
            d.kind.value,
            # Tool-version salt: bump when backend output format changes.
            "cooker-v1",
        ])

    def _cook_one(self, d: AssetDescriptor) -> CookResult:
        """Cook a single descriptor. Never raises; errors are captured in the result."""
        start = time.perf_counter()
        dest  = platform_output_path(self.output_root, self.platform, d.rel)
        try:
            if self.ddc is not None:
                key = self._ddc_key(d)
                if self.ddc.get(key, dest):
                    return CookResult(d.id, ok=True, cache_hit=True,
                                      seconds=time.perf_counter() - start)

            backend = self.backends[d.kind]
            backend.cook(d, self.platform, dest)

            if self.ddc is not None:
                self.ddc.put(key, dest)  # type: ignore[has-type]

            return CookResult(d.id, ok=True, cache_hit=False,
                              seconds=time.perf_counter() - start)

        except Exception as ex:  # noqa: BLE001 - we report, we don't crash the pool
            log.exception("cook failed: %s", d.id)
            return CookResult(d.id, ok=False, cache_hit=False,
                              seconds=time.perf_counter() - start, error=str(ex))


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
    graph = CookGraph()
    for path in input_root.rglob("*"):
        if not path.is_file():
            continue
        kind = ext_to_kind.get(path.suffix.lower(), AssetKind.RAW)
        graph.add(AssetDescriptor(
            source=path.resolve(),
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

    ddc: Ddc | None = None
    if args.incremental:
        if args.ddc is None:
            log.error("--incremental requires --ddc <path>")
            return 2
        ddc = Ddc(args.ddc)

    graph   = _discover(args.input)
    worker  = CookWorker(
        platform=Platform(args.platform),
        output_root=args.output,
        ddc=ddc,
        max_workers=args.jobs,
    )
    results = worker.run(graph)

    failures = [r for r in results if not r.ok]
    hits     = sum(1 for r in results if r.cache_hit)
    total_s  = sum(r.seconds for r in results)
    log.info("cooked %d assets (%d cache hits, %d failures) in %.2fs",
             len(results), hits, len(failures), total_s)

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
