#!/usr/bin/env python3
"""Multi-repo evidence gathering for story-refinery. Stdlib only.

Subcommands
-----------
  manifest   Build or refresh sha-keyed repo manifests (source 2).
  index      Load a provided index and report staleness (source 1).
  scan       Budgeted, hypothesis-driven search across repos (source 3).
  contracts  List contract files and infer cross-repo producer/consumer edges.

Examples
--------
  python evidence.py manifest --config refinery.yaml
  python evidence.py index    --config refinery.yaml
  python evidence.py scan     --config refinery.yaml -q TaxCalculator -q "reverse charge"
  python evidence.py contracts --config refinery.yaml
"""

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _yaml import get, load_config  # noqa: E402

SKIP_DIRS = {
    ".git", "node_modules", "vendor", "dist", "build", "target", ".venv", "venv",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".idea", ".gradle", "bin", "obj",
    ".next", ".nuxt", "coverage", ".tox", "Pods", ".terraform",
}
LANG_BY_EXT = {
    ".py": "python", ".ts": "typescript", ".tsx": "typescript", ".js": "javascript",
    ".jsx": "javascript", ".go": "go", ".rs": "rust", ".java": "java", ".kt": "kotlin",
    ".rb": "ruby", ".cs": "csharp", ".php": "php", ".cpp": "cpp", ".cc": "cpp",
    ".c": "c", ".h": "c-header", ".hpp": "cpp-header", ".sql": "sql", ".sh": "shell",
    ".scala": "scala", ".swift": "swift", ".m": "objc", ".ex": "elixir",
}
TEXT_EXTS = set(LANG_BY_EXT) | {
    ".yaml", ".yml", ".json", ".toml", ".md", ".proto", ".graphql", ".graphqls",
    ".tf", ".ini", ".cfg", ".xml", ".html", ".css", ".scss", ".env",
}
DEFAULT_CONTRACT_GLOBS = [
    "**/openapi*.yaml", "**/openapi*.yml", "**/swagger*.json", "**/*.proto",
    "**/*.graphql", "**/*.graphqls", "**/schema.sql", "**/migrations/**", "**/*.avsc",
]


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run(cmd, cwd=None):
    try:
        out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=20)
        return out.returncode, out.stdout.strip(), out.stderr.strip()
    except Exception as exc:  # noqa: BLE001
        return 1, "", str(exc)


def repo_sha(root):
    code, out, _ = run(["git", "rev-parse", "--short", "HEAD"], cwd=root)
    return out if code == 0 and out else "nogit"


def iter_files(root, limit=200000):
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".cache")]
        for name in filenames:
            full = os.path.join(dirpath, name)
            yield os.path.relpath(full, root).replace(os.sep, "/"), full
            count += 1
            if count >= limit:
                return


def glob_match(rel, pattern):
    if fnmatch.fnmatch(rel, pattern):
        return True
    if pattern.startswith("**/"):
        return fnmatch.fnmatch(rel, pattern[3:]) or fnmatch.fnmatch("/" + rel, "*/" + pattern[3:])
    return False


# --------------------------------------------------------------------- commands

def detect_commands(root, files):
    """Detect build/test/lint commands. CI config wins - it is what gates merges."""
    cmds, sources = {}, {}

    def put(key, value, source):
        if key not in cmds and value:
            cmds[key], sources[key] = value, source

    for rel in files:
        low = rel.lower()
        if low.startswith((".github/workflows/", ".gitlab-ci")) or low in ("azure-pipelines.yml",):
            try:
                with open(os.path.join(root, rel), "r", encoding="utf-8", errors="ignore") as fh:
                    for line in fh:
                        m = re.search(r"^\s*(?:-\s*)?(?:run:|script:)\s*(.+)$", line)
                        if not m:
                            continue
                        c = m.group(1).strip().strip("'\"")
                        if re.search(r"\b(test|pytest|jest|vitest|go test|cargo test)\b", c):
                            put("test", c, rel)
                        elif re.search(r"\b(lint|ruff|eslint|clippy|flake8)\b", c):
                            put("lint", c, rel)
                        elif re.search(r"\b(build|compile)\b", c):
                            put("build", c, rel)
            except OSError:
                pass

    if "package.json" in files:
        try:
            with open(os.path.join(root, "package.json"), "r", encoding="utf-8") as fh:
                scripts = (json.load(fh) or {}).get("scripts", {}) or {}
            for key in ("test", "lint", "build"):
                if key in scripts:
                    put(key, "npm run %s" % key, "package.json")
        except (OSError, ValueError):
            pass
    if "Makefile" in files:
        try:
            with open(os.path.join(root, "Makefile"), "r", encoding="utf-8", errors="ignore") as fh:
                targets = re.findall(r"^([a-zA-Z0-9_.-]+):", fh.read(), re.M)
            for key in ("test", "lint", "build"):
                if key in targets:
                    put(key, "make %s" % key, "Makefile")
        except OSError:
            pass
    if "pyproject.toml" in files or "tox.ini" in files or "pytest.ini" in files:
        put("test", "pytest -q", "python project")
    if "go.mod" in files:
        put("test", "go test ./...", "go.mod")
        put("build", "go build ./...", "go.mod")
    if "Cargo.toml" in files:
        put("test", "cargo test", "Cargo.toml")
        put("build", "cargo build", "Cargo.toml")
    return cmds, sources


def detect_owners(root, files):
    owners = []
    for candidate in ("CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS", ".gitlab/CODEOWNERS"):
        if candidate not in files:
            continue
        try:
            with open(os.path.join(root, candidate), "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    line = line.split("#", 1)[0].strip()
                    if not line:
                        continue
                    parts = line.split()
                    if len(parts) >= 2:
                        owners.append({"glob": parts[0], "owner": " ".join(parts[1:])})
        except OSError:
            pass
        break
    return owners


def detect_deps(root, files):
    internal, external = [], []
    if "package.json" in files:
        try:
            with open(os.path.join(root, "package.json"), "r", encoding="utf-8") as fh:
                pkg = json.load(fh) or {}
            for block in ("dependencies", "devDependencies"):
                external.extend(sorted((pkg.get(block) or {}).keys()))
        except (OSError, ValueError):
            pass
    if "go.mod" in files:
        try:
            with open(os.path.join(root, "go.mod"), "r", encoding="utf-8", errors="ignore") as fh:
                external.extend(re.findall(r"^\s+([\w./-]+)\s+v", fh.read(), re.M))
        except OSError:
            pass
    if "pyproject.toml" in files:
        try:
            with open(os.path.join(root, "pyproject.toml"), "r", encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
            for block in re.findall(r"dependencies\s*=\s*\[(.*?)\]", text, re.S):
                external.extend(re.findall(r'"\s*([A-Za-z0-9_.-]+)', block))
        except OSError:
            pass
    return {"internal": internal, "external": sorted(set(external))[:200]}


def build_manifest(name, root, contract_globs):
    files = [rel for rel, _ in iter_files(root)]
    langs = {}
    for rel in files:
        ext = os.path.splitext(rel)[1].lower()
        if ext in LANG_BY_EXT:
            langs[LANG_BY_EXT[ext]] = langs.get(LANG_BY_EXT[ext], 0) + 1
    modules = {}
    for rel in files:
        parts = rel.split("/")
        key = "/".join(parts[:2]) if len(parts) > 2 else (parts[0] if len(parts) > 1 else ".")
        modules[key] = modules.get(key, 0) + 1
    contracts = [
        {"path": rel, "kind": _contract_kind(rel)}
        for rel in files
        if any(glob_match(rel, g) for g in contract_globs)
    ]
    cmds, cmd_sources = detect_commands(root, set(files))
    entry = [r for r in files if os.path.basename(r) in
             ("main.py", "main.go", "main.ts", "index.ts", "main.rs", "app.py", "Program.cs")]
    return {
        "name": name,
        "root": root,
        "sha": repo_sha(root),
        "generated_at": now_iso(),
        "file_count": len(files),
        "languages": dict(sorted(langs.items(), key=lambda kv: -kv[1])),
        "commands": cmds,
        "command_sources": cmd_sources,
        "entrypoints": entry[:10],
        "modules": [{"path": k, "files": v} for k, v in
                    sorted(modules.items(), key=lambda kv: -kv[1])[:40]],
        "contracts": contracts[:200],
        "owners": detect_owners(root, set(files)),
        "deps": detect_deps(root, set(files)),
    }


def _contract_kind(rel):
    low = rel.lower()
    if "openapi" in low or "swagger" in low:
        return "openapi"
    if low.endswith(".proto"):
        return "protobuf"
    if low.endswith((".graphql", ".graphqls")):
        return "graphql"
    if "/migrations/" in low or low.endswith("schema.sql"):
        return "schema"
    if low.endswith(".avsc"):
        return "avro"
    return "other"


# ------------------------------------------------------------------------ scan

def scan_repo(name, root, queries, budget_files, budget_hits, deadline):
    """Returns (hits, truncated). Both paths treat the query as a literal string so a
    machine with ripgrep and one without produce the same result set."""
    hits, scanned, truncated = [], 0, False
    rg = shutil.which("rg")
    if rg:
        for q in queries:
            if time.time() > deadline:
                truncated = True
                break
            code, out, _ = run([rg, "-n", "--no-heading", "-i", "-F", "--max-count", "40",
                                "-g", "!node_modules", "-g", "!.git", q, "."], cwd=root)
            if code not in (0, 1):
                continue
            lines = out.splitlines()
            if len(lines) > budget_hits:
                truncated = True
            for line in lines[:budget_hits]:
                parts = line.split(":", 2)
                if len(parts) == 3:
                    hits.append({"repo": name, "path": parts[0].lstrip("./"),
                                 "line": int(parts[1]) if parts[1].isdigit() else 0,
                                 "query": q, "text": parts[2].strip()[:200]})
        return hits, truncated

    patterns = [(q, re.compile(re.escape(q), re.I)) for q in queries]
    for rel, full in iter_files(root):
        if time.time() > deadline or scanned >= budget_files or len(hits) >= budget_hits:
            truncated = True
            break
        if os.path.splitext(rel)[1].lower() not in TEXT_EXTS:
            continue
        scanned += 1
        try:
            with open(full, "r", encoding="utf-8", errors="ignore") as fh:
                for lineno, text in enumerate(fh, 1):
                    for q, rx in patterns:
                        if rx.search(text):
                            hits.append({"repo": name, "path": rel, "line": lineno,
                                         "query": q, "text": text.strip()[:200]})
        except OSError:
            continue
    return hits, truncated


# ----------------------------------------------------------------------- index

def load_provided_index(path):
    """Read any external index generically. Returns {repo_name: {'rev':..,'files':[..]}}."""
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    repos = raw.get("repos") or raw.get("repositories") or raw.get("projects") or []
    if isinstance(repos, dict):
        repos = [dict(v, name=k) for k, v in repos.items()]
    out = {}
    for entry in repos:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name") or entry.get("repo") or entry.get("id")
        if not name:
            continue
        out[name] = {
            "rev": entry.get("rev") or entry.get("sha") or entry.get("commit") or "",
            "files": entry.get("files") or entry.get("modules") or [],
            "generated_at": entry.get("generated_at") or raw.get("generated_at") or "",
        }
    return out


# ------------------------------------------------------------------ cross edges

def contract_edges(manifests):
    """producer -> consumer edges inferred from shared contract paths and internal deps."""
    edges, by_contract = [], {}
    for m in manifests:
        for c in m.get("contracts", []):
            by_contract.setdefault(os.path.basename(c["path"]), []).append((m["name"], c["path"]))
    for base, owners in by_contract.items():
        if len(owners) < 2:
            continue
        producer = owners[0][0]
        for consumer, path in owners[1:]:
            edges.append({"contract": base, "producer": producer, "consumer": consumer,
                          "path": path, "confidence": "shared-filename",
                          "direction": "GUESSED - confirm which repo owns this file before "
                                       "ordering subtasks on it"})
    names = {m["name"] for m in manifests}
    for m in manifests:
        for dep in m.get("deps", {}).get("external", []):
            short = dep.split("/")[-1]
            if short in names and short != m["name"]:
                edges.append({"contract": "package:%s" % short, "producer": short,
                              "consumer": m["name"], "path": "", "confidence": "dependency"})
    return edges


# ------------------------------------------------------------------------- cli

def repos_from_config(cfg):
    repos = get(cfg, "evidence.repos", []) or []
    out = []
    for r in repos:
        if isinstance(r, dict) and r.get("name") and r.get("path"):
            out.append((r["name"], os.path.abspath(r["path"])))
    return out


def source_of(cfg, kind):
    for src in get(cfg, "evidence.sources", []) or []:
        if isinstance(src, dict) and src.get("type") == kind:
            return src
    return {}


def cmd_manifest(args, cfg):
    src = source_of(cfg, "cached_manifest")
    outdir = args.out or src.get("dir") or ".refinery/manifests"
    globs = get(cfg, "evidence.contract_globs", DEFAULT_CONTRACT_GLOBS) or DEFAULT_CONTRACT_GLOBS
    os.makedirs(outdir, exist_ok=True)
    manifests = []
    for name, root in repos_from_config(cfg):
        if not os.path.isdir(root):
            print("MISSING  %-12s %s  (mark all claims ASSUMPTION)" % (name, root))
            continue
        sha = repo_sha(root)
        path = os.path.join(outdir, "%s@%s.json" % (name, sha))
        ttl_days = src.get("ttl_days") or 14
        expired = os.path.exists(path) and \
            (time.time() - os.path.getmtime(path)) > ttl_days * 86400
        if expired:
            print("expired  %-12s manifest older than %s day(s) - rebuilding" % (name, ttl_days))
        if os.path.exists(path) and not args.force and not expired:
            with open(path, "r", encoding="utf-8") as fh:
                man = json.load(fh)
            print("cached   %-12s %s" % (name, path))
        else:
            man = build_manifest(name, root, globs)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(man, fh, indent=2)
            print("built    %-12s %s  (%d files)" % (name, path, man["file_count"]))
        manifests.append(man)
    names = {m["name"] for m in manifests}
    for m in manifests:
        deps = m.setdefault("deps", {"internal": [], "external": []})
        deps["internal"] = sorted({d.split("/")[-1] for d in deps.get("external", [])
                                   if d.split("/")[-1] in names and d.split("/")[-1] != m["name"]})
    for m in manifests:
        print("  %-12s sha=%-10s test=%s" % (m["name"], m["sha"], m["commands"].get("test", "-")))
    if args.json:
        print(json.dumps(manifests, indent=2))
    return 0


def cmd_index(args, cfg):
    src = source_of(cfg, "provided_index")
    path = args.path or src.get("path")
    if not path or not os.path.exists(path):
        print("no provided_index at %r - fall through to manifests" % path)
        return 1
    idx = load_provided_index(path)
    print("provided_index %s (adapter=%s) -> %d repos" % (path, src.get("adapter", "?"), len(idx)))
    stale = 0
    for name, root in repos_from_config(cfg):
        entry = idx.get(name)
        if not entry:
            print("  %-12s NOT IN INDEX" % name)
            continue
        live = repo_sha(root) if os.path.isdir(root) else "?"
        ok = entry["rev"].startswith(live) or live.startswith(entry["rev"] or "\0")
        if not ok:
            stale += 1
        print("  %-12s index=%-10s live=%-10s %s" %
              (name, entry["rev"] or "-", live, "OK" if ok else "STALE -> claims become [?]"))
    if stale:
        print("\n%d stale repo(s): re-verify every path:line you intend to cite." % stale)
    return 0


def cmd_scan(args, cfg):
    src = source_of(cfg, "targeted_scan")
    budget_files = args.budget_files or src.get("budget_files") or 400
    budget_secs = args.budget_seconds or src.get("budget_seconds") or 60
    deadline = time.time() + budget_secs
    all_hits, truncated = [], False
    for name, root in repos_from_config(cfg):
        if args.repo and name not in args.repo:
            continue
        if not os.path.isdir(root):
            print("MISSING  %-12s %s  (mark all claims ASSUMPTION)" % (name, root))
            continue
        hits, was_truncated = scan_repo(name, root, args.query, budget_files,
                                        args.budget_hits, deadline)
        all_hits.extend(hits)
        truncated = truncated or was_truncated
    if args.json:
        print(json.dumps({"hits": all_hits, "truncated": truncated}, indent=2))
    else:
        for h in all_hits[: args.limit]:
            print("%s/%s:%d  [%s]  %s" % (h["repo"], h["path"], h["line"], h["query"], h["text"]))
        print("\n%d hit(s)%s" % (len(all_hits), "; BUDGET EXHAUSTED - say so in the refinement"
                                 if truncated else ""))
    return 0


def cmd_contracts(args, cfg):
    src = source_of(cfg, "cached_manifest")
    outdir = src.get("dir") or ".refinery/manifests"
    manifests = []
    for name, root in repos_from_config(cfg):
        if not os.path.isdir(root):
            continue
        path = os.path.join(outdir, "%s@%s.json" % (name, repo_sha(root)))
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                manifests.append(json.load(fh))
        else:
            globs = get(cfg, "evidence.contract_globs", DEFAULT_CONTRACT_GLOBS)
            manifests.append(build_manifest(name, root, globs or DEFAULT_CONTRACT_GLOBS))
    edges = contract_edges(manifests)
    if args.json:
        print(json.dumps({"contracts": [
            {"repo": m["name"], **c} for m in manifests for c in m.get("contracts", [])],
            "edges": edges}, indent=2))
        return 0
    for m in manifests:
        for c in m.get("contracts", [])[:30]:
            print("%-12s %-8s %s" % (m["name"], c["kind"], c["path"]))
    print()
    for e in edges:
        print("edge  %s -> %s   via %s (%s)%s" %
              (e["producer"], e["consumer"], e["contract"], e["confidence"],
               "  [direction guessed]" if e.get("direction") else ""))
    if not edges:
        print("no cross-repo edges found - if >1 repo changes, find the seam manually")
    return 0


def cmd_init(args, cfg):
    """Scaffold refinery.yaml from the repos actually sitting next to this one."""
    if os.path.exists(args.config) and not args.force:
        print("%s already exists - pass --force to overwrite" % args.config)
        return 1
    root = os.path.abspath(args.root)
    found = []
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        if not os.path.isdir(path) or name.startswith(".") or name in SKIP_DIRS:
            continue
        markers = ("package.json", "pyproject.toml", "go.mod", "Cargo.toml", "pom.xml",
                   "build.gradle", "CMakeLists.txt", ".git")
        if any(os.path.exists(os.path.join(path, m)) for m in markers):
            found.append((name, os.path.relpath(path, os.getcwd()).replace(os.sep, "/")))
    example = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "assets", "refinery.example.yaml")
    if not os.path.exists(example):
        print("cannot find assets/refinery.example.yaml next to the scripts")
        return 1
    with open(example, "r", encoding="utf-8") as fh:
        text = fh.read()
    if found:
        block = "\n".join("    - name: %s\n      path: %s" % (n, p) for n, p in found)
        text = re.sub(r"  repos:.*?\n(?=  contract_globs:)",
                      "  repos:                          # [script] detected by `init`\n"
                      + block + "\n", text, flags=re.S)
    with open(args.config, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("wrote %s with %d repo(s): %s" % (args.config, len(found),
                                            ", ".join(n for n, _ in found) or "none detected"))
    print("Now set tracker.adapter, tracker.project and the agent_brief sink before use.")
    return 0


def main(argv=None):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default="refinery.yaml")
    ap = argparse.ArgumentParser(description=__doc__, parents=[common],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("manifest", parents=[common]); p.add_argument("--out"); p.add_argument("--force", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("index", parents=[common]); p.add_argument("--path")
    p = sub.add_parser("scan", parents=[common])
    p.add_argument("-q", "--query", action="append", required=True)
    p.add_argument("--budget-files", type=int); p.add_argument("--budget-seconds", type=int)
    p.add_argument("--budget-hits", type=int, default=200)
    p.add_argument("--repo", action="append", help="limit the scan to these repo names")
    p.add_argument("--limit", type=int, default=60); p.add_argument("--json", action="store_true")
    p = sub.add_parser("contracts", parents=[common]); p.add_argument("--json", action="store_true")
    p = sub.add_parser("init", parents=[common])
    p.add_argument("--root", default="..", help="directory holding the sibling repos")
    p.add_argument("--force", action="store_true")

    args = ap.parse_args(argv)
    cfg = load_config(args.config) if os.path.exists(args.config) else {}
    return {"manifest": cmd_manifest, "index": cmd_index, "scan": cmd_scan,
            "contracts": cmd_contracts, "init": cmd_init}[args.cmd](args, cfg)


if __name__ == "__main__":
    sys.exit(main())
