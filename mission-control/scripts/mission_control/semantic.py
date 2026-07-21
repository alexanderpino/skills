"""Semantic target indexing, conflict detection, and committed-diff scope.

Python uses the stdlib AST.  Unsupported, generated, unparsable, and
non-semantic-only changes deliberately collapse to a file target.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .models import bytes_hash, json_text, normalize_path


TARGET_TYPES = ("file", "symbol", "synthetic")
SYNTHETIC_AREAS = (
    "imports", "globals", "preprocessor", "module-members",
)
SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _git(
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


def _anchor(path: str, kind: str, qualified: str) -> str:
    value = f"python-ast-v1\0{path}\0{kind}\0{qualified}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _file_target(
    path: str, *, commit: str | None, blob: str | None,
    adapter: str, diagnostic: str,
) -> dict[str, Any]:
    return {
        "path": normalize_path(path),
        "type": "file",
        "qualified_symbol": None,
        "node_kind": "file",
        "base_blob": blob,
        "base_commit": commit,
        "structural_anchor_hash": None,
        "adapter": adapter,
        "diagnostic": diagnostic,
    }


def canonical_target(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("semantic target must be a JSON object")
    target_type = value.get("type")
    if target_type not in TARGET_TYPES:
        raise ValueError("semantic target.type must be file, symbol, or synthetic")
    result = dict(value)
    result["path"] = normalize_path(value.get("path"))
    qualified = value.get("qualified_symbol")
    if target_type == "file":
        if qualified not in (None, ""):
            raise ValueError("file targets cannot name qualified_symbol")
        result["qualified_symbol"] = None
        result.setdefault("node_kind", "file")
        result.setdefault("structural_anchor_hash", None)
    else:
        if not isinstance(qualified, str) or not qualified.strip():
            raise ValueError(
                f"{target_type} target requires qualified_symbol")
        result["qualified_symbol"] = qualified.strip()
        if target_type == "synthetic" and \
                qualified not in SYNTHETIC_AREAS:
            raise ValueError(
                "synthetic qualified_symbol must be one of "
                + ", ".join(SYNTHETIC_AREAS))
        if not isinstance(result.get("node_kind"), str):
            raise ValueError("semantic target.node_kind must be a string")
        anchor = result.get("structural_anchor_hash")
        if not isinstance(anchor, str) or not re.fullmatch(
                r"[0-9a-f]{64}", anchor):
            raise ValueError(
                "semantic target.structural_anchor_hash must be SHA-256")
    for field_name in ("base_blob", "base_commit"):
        field_value = result.get(field_name)
        if field_value is not None and not isinstance(field_value, str):
            raise ValueError(f"semantic target.{field_name} must be string/null")
        result.setdefault(field_name, None)
    result.setdefault("adapter", "explicit")
    return result


def target_key(target: dict[str, Any]) -> tuple[str, str, str]:
    target = canonical_target(target)
    return (
        target["path"], target["type"],
        target.get("qualified_symbol") or "",
    )


def _path_hierarchy_conflict(left: str, right: str) -> bool:
    left, right = normalize_path(left), normalize_path(right)
    return left == right or left.startswith(right.rstrip("/") + "/") or \
        right.startswith(left.rstrip("/") + "/")


def _symbol_ancestor(left: str, right: str) -> bool:
    return left == right or left.startswith(right + ".") or \
        right.startswith(left + ".")


def targets_conflict(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """Return whether two lease targets are mutually exclusive."""
    left, right = canonical_target(left), canonical_target(right)
    if left["type"] == "file" or right["type"] == "file":
        return _path_hierarchy_conflict(left["path"], right["path"])
    if left["path"] != right["path"]:
        return False
    if left["type"] == right["type"] == "symbol":
        return _symbol_ancestor(
            left["qualified_symbol"], right["qualified_symbol"])
    if left["type"] == right["type"] == "synthetic":
        return left["qualified_symbol"] == right["qualified_symbol"]
    if left["type"] == "synthetic":
        synthetic, symbol = left, right
    else:
        synthetic, symbol = right, left
    # Changing the module member structure can invalidate every top-level
    # symbol anchor. Imports and global statements remain sibling resources.
    return synthetic["qualified_symbol"] == "module-members" and \
        "." not in symbol["qualified_symbol"]


def target_covers(lease: dict[str, Any], changed: dict[str, Any]) -> bool:
    lease, changed = canonical_target(lease), canonical_target(changed)
    if lease["type"] == "file":
        path = lease["path"]
        return changed["path"] == path or \
            changed["path"].startswith(path.rstrip("/") + "/")
    if lease["path"] != changed["path"]:
        return False
    if lease["type"] == "symbol" and changed["type"] == "symbol":
        owned = lease["qualified_symbol"]
        actual = changed["qualified_symbol"]
        return actual == owned or actual.startswith(owned + ".")
    return lease["type"] == changed["type"] == "synthetic" and \
        lease["qualified_symbol"] == changed["qualified_symbol"]


def _canonical_ast(node: Any, *, root: bool = True,
                   omit_root_name: bool = False) -> Any:
    if isinstance(node, SCOPE_NODES) and not root:
        return ("nested-scope", type(node).__name__, node.name)
    if isinstance(node, ast.AST):
        fields = []
        for name, value in ast.iter_fields(node):
            if name in ("ctx", "type_comment"):
                continue
            if root and omit_root_name and name == "name":
                continue
            fields.append((
                name,
                _canonical_ast(
                    value, root=False, omit_root_name=omit_root_name),
            ))
        return (type(node).__name__, tuple(fields))
    if isinstance(node, list):
        return tuple(
            _canonical_ast(value, root=False,
                           omit_root_name=omit_root_name)
            for value in node
        )
    return node


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(repr(value).encode("utf-8")).hexdigest()


@dataclass
class Scope:
    target: dict[str, Any]
    fingerprint: str
    rename_fingerprint: str
    parent: str | None
    node: ast.AST


@dataclass
class SemanticIndex:
    path: str
    commit: str | None
    blob: str | None
    adapter: str
    targets: list[dict[str, Any]]
    diagnostics: list[str] = field(default_factory=list)
    scopes: dict[str, Scope] = field(default_factory=dict, repr=False)
    synthetic_fingerprints: dict[str, str] = field(
        default_factory=dict, repr=False)
    source: str | None = field(default=None, repr=False)

    @property
    def fallback(self) -> bool:
        return len(self.targets) == 1 and self.targets[0]["type"] == "file"

    def public(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "commit": self.commit,
            "blob": self.blob,
            "adapter": self.adapter,
            "fallback": self.fallback,
            "diagnostics": self.diagnostics,
            "targets": self.targets,
        }


class PythonAstAdapter:
    """Robust stdlib Python semantic adapter."""

    name = "python-ast"
    extensions = (".py", ".pyi")

    @staticmethod
    def supports(path: str) -> bool:
        return Path(path).suffix.lower() in PythonAstAdapter.extensions

    def index(
        self, path: str, source: bytes, *, commit: str | None,
        blob: str | None = None,
    ) -> SemanticIndex:
        normalized = normalize_path(path)
        digest = blob or bytes_hash(source)
        try:
            text = source.decode("utf-8")
        except UnicodeDecodeError:
            return SemanticIndex(
                normalized, commit, digest, self.name + "-fallback",
                [_file_target(
                    normalized, commit=commit, blob=digest,
                    adapter=self.name + "-fallback",
                    diagnostic="Python source is not UTF-8")],
                ["Python source is not UTF-8; file lease required"],
            )
        preamble = "\n".join(text.splitlines()[:8])
        if re.search(r"(?i)\b(?:generated|do not edit)\b", preamble):
            return SemanticIndex(
                normalized, commit, digest, self.name + "-fallback",
                [_file_target(
                    normalized, commit=commit, blob=digest,
                    adapter=self.name + "-fallback",
                    diagnostic="generated source")],
                ["generated source detected; file lease required"],
                source=text,
            )
        try:
            tree = ast.parse(text, filename=normalized, type_comments=True)
        except SyntaxError as exc:
            diagnostic = (
                f"Python parse failed ({exc.msg}); file lease required")
            return SemanticIndex(
                normalized, commit, digest, self.name + "-fallback",
                [_file_target(
                    normalized, commit=commit, blob=digest,
                    adapter=self.name + "-fallback",
                    diagnostic=diagnostic)],
                [diagnostic],
                source=text,
            )
        scopes: dict[str, Scope] = {}

        def walk(body: Iterable[ast.stmt], parent: str | None = None) -> None:
            for node in body:
                if not isinstance(node, SCOPE_NODES):
                    continue
                qualified = node.name if parent is None else \
                    f"{parent}.{node.name}"
                kind = type(node).__name__
                target = {
                    "path": normalized,
                    "type": "symbol",
                    "qualified_symbol": qualified,
                    "node_kind": kind,
                    "base_blob": digest,
                    "base_commit": commit,
                    "structural_anchor_hash": _anchor(
                        normalized, kind, qualified),
                    "adapter": self.name,
                }
                scopes[qualified] = Scope(
                    target=target,
                    fingerprint=_fingerprint(_canonical_ast(node)),
                    rename_fingerprint=_fingerprint(
                        _canonical_ast(node, omit_root_name=True)),
                    parent=parent,
                    node=node,
                )
                walk(node.body, qualified)

        walk(tree.body)
        imports = [
            node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        globals_ = [
            node for node in tree.body
            if not isinstance(node, (ast.Import, ast.ImportFrom, *SCOPE_NODES))
        ]
        members = [
            (type(node).__name__, node.name)
            for node in tree.body if isinstance(node, SCOPE_NODES)
        ]
        synthetic_values = {
            "imports": imports,
            "globals": globals_,
            "module-members": members,
        }
        synthetics: list[dict[str, Any]] = []
        synthetic_fingerprints: dict[str, str] = {}
        for area, nodes in synthetic_values.items():
            canonical = _canonical_ast(nodes)
            synthetic_fingerprints[area] = _fingerprint(canonical)
            synthetics.append({
                "path": normalized,
                "type": "synthetic",
                "qualified_symbol": area,
                "node_kind": "synthetic",
                "base_blob": digest,
                "base_commit": commit,
                "structural_anchor_hash": _anchor(
                    normalized, "synthetic", area),
                "adapter": self.name,
            })
        return SemanticIndex(
            normalized, commit, digest, self.name,
            [scope.target for scope in scopes.values()] + synthetics,
            [], scopes, synthetic_fingerprints, text,
        )


class SemanticRegistry:
    """Adapter discovery seam with a conservative file fallback."""

    def __init__(self, adapters: Iterable[Any] | None = None):
        self.adapters = list(adapters or [PythonAstAdapter()])

    def adapter_for(self, path: str) -> Any | None:
        return next(
            (adapter for adapter in self.adapters if adapter.supports(path)),
            None,
        )

    def index_bytes(
        self, path: str, source: bytes, *, commit: str | None,
        blob: str | None = None,
    ) -> SemanticIndex:
        adapter = self.adapter_for(path)
        normalized = normalize_path(path)
        digest = blob or bytes_hash(source)
        if adapter is None:
            extension = Path(path).suffix or "<none>"
            diagnostic = (
                f"unsupported language {extension}; file lease required")
            return SemanticIndex(
                normalized, commit, digest, "file-fallback",
                [_file_target(
                    normalized, commit=commit, blob=digest,
                    adapter="file-fallback", diagnostic=diagnostic)],
                [diagnostic],
            )
        return adapter.index(path, source, commit=commit, blob=digest)

    def index_repo(
        self, repo: Path, path: str, *, commit: str = "HEAD",
    ) -> SemanticIndex:
        normalized = normalize_path(path)
        resolved_commit = _git(
            repo, ["rev-parse", commit]).stdout.strip()
        result = _git(
            repo, ["show", f"{resolved_commit}:{normalized}"], check=False)
        if result.returncode:
            raise ValueError(
                f"{normalized} does not exist at {resolved_commit}")
        raw = result.stdout.encode("utf-8")
        blob = _git(
            repo, ["rev-parse", f"{resolved_commit}:{normalized}"]
        ).stdout.strip()
        return self.index_bytes(
            normalized, raw, commit=resolved_commit, blob=blob)

    def resolve(
        self, repo: Path, path: str, target_type: str,
        qualified: str | None = None, *, commit: str = "HEAD",
    ) -> dict[str, Any]:
        index = self.index_repo(repo, path, commit=commit)
        if target_type == "file":
            return _file_target(
                index.path, commit=index.commit, blob=index.blob,
                adapter=index.adapter,
                diagnostic=(
                    index.diagnostics[0] if index.diagnostics
                    else "explicit file target"),
            )
        if index.fallback:
            raise ValueError(
                f"{index.path} has no safe semantic adapter: "
                f"{'; '.join(index.diagnostics)}")
        match = next(
            (target for target in index.targets
             if target["type"] == target_type
             and target["qualified_symbol"] == qualified),
            None,
        )
        if match is None:
            choices = [
                target["qualified_symbol"] for target in index.targets
                if target["type"] == target_type
            ]
            raise ValueError(
                f"no {target_type} target {qualified!r} in {index.path}; "
                f"available: {', '.join(choices) or 'none'}")
        return match


def _show_bytes(repo: Path, commit: str, path: str) -> bytes | None:
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{path}"],
        capture_output=True,
    )
    return None if result.returncode else result.stdout


def changed_paths(
    repo: Path, base: str, result: str,
) -> list[tuple[str, str, str | None]]:
    diff = _git(
        repo, ["diff", "--name-status", "-M", f"{base}..{result}"],
        check=False,
    )
    if diff.returncode:
        raise ValueError("cannot inspect committed diff")
    output: list[tuple[str, str, str | None]] = []
    for line in diff.stdout.splitlines():
        fields = line.split("\t")
        status = fields[0]
        if status.startswith(("R", "C")) and len(fields) == 3:
            output.append((status[0], normalize_path(fields[1]),
                           normalize_path(fields[2])))
        elif len(fields) >= 2:
            output.append((status[0], normalize_path(fields[1]), None))
    return output


def _changed_python_targets(
    before: SemanticIndex, after: SemanticIndex,
) -> list[dict[str, Any]]:
    if before.fallback or after.fallback:
        diagnostic = "; ".join(before.diagnostics + after.diagnostics)
        return [_file_target(
            before.path, commit=before.commit, blob=before.blob,
            adapter="file-fallback",
            diagnostic=diagnostic or "unmappable semantic change",
        )]
    changed: list[dict[str, Any]] = []
    before_names, after_names = set(before.scopes), set(after.scopes)
    for name in sorted(before_names & after_names):
        if before.scopes[name].fingerprint != after.scopes[name].fingerprint:
            target = dict(before.scopes[name].target)
            target["change"] = "modified"
            target["result_anchor_hash"] = \
                after.scopes[name].target["structural_anchor_hash"]
            changed.append(target)
    removed = set(before_names - after_names)
    added = set(after_names - before_names)
    # A rename is safe to map only when kind, parent, and the complete
    # name-independent structure match uniquely.
    rename_pairs: list[tuple[str, str]] = []
    for old in sorted(removed):
        candidates = [
            new for new in added
            if before.scopes[old].rename_fingerprint ==
            after.scopes[new].rename_fingerprint
            and before.scopes[old].parent == after.scopes[new].parent
            and before.scopes[old].target["node_kind"] ==
            after.scopes[new].target["node_kind"]
        ]
        if len(candidates) == 1:
            reverse = [
                candidate for candidate in removed
                if before.scopes[candidate].rename_fingerprint ==
                after.scopes[candidates[0]].rename_fingerprint
                and before.scopes[candidate].parent ==
                after.scopes[candidates[0]].parent
            ]
            if len(reverse) == 1:
                rename_pairs.append((old, candidates[0]))
    for old, new in rename_pairs:
        removed.discard(old)
        added.discard(new)
        target = dict(before.scopes[old].target)
        target["change"] = "renamed"
        target["result_qualified_symbol"] = new
        target["result_anchor_hash"] = \
            after.scopes[new].target["structural_anchor_hash"]
        changed.append(target)
    for old in sorted(removed):
        target = dict(before.scopes[old].target)
        target["change"] = "deleted"
        changed.append(target)
    for new in sorted(added):
        scope = after.scopes[new]
        if scope.parent is not None:
            parent = before.scopes.get(scope.parent) or \
                after.scopes.get(scope.parent)
            if parent is None:
                return [_file_target(
                    before.path, commit=before.commit, blob=before.blob,
                    adapter="file-fallback",
                    diagnostic="new nested symbol parent cannot be mapped",
                )]
            target = dict(parent.target)
            target["change"] = "child-added"
            target["affected_symbol"] = new
            changed.append(target)
        else:
            target = next(
                target for target in before.targets
                if target["type"] == "synthetic"
                and target["qualified_symbol"] == "module-members")
            target = dict(target)
            target["change"] = "symbol-added"
            target["affected_symbol"] = new
            changed.append(target)
    for area in ("imports", "globals"):
        if before.synthetic_fingerprints[area] != \
                after.synthetic_fingerprints[area]:
            target = next(
                target for target in before.targets
                if target["type"] == "synthetic"
                and target["qualified_symbol"] == area)
            target = dict(target)
            target["change"] = "modified"
            changed.append(target)
    # AST equality plus byte inequality is comments, whitespace, encoding, or
    # another structure the adapter cannot own reliably.
    if not changed and before.blob != after.blob:
        return [_file_target(
            before.path, commit=before.commit, blob=before.blob,
            adapter="file-fallback",
            diagnostic="formatting/comment-only or unmappable change",
        )]
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for target in changed:
        unique[target_key(target)] = target
    return list(unique.values())


def map_committed_diff(
    repo: Path, base: str, result: str,
    *, registry: SemanticRegistry | None = None,
) -> dict[str, Any]:
    registry = registry or SemanticRegistry()
    base_commit = _git(repo, ["rev-parse", base]).stdout.strip()
    result_commit = _git(repo, ["rev-parse", result]).stdout.strip()
    changes = changed_paths(repo, base_commit, result_commit)
    if not changes:
        raise ValueError("implementation has no committed diff")
    targets: list[dict[str, Any]] = []
    diagnostics: list[str] = []
    for status, old_path, new_path in changes:
        if status in ("R", "C"):
            diagnostics.append(
                f"{status} {old_path} -> {new_path}: file leases required")
            targets.append(_file_target(
                old_path, commit=base_commit, blob=None,
                adapter="file-fallback", diagnostic="renamed/copied path"))
            targets.append(_file_target(
                new_path or old_path, commit=base_commit, blob=None,
                adapter="file-fallback", diagnostic="renamed/copied path"))
            continue
        before_bytes = _show_bytes(repo, base_commit, old_path)
        after_bytes = _show_bytes(repo, result_commit, old_path)
        if before_bytes is None or after_bytes is None:
            diagnostic = (
                f"{status} {old_path}: added/deleted file requires file lease")
            diagnostics.append(diagnostic)
            targets.append(_file_target(
                old_path, commit=base_commit,
                blob=bytes_hash(before_bytes or after_bytes or b""),
                adapter="file-fallback", diagnostic=diagnostic))
            continue
        before = registry.index_bytes(
            old_path, before_bytes, commit=base_commit)
        after = registry.index_bytes(
            old_path, after_bytes, commit=result_commit)
        mapped = _changed_python_targets(before, after) \
            if before.adapter.startswith("python-ast") and \
            after.adapter.startswith("python-ast") else [
                _file_target(
                    old_path, commit=base_commit,
                    blob=before.blob, adapter="file-fallback",
                    diagnostic=(
                        "; ".join(before.diagnostics + after.diagnostics)
                        or "unsupported semantic diff"),
                )
            ]
        targets.extend(mapped)
        diagnostics.extend(before.diagnostics + after.diagnostics)
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for target in targets:
        unique[target_key(target)] = target
    return {
        "base_commit": base_commit,
        "result_commit": result_commit,
        "changed_paths": [
            {"status": status, "path": old, "result_path": new}
            for status, old, new in changes
        ],
        "changed_targets": list(unique.values()),
        "diagnostics": list(dict.fromkeys(diagnostics)),
    }


def validate_committed_scope(
    repo: Path, base: str, result: str,
    leases: list[dict[str, Any]],
    *, registry: SemanticRegistry | None = None,
) -> dict[str, Any]:
    report = map_committed_diff(repo, base, result, registry=registry)
    canonical_leases = [
        canonical_target(lease.get("target", lease)) for lease in leases
    ]
    uncovered = [
        changed for changed in report["changed_targets"]
        if not any(target_covers(lease, changed)
                   for lease in canonical_leases)
    ]
    report.update({
        "leased_targets": canonical_leases,
        "uncovered_targets": uncovered,
        "verdict": "green" if not uncovered else "red",
    })
    return report


def parse_target_json(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid semantic target JSON: {exc}") from exc
    return canonical_target(value)


def targets_overlap(
    left: Iterable[dict[str, Any]], right: Iterable[dict[str, Any]],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    return [
        (a, b) for a in left for b in right if targets_conflict(a, b)
    ]


def replace_disjoint_python_symbols(
    base_source: str, ours_source: str, theirs_source: str,
    path: str, ours_names: set[str], theirs_names: set[str],
) -> str:
    """Combine sibling symbol bodies for a mechanical conflict resolution."""
    if any(_symbol_ancestor(a, b) for a in ours_names for b in theirs_names):
        raise ValueError("same/ancestor Python symbol changed on both sides")
    adapter = PythonAstAdapter()
    ours = adapter.index(
        path, ours_source.encode(), commit="ours", blob=bytes_hash(
            ours_source.encode()))
    theirs = adapter.index(
        path, theirs_source.encode(), commit="theirs", blob=bytes_hash(
            theirs_source.encode()))
    if ours.fallback or theirs.fallback:
        raise ValueError("Python conflict cannot be parsed safely")
    lines = ours_source.splitlines(keepends=True)
    replacements: list[tuple[int, int, list[str]]] = []
    theirs_lines = theirs_source.splitlines(keepends=True)
    for name in theirs_names:
        ours_scope = ours.scopes.get(name)
        theirs_scope = theirs.scopes.get(name)
        if ours_scope is None or theirs_scope is None:
            raise ValueError(
                "automatic disjoint resolution only supports existing symbols")
        ours_node, theirs_node = ours_scope.node, theirs_scope.node
        if not all(hasattr(node, "end_lineno") for node in (
                ours_node, theirs_node)):
            raise ValueError("Python runtime lacks end positions")
        replacements.append((
            ours_node.lineno - 1,
            ours_node.end_lineno,
            theirs_lines[theirs_node.lineno - 1:theirs_node.end_lineno],
        ))
    for start, end, replacement in sorted(replacements, reverse=True):
        lines[start:end] = replacement
    merged = "".join(lines)
    ast.parse(merged, filename=path)
    return merged
