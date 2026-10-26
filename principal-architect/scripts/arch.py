#!/usr/bin/env python3
"""
arch.py — change-workflow CLI for the principal-architect skill.

Owns the state the workflows in references/workflows/ depend on, so the agent never
has to guess it: where the docs live, which decisions bind a change, what a change
has planned and done, and whether it is fit to archive. Pure standard library
(Python 3.8+); reuses the front-matter parser of the bundled arch_lint.py.

Commands (add --json for machine-readable output; every workflow uses it):
  context                     resolve the docs root (Step 0) and inventory it
  consult  [--base REF] [--paths P ...] [--affects C ...]
                              decisions and docs that bind the files a change touches
  new      <change-id> --title T [--level L] [--archetype A]
                              scaffold <root>/changes/<id>/ (change.md + tasks.md)
  record   adr|rfc --change ID --title T [--supersedes ADR-NNNN] [--from-rfc RFC-NNNN]
                              mint the next ADR/RFC number into decisions/, linked to the change
  status   [--change ID]      planning completeness, task progress, state, next step,
                              and where any hand-over (OpenSpec / spec-kit) stands
  list                        active changes with state and progress
  verify   [--change ID | --tree] [--strict]
                              mechanical gate: arch_lint + change checks, CRITICAL/WARNING/SUGGESTION;
                              --tree also checks every hand-over ever made, archived changes included
  log      [--write]          check (or sync) the decision log against the ADR files
  archive  [--change ID] [--yes] [--leave-proposed] [--allow-incomplete]
                              accept records, sync the log, move the change to changes/archive/
  init     [--yes] [--with-ci]
                              lay down the minimal conformant docs root
  export   openspec|speckit --change ID [--yes] [--force] [--out DIR]
                              seed an implementation change from the architecture record
  export   constitution [--yes] [--force] [--out FILE]
                              spec-kit constitution from the enterprise principles (PR.xx)

Mutating commands (archive, init) are dry runs unless --yes is given.
Exit codes: 0 ok · 1 the command ran and reports a failing state (verify with CRITICAL,
archive refused) · 2 usage or environment error (JSON body carries "error").
"""
from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
BUNDLED_LINT = os.path.join(SKILL, "assets", "ci", "tools", "arch_lint.py")
BUNDLED_CI = os.path.join(SKILL, "assets", "ci")
TEMPLATES = os.path.join(SKILL, "assets", "templates")


def _load_lint():
    spec = importlib.util.spec_from_file_location("arch_lint", BUNDLED_LINT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


LINT = _load_lint()
split_frontmatter = LINT.split_frontmatter

TODAY = datetime.date.today().isoformat()
CHANGE_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ROOT_CANDIDATES = ("docs/architecture", "docs/adr", "docs/decisions", "doc/arch",
                   "architecture", "adr")
LEVELS = ("enterprise", "solution", "software")

# Triage archetypes (SKILL.md Triage tables) and the records each one requires.
ARCHETYPES = {
    "trivial": None, "local": None, "new-component": None,
    "published-interface": "adr", "significant": "adr", "quality-target": None,
    "stakeholder": None, "feature": None, "greenfield": "adr",
    "capability": "adr", "solution": "adr", "process": None,
    "migration": "adr", "platform": "adr", "evaluation": None,
}
# Archetypes that usually alter the AD.md root (stakeholder, concern, view).
AD_ARCHETYPES = {"stakeholder", "quality-target", "significant", "greenfield"}
CHANGE_SECTIONS = ("Intent", "Evidence", "Decisions on record", "Triage",
                   "Assumptions and gaps")
JUDGEMENT_GATE = [
    "Evidence: every fact traceable to code, config, tests, history or a named person; every guess marked as an assumption or gap",
    "Numbers: every capacity, latency, availability or cost figure carries its model and assumptions, measured or derived",
    "Simplicity: the four anti-over-engineering checks (SKILL.md §2) pass; for a kept or replaced mechanism both §1 questions are answered separately and the gap recorded",
    "Triage: only the artifacts the archetype calls for, and every one it does call for",
    "Consistency: the AD.md §7 correspondence rules hold for every view, SD and diagram that corresponds to what changed",
    "Voice: prose reads as an engineer explaining a decision to a peer, forces and trade-offs on the page, no banned phrases",
]
GENERIC_TOKENS = {
    "src", "lib", "app", "apps", "main", "test", "tests", "spec", "specs", "index",
    "util", "utils", "docs", "doc", "internal", "pkg", "cmd", "core", "common",
    "py", "js", "ts", "tsx", "jsx", "go", "rs", "java", "kt", "cs", "rb", "md",
    "yaml", "yml", "json", "toml", "init", "mod", "the", "and", "for",
}
CODE_SUFFIX_SKIP = (".md", ".markdown", ".txt", ".rst")


class CliError(Exception):
    def __init__(self, code, message, **extra):
        super().__init__(message)
        self.code, self.message, self.extra = code, message, extra


# ---------------------------------------------------------------- utilities
def git(repo, *args):
    try:
        p = subprocess.run(["git", "-C", repo] + list(args), capture_output=True,
                           text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return p.stdout if p.returncode == 0 else None


def repo_root():
    out = git(os.getcwd(), "rev-parse", "--show-toplevel")
    return os.path.abspath(out.strip()) if out else os.path.abspath(os.getcwd())


def rel(path, base):
    return os.path.relpath(path, base).replace(os.sep, "/")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def slugify(title, limit=60):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:limit].rstrip("-") or "untitled"


def as_list(v):
    if v is None or v == "":
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [x.strip() for x in str(v).strip("[]").split(",") if x.strip()]


def frontmatter(path):
    try:
        return split_frontmatter(read(path))
    except (OSError, UnicodeDecodeError):
        return {}, ""


PLACEHOLDER = re.compile(r"<(?![!/\s])([^<>]{1,600})>")
HTML_TAG = re.compile(r"^(br|hr|p|b|i|u|em|strong|sub|sup|details|summary|img|a|span|"
                      r"div|kbd|code|pre|table|tr|td|th|ul|ol|li)(\s|/|$)", re.I)


def _blank(m):
    return re.sub(r"[^\n]", " ", m.group(0))


def prose(text):
    """The text with HTML comments, fenced code and inline code blanked out, line
    numbers preserved — what a reader actually sees as prose."""
    text = re.sub(r"<!--.*?(?:-->|\Z)", _blank, text, flags=re.S)
    text = re.sub(r"(?m)^[ \t]*(```|~~~).*?(?:^[ \t]*\1[^\n]*$|\Z)", _blank, text, flags=re.S)
    return re.sub(r"`[^`\n]*`", _blank, text)


def placeholders(text):
    """Unfilled `<placeholder>` tokens (they may span lines), ignoring HTML comments,
    code fences and inline code. Returns [(line_no, first line of the token)]."""
    clean, out = prose(text), []
    for m in PLACEHOLDER.finditer(clean):
        tok = m.group(1)
        if HTML_TAG.match(tok) or tok.startswith(("http://", "https://", "mailto:")):
            continue
        if not re.search(r"[A-Za-z]", tok):
            continue
        first = tok.splitlines()[0].strip()
        out.append((clean.count("\n", 0, m.start()) + 1,
                    "<" + first + (">" if "\n" not in tok else " ...>")))
    return out


def strip_comments(text):
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def sections(body):
    """Level-2 sections of a markdown body: {lower-cased heading: text}."""
    out, cur, buf = {}, None, []
    for line in body.splitlines():
        m = re.match(r"^##\s+(.*?)\s*$", line)
        if m and not line.startswith("###"):
            if cur is not None:
                out[cur] = "\n".join(buf)
            cur, buf = m.group(1).strip().lower(), []
        elif cur is not None:
            buf.append(line)
    if cur is not None:
        out[cur] = "\n".join(buf)
    return out


def _fm_bounds(lines):
    start = next((i for i, ln in enumerate(lines[:15]) if ln.strip() == "---"), None)
    if start is None:
        return None, None
    end = next((j for j in range(start + 1, len(lines)) if lines[j].strip() == "---"), None)
    return start, end


def _fm_value(value):
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(str(v) for v in value) + "]"
    return str(value)


def set_fm(path, key, value):
    """Set one front-matter key in place, keeping any trailing `# comment`."""
    lines = read(path).splitlines()
    start, end = _fm_bounds(lines)
    if start is None or end is None:
        raise CliError("no_frontmatter", f"{path} has no front-matter block")
    pat = re.compile(r"^(" + re.escape(key) + r":)([ \t]*)([^#]*?)([ \t]+#.*)?$")
    for i in range(start + 1, end):
        m = pat.match(lines[i])
        if m:
            comment = m.group(4) or ""
            pad = " " if not comment else "  "
            lines[i] = f"{key}: {_fm_value(value)}" + (pad + comment.strip() if comment else "")
            break
    else:
        lines.insert(end, f"{key}: {_fm_value(value)}")
    write(path, "\n".join(lines) + "\n")


def set_status_line(path, word):
    """Rewrite the first content line under `## Status` (Nygård body)."""
    lines = read(path).splitlines()
    for i, ln in enumerate(lines):
        if not re.match(r"^##\s+Status\s*$", ln):
            continue
        j, in_comment = i + 1, False
        while j < len(lines):
            s = lines[j].strip()
            if in_comment or s.startswith("<!--"):
                in_comment = "-->" not in s
                j += 1
                continue
            if not s:
                j += 1
                continue
            if s.startswith("#"):
                lines.insert(j, word)  # the section was empty
            else:
                lines[j] = word
            break
        else:
            lines.append(word)
        write(path, "\n".join(lines) + "\n")
        return True
    return False


def emit(result, as_json, human):
    if as_json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(human(result))


# ---------------------------------------------------------------- docs root
def _config(repo):
    for name in (".architecture.yml", ".architecture.yaml"):
        p = os.path.join(repo, name)
        if os.path.exists(p):
            cfg = {}
            for ln in read(p).splitlines():
                m = re.match(r"^\s*(root|docs_root|src)\s*:\s*['\"]?([^'\"#\s]+)", ln)
                if m:
                    cfg["src" if m.group(1) == "src" else "root"] = m.group(2)
            return name, cfg
    return None, {}


def resolve(args):
    """Step 0 of SKILL.md, deterministic. Returns a context dict."""
    repo = repo_root()
    cfg_name, cfg = _config(repo)
    if getattr(args, "root", None):
        root, how = os.path.abspath(args.root), "argument"
    elif cfg.get("root"):
        root, how = os.path.join(repo, cfg["root"]), f"config:{cfg_name}"
    else:
        root, how = None, "default"
        for cand in ROOT_CANDIDATES:
            if os.path.isdir(os.path.join(repo, cand)):
                root, how = os.path.join(repo, cand), "existing"
                break
        root = root or os.path.join(repo, "docs/architecture")
    if getattr(args, "src", None):
        src, src_how = os.path.abspath(args.src), "argument"
    elif cfg.get("src"):
        src, src_how = os.path.join(repo, cfg["src"]), f"config:{cfg_name}"
    elif os.path.isdir(os.path.join(repo, "src")):
        src, src_how = os.path.join(repo, "src"), "existing"
    else:
        src, src_how = repo, "repo-root (guessed; set src: in .architecture.yml)"
    base = os.path.basename(root.rstrip("/"))
    decisions = root if base in ("adr", "decisions") else os.path.join(root, "decisions")
    repo_lint = os.path.join(repo, "tools", "arch_lint.py")
    validator = repo_lint if os.path.exists(repo_lint) else BUNDLED_LINT
    house = next((p for p in (os.path.join(root, "house-profile.yaml"),
                              os.path.join(repo, "house-profile.yaml")) if os.path.exists(p)), None)
    return {
        "repo": repo, "root": root, "root_resolved_by": how, "root_exists": os.path.isdir(root),
        "src": src, "src_resolved_by": src_how, "decisions": decisions,
        "rfc": os.path.join(decisions, "rfc"), "changes": os.path.join(root, "changes"),
        "validator": validator, "validator_source": "repo" if validator == repo_lint else "bundled",
        "house_profile": house,
    }


def require_root(ctx):
    if not ctx["root_exists"]:
        raise CliError("no_docs_root",
                       f"no architecture docs root at {rel(ctx['root'], ctx['repo'])} "
                       f"(resolved by {ctx['root_resolved_by']}); run the bootstrap workflow "
                       f"(arch.py init) first")


def walk_md(root, include_changes=False):
    for dp, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        relp = rel(dp, root)
        if not include_changes and (relp == "changes" or relp.startswith("changes/")):
            dirs[:] = []
            continue
        for fn in sorted(files):
            if fn.endswith(".md"):
                yield os.path.join(dp, fn)


def inventory(ctx):
    root = ctx["root"]
    records, docs = [], []
    for path in walk_md(root):
        fm, _ = frontmatter(path)
        kind = LINT.doc_kind(path, fm)
        entry = {
            "kind": kind, "id": str(fm.get("id", "")) or None, "title": fm.get("title"),
            "status": str(fm.get("status", "")) or None, "path": rel(path, ctx["repo"]),
            "level": fm.get("level"), "affects": as_list(fm.get("affects")),
        }
        if kind in ("ADR", "RFC"):
            entry.update({
                "supersedes": fm.get("supersedes") or None,
                "superseded_by": fm.get("superseded-by") or None,
                "derived_from_rfc": fm.get("derived-from-rfc") or None,
                "resulting_adr": fm.get("resulting-adr") or None,
                "date": str(fm.get("date", "")) or None,
            })
            records.append(entry)
        elif kind != "INDEX" or os.path.basename(path).lower() != "readme.md":
            entry["related_adrs"] = as_list(fm.get("related-adrs"))
            entry["satisfies"] = as_list(fm.get("satisfies"))
            docs.append(entry)
    return records, docs


def next_number(ctx, prefix):
    pat = re.compile(r"^" + prefix + r"-(\d{4})\b")
    top = 0
    for dp, _, files in os.walk(ctx["root"]):
        for fn in files:
            m = pat.match(fn)
            if m:
                top = max(top, int(m.group(1)))
    return f"{prefix}-{top + 1:04d}"


def find_record(ctx, rid):
    for path in walk_md(ctx["root"]):
        if os.path.basename(path).startswith(rid + "-") or os.path.basename(path) == rid + ".md":
            return path
    return None


# ---------------------------------------------------------------- git scope
def default_base(repo):
    out = git(repo, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    if out:
        return out.strip().replace("refs/remotes/", "")
    for cand in ("main", "master", "origin/main", "origin/master"):
        if git(repo, "rev-parse", "--verify", "--quiet", cand):
            return cand
    return None


def changed_files(repo, base):
    """Repo-relative files changed since merge-base(base, HEAD), plus staged,
    unstaged and untracked. None when not in a git repository."""
    if git(repo, "rev-parse", "--git-dir") is None:
        return None, None, False
    files, added = set(), set()
    resolved = False
    if base:
        mb = git(repo, "merge-base", "HEAD", base)
        if mb:
            resolved = True
            mb = mb.strip()
            files |= set((git(repo, "diff", "--name-only", mb) or "").split())
            added |= set((git(repo, "diff", "--name-only", "--diff-filter=A", mb) or "").split())
    files |= set((git(repo, "diff", "--name-only") or "").split())
    files |= set((git(repo, "diff", "--name-only", "--cached") or "").split())
    added |= set((git(repo, "diff", "--name-only", "--cached", "--diff-filter=A") or "").split())
    untracked = set((git(repo, "ls-files", "--others", "--exclude-standard") or "").split())
    return sorted(files | untracked), sorted(added | untracked), resolved


MARKER = re.compile(r"ARCH-REF:\s*([A-Z]+-[A-Za-z0-9][\w-]*)")


def markers_in(path):
    out = []
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            for n, line in enumerate(fh, 1):
                for m in MARKER.finditer(line):
                    out.append((n, m.group(1).rstrip("-")))
    except OSError:
        pass
    return out


def path_tokens(relpath):
    parts = re.split(r"[/\\._-]+", relpath.lower())
    return {p for p in parts if len(p) >= 3 and p not in GENERIC_TOKENS and not p.isdigit()}


def term_parts(term):
    return {p for p in re.split(r"[^a-z0-9]+", term.lower()) if len(p) >= 3} | {term.lower()}


# ---------------------------------------------------------------- changes
def change_dir(ctx, cid):
    active = os.path.join(ctx["changes"], cid)
    if os.path.isdir(active):
        return active, False
    arch = os.path.join(ctx["changes"], "archive")
    if os.path.isdir(arch):
        for d in sorted(os.listdir(arch)):
            if re.match(r"^\d{4}-\d{2}-\d{2}-" + re.escape(cid) + r"$", d):
                return os.path.join(arch, d), True
    return None, False


def active_changes(ctx):
    d = ctx["changes"]
    if not os.path.isdir(d):
        return []
    return sorted(x for x in os.listdir(d)
                  if x != "archive" and os.path.isfile(os.path.join(d, x, "change.md")))


def select_change(ctx, cid):
    if cid:
        path, archived = change_dir(ctx, cid)
        if not path:
            raise CliError("change_not_found", f"no change '{cid}' under "
                           f"{rel(ctx['changes'], ctx['repo'])}", active=active_changes(ctx))
        return cid, path, archived, "argument"
    act = active_changes(ctx)
    if len(act) == 1:
        return act[0], os.path.join(ctx["changes"], act[0]), False, "only-active"
    raise CliError("change_required", "name the change with --change" if act
                   else "there are no active changes", active=act)


def parse_tasks(path):
    tasks, section = [], None
    if not os.path.exists(path):
        return tasks
    text = read(path)
    # match structure on the comment-free text, take content from the original line
    for n, (clean, line) in enumerate(zip(prose(text).splitlines(), text.splitlines()), 1):
        h = re.match(r"^##\s+(.*?)\s*$", clean)
        if h:
            section = h.group(1)
            continue
        if not re.match(r"^\s*[-*]\s+\[( |x|X)\]", clean):
            continue
        m = re.match(r"^\s*[-*]\s+\[( |x|X)\]\s+(.*\S)\s*$", line)
        if m:
            text = m.group(2)
            num = re.match(r"^(\d+(?:\.\d+)*)\s+", text)
            tasks.append({"line": n, "done": m.group(1) != " ", "text": text,
                          "number": num.group(1) if num else None, "section": section,
                          "paths": re.findall(r"`([^`\s]+(?:/[^`\s]*|\.[A-Za-z0-9]{1,6}))`", text)})
    return tasks


def change_state(ctx, cid, cdir, archived):
    """The planning/progress model of one change (the `status` contract)."""
    cpath, tpath = os.path.join(cdir, "change.md"), os.path.join(cdir, "tasks.md")
    missing = []
    fm, body = frontmatter(cpath) if os.path.exists(cpath) else ({}, "")
    if not os.path.exists(cpath):
        missing.append({"artifact": "change.md", "problem": "missing"})
    else:
        secs = sections(body)
        for name in CHANGE_SECTIONS:
            text = secs.get(name.lower())
            if text is None:
                missing.append({"artifact": "change.md", "problem": f"section '{name}' missing"})
            elif not strip_comments(text).strip() or placeholders(text):
                missing.append({"artifact": "change.md", "problem": f"section '{name}' not filled"})
        arche = str(fm.get("archetype", "")).strip()
        if arche not in ARCHETYPES:
            missing.append({"artifact": "change.md",
                            "problem": f"archetype '{arche}' is not one of {sorted(ARCHETYPES)}"})
        if str(fm.get("level", "")) not in LEVELS:
            missing.append({"artifact": "change.md", "problem": "level must be enterprise|solution|software"})
        if not as_list(fm.get("affects")):
            missing.append({"artifact": "change.md",
                            "problem": "affects is empty (components/areas this change touches)"})
        clines = read(cpath).splitlines()
        start, end = _fm_bounds(clines)
        if start is not None and end is not None:
            for ln, tok in placeholders("\n".join(clines[:end + 1])):
                missing.append({"artifact": "change.md", "problem": f"unfilled {tok} on line {ln}"})
    records = []
    for rid in as_list(fm.get("records")):
        path = find_record(ctx, rid)
        rec = {"id": rid, "path": rel(path, ctx["repo"]) if path else None}
        if not path:
            missing.append({"artifact": rid, "problem": "listed in records but no file found"})
        else:
            rfm, _ = frontmatter(path)
            rec.update({"status": str(rfm.get("status", "")), "supersedes": rfm.get("supersedes") or None,
                        "kind": "ADR" if rid.startswith("ADR-") else "RFC"})
            ph = placeholders(read(path))
            rec["unfilled"] = len(ph)
            if ph:
                missing.append({"artifact": rid, "problem": f"{len(ph)} unfilled placeholder(s), "
                                f"first {ph[0][1]} on line {ph[0][0]}"})
        records.append(rec)
    arche = str(fm.get("archetype", "")).strip()
    if ARCHETYPES.get(arche) == "adr" and not any(r["id"].startswith(("ADR-", "RFC-")) for r in records):
        missing.append({"artifact": "records", "problem": f"archetype '{arche}' requires a decision "
                        f"record; run: arch.py record adr --change {cid} --title ..."})
    superseded_here = {str(r.get("supersedes")) for r in records if r.get("supersedes")}
    for adr in as_list(fm.get("conflicts")):
        if adr not in superseded_here:
            missing.append({"artifact": "conflicts", "problem": f"conflict with {adr} is unresolved: "
                            f"supersede it with a record in this change, or change the plan and "
                            f"remove it from conflicts"})
    tasks = parse_tasks(tpath)
    if not os.path.exists(tpath):
        missing.append({"artifact": "tasks.md", "problem": "missing"})
    elif not tasks:
        missing.append({"artifact": "tasks.md", "problem": "no tasks ('- [ ] N.M ...')"})
    done = sum(t["done"] for t in tasks)
    if archived:
        state = "archived"
    elif arche == "trivial":
        state = "not_needed"
    elif missing:
        state = "blocked"
    elif done == 0:
        state = "ready"
    elif done < len(tasks):
        state = "in_progress"
    else:
        state = "all_done"
    nxt = {
        "archived": "Nothing to do; this change is archived.",
        "not_needed": "Trivial changes need no change folder (SKILL.md Triage). Delete it and just make the change.",
        "blocked": "Planning is incomplete. Fix every item in 'missing', then re-run status.",
        "ready": "Planning is complete. Present it for review; on a new request run the apply workflow.",
        "in_progress": "Continue with the first task whose done is false.",
        "all_done": "All tasks are done. Run the verify workflow, then archive.",
    }[state]
    return {
        "change": cid, "path": rel(cdir, ctx["repo"]), "archived": archived, "state": state,
        "title": fm.get("title"), "level": fm.get("level"), "archetype": arche or None,
        "affects": as_list(fm.get("affects")), "base": fm.get("base") or None,
        "conflicts": as_list(fm.get("conflicts")), "records": records, "missing": missing,
        "progress": {"total": len(tasks), "done": done, "remaining": len(tasks) - done},
        "tasks": [dict(t, source=rel(tpath, ctx["repo"])) for t in tasks], "next": nxt,
        "handoff": as_list(fm.get("handoff")),
    }


# ---------------------------------------------------------------- hand-over state
# A decision is accepted when it is made (MADR, TOGAF implementation governance); delivery
# is tracked in the implementation tool. The link between the two is kept visible in both
# directions and is never a lock: nothing here refuses, it only reports.
HANDOFF = re.compile(r"^([a-z]+):(.+?)(?:@([0-9a-f]{6,64}))?$")


def current_fingerprint(ctx, state):
    import arch_export
    return arch_export.fingerprint(arch_export.Source(sys.modules[__name__], ctx, state).build())


def handoff_state(ctx, state):
    """Where each hand-over of a change lives now, how far it is, and whether the seed
    still matches the architecture record it was derived from."""
    entries = state.get("handoff") or []
    if not entries:
        return []
    fp_now = current_fingerprint(ctx, state)
    out = []
    for raw in entries:
        m = HANDOFF.match(raw)
        if not m:
            out.append({"raw": raw, "target": None, "path": None, "state": "unparseable",
                        "exists": False, "archived": False, "progress": None, "seed_current": None})
            continue
        target, path, fp = m.groups()
        full = os.path.join(ctx["repo"], path)
        found, archived = (full if os.path.isdir(full) else None), False
        if found is None and target == "openspec":
            # openspec archive moves the change to changes/archive/<date>-<id>/
            arch_dir = os.path.join(os.path.dirname(full), "archive")
            name = os.path.basename(full)
            if os.path.isdir(arch_dir):
                for d in sorted(os.listdir(arch_dir)):
                    if d.endswith("-" + name) and os.path.isdir(os.path.join(arch_dir, d)):
                        found, archived = os.path.join(arch_dir, d), True
        entry = {"raw": raw, "target": target, "path": rel(found, ctx["repo"]) if found else path,
                 "exists": found is not None, "archived": archived, "fingerprint": fp,
                 "seed_current": None if fp is None else fp == fp_now, "progress": None}
        if found is None:
            entry["state"] = "missing"
        else:
            tasks = parse_tasks(os.path.join(found, "tasks.md"))
            done = sum(t["done"] for t in tasks)
            entry["progress"] = {"total": len(tasks), "done": done}
            entry["state"] = ("archived" if archived else "seeded" if not tasks else
                              "not_started" if done == 0 else "in_progress" if done < len(tasks) else "done")
        out.append(entry)
    return out


def all_changes(ctx):
    """(id, dir, archived) for every change, active first, then the archive."""
    out = [(cid, os.path.join(ctx["changes"], cid), False) for cid in active_changes(ctx)]
    arch_dir = os.path.join(ctx["changes"], "archive")
    if os.path.isdir(arch_dir):
        for d in sorted(os.listdir(arch_dir)):
            m = re.match(r"^\d{4}-\d{2}-\d{2}-(.+)$", d)
            if m and os.path.isfile(os.path.join(arch_dir, d, "change.md")):
                out.append((m.group(1), os.path.join(arch_dir, d), True))
    return out


def _handoff_checks(ctx, state, check, issue, label="handoff"):
    """The Implementation checks of verify for one change; returns its hand-over entries."""
    hand = handoff_state(ctx, state)
    if not hand:
        check(label, "Implementation", "passed", "no hand-over recorded")
        return hand
    bad = 0
    for h in hand:
        if h["state"] == "unparseable":
            bad += 1
            issue("WARNING", "Implementation", f"{state['change']}: handoff entry '{h['raw']}' is not target:path",
                  state["path"])
        elif h["state"] == "missing":
            bad += 1
            issue("WARNING", "Implementation", f"{state['change']}: hand-over target {h['path']} ({h['target']}) "
                  f"no longer exists; re-export it or remove it from handoff:", state["path"])
        elif h["seed_current"] is False:
            bad += 1
            issue("WARNING", "Implementation", f"{state['change']}: the architecture record changed after the "
                  f"{h['target']} seed at {h['path']} was written; re-export with --force, or carry the change "
                  f"into the seed and re-export to refresh the fingerprint", h["path"])
        elif h["seed_current"] is None:
            issue("SUGGESTION", "Implementation", f"{state['change']}: {h['target']} seed at {h['path']} carries "
                  f"no fingerprint (older export); re-export so drift becomes detectable", h["path"])
        h["change"] = state["change"]
    check(label, "Implementation", "failed" if bad else "passed", "; ".join(_handoff_line(h) for h in hand))
    return hand


def _handoff_line(h):
    prog = f" {h['progress']['done']}/{h['progress']['total']} tasks" if h.get("progress") else ""
    seed = "" if h.get("seed_current") in (True, None) else " — record changed since the seed"
    return f"{h['target'] or '?'} {h['state']}{prog} at {h['path'] or h['raw']}{seed}"


# ---------------------------------------------------------------- commands
def cmd_context(args):
    ctx = resolve(args)
    def shown(k, v):
        if k == "repo" or not (isinstance(v, str) and os.path.isabs(v)):
            return v
        r = rel(v, ctx["repo"])
        return v if r.startswith("../") else r
    out = {k: shown(k, v) for k, v in ctx.items()}
    out["state"] = "ok" if ctx["root_exists"] else "no_docs_root"
    if ctx["root_exists"]:
        records, docs = inventory(ctx)
        out["records"] = records
        out["documents"] = docs
        out["has"] = {k: os.path.exists(os.path.join(ctx["root"], f)) for k, f in
                      (("index", "README.md"), ("ad", "AD.md"),
                       ("checklist", "conformance-checklist.md"),
                       ("decision_log", os.path.join(rel(ctx["decisions"], ctx["root"]), "README.md")))}
        out["changes"] = active_changes(ctx)
        out["next_ids"] = {"ADR": next_number(ctx, "ADR"), "RFC": next_number(ctx, "RFC")}
    out["base"] = default_base(ctx["repo"])

    def human(r):
        lines = [f"docs root: {r['root']} ({r['root_resolved_by']}){'' if r['root_exists'] else '  — DOES NOT EXIST'}",
                 f"src:       {r['src']} ({r['src_resolved_by']})",
                 f"validator: {r['validator']} ({r['validator_source']})"]
        if r["root_exists"]:
            lines.append(f"records:   {len(r['records'])}   documents: {len(r['documents'])}   "
                         f"active changes: {', '.join(r['changes']) or 'none'}")
            lines.append(f"next ids:  {r['next_ids']['ADR']}, {r['next_ids']['RFC']}")
        return "\n".join(lines)
    emit(out, args.json, human)


def cmd_consult(args):
    ctx = resolve(args)
    require_root(ctx)
    repo = ctx["repo"]
    base = args.base or default_base(repo)
    if args.paths:
        touched, base_resolved = sorted({rel(os.path.abspath(p), repo) for p in args.paths}), None
    else:
        touched, _, base_resolved = changed_files(repo, base)
        touched = touched or []
    root_rel = rel(ctx["root"], repo)
    code = [p for p in touched if not (p + "/").startswith(root_rel + "/")]
    records, docs = inventory(ctx)
    by_id = {r["id"]: r for r in records if r["id"]}
    markers, warnings = [], []
    tokens = set()
    for p in code:
        tokens |= path_tokens(p)
        for ln, mid in markers_in(os.path.join(repo, p)):
            markers.append({"path": p, "line": ln, "id": mid})
    for a in args.affects or []:
        tokens |= term_parts(a)
    hits = {}

    def hit(entry, how):
        key = entry["path"]
        h = hits.setdefault(key, dict(entry, match=[]))
        if how not in h["match"]:
            h["match"].append(how)

    for m in markers:
        r = by_id.get(m["id"])
        if r:
            hit(r, f"marker {m['path']}:{m['line']}")
            if r["status"] in ("superseded", "deprecated"):
                warnings.append(f"{m['path']}:{m['line']} references {r['status']} {m['id']}"
                                + (f" (superseded by {r['superseded_by']})" if r.get("superseded_by") else ""))
        elif m["id"].startswith(("ADR-", "RFC-")):
            warnings.append(f"{m['path']}:{m['line']} references {m['id']}, which has no record")
        else:
            d = next((d for d in docs if d["id"] == m["id"]), None)
            if d:
                hit(d, f"marker {m['path']}:{m['line']}")
    for r in records:
        if tokens and any(term_parts(a) & tokens for a in r["affects"]):
            hit(r, "affects")
    matched_adrs = {h["id"] for h in hits.values() if h.get("kind") == "ADR"}
    for d in docs:
        idp = term_parts(d["id"] or "") - {"sd", "hld", "prd", "sad"}
        if tokens and (idp & tokens or any(term_parts(a) & tokens for a in d["affects"])):
            hit(d, "name/affects")
        if set(d.get("related_adrs") or []) & matched_adrs:
            hit(d, "related-adrs")
    decisions = sorted((h for h in hits.values() if h.get("kind") in ("ADR", "RFC")),
                       key=lambda h: h["id"] or "")
    for d in decisions:
        d["binding"] = d["kind"] == "ADR" and d["status"] == "accepted"
        d["strength"] = "strong" if any(x.startswith("marker") for x in d["match"]) else "candidate"
    documents = sorted((h for h in hits.values() if h.get("kind") not in ("ADR", "RFC")),
                       key=lambda h: h["path"])
    overlapping = []
    for cid in active_changes(ctx):
        cfm, _ = frontmatter(os.path.join(ctx["changes"], cid, "change.md"))
        if tokens and any(term_parts(a) & tokens for a in as_list(cfm.get("affects"))):
            overlapping.append(cid)
    reads = [p for p in (os.path.join(root_rel, "README.md"), os.path.join(root_rel, "AD.md"))
             if os.path.exists(os.path.join(repo, p))]
    reads += [d["path"] for d in documents] + [d["path"] for d in decisions if d["binding"]]
    out = {
        "base": base, "base_resolved": base_resolved, "touched": touched, "code": code,
        "tokens": sorted(tokens), "markers": markers, "decisions": decisions, "documents": documents,
        "binding": [d["id"] for d in decisions if d["binding"]], "warnings": warnings,
        "overlapping_changes": overlapping, "suggested_reads": list(dict.fromkeys(reads)),
        "note": "Matches by 'affects' and name are candidates found by token overlap; read them and "
                "decide. Matches by marker are the code saying so itself.",
    }

    def human(r):
        lines = [f"touched: {len(r['touched'])} file(s), {len(r['code'])} outside the docs root"]
        for d in r["decisions"]:
            lines.append(f"  {'BINDING ' if d['binding'] else '        '}{d['id']} [{d['status']}] "
                         f"{d['title']}  ({', '.join(d['match'])})")
        for d in r["documents"]:
            lines.append(f"  doc {d['path']}  ({', '.join(d['match'])})")
        for w in r["warnings"]:
            lines.append(f"  WARNING {w}")
        if r["overlapping_changes"]:
            lines.append(f"  overlapping active changes: {', '.join(r['overlapping_changes'])}")
        return "\n".join(lines)
    emit(out, args.json, human)


def _fill(text, values):
    for k, v in values.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text


def cmd_new(args):
    ctx = resolve(args)
    require_root(ctx)
    cid = args.change_id
    if not CHANGE_ID.match(cid):
        raise CliError("invalid_change_id", f"'{cid}' is not kebab-case (e.g. add-key-rotation)")
    if args.archetype and args.archetype not in ARCHETYPES:
        raise CliError("invalid_archetype", f"archetype must be one of {sorted(ARCHETYPES)}")
    if args.archetype == "trivial":
        raise CliError("not_needed", "trivial changes need no change folder (SKILL.md Triage); "
                       "make the change, fix any line that is now wrong, and stop")
    if args.level not in LEVELS:
        raise CliError("invalid_level", "level must be enterprise|solution|software")
    existing, archived = change_dir(ctx, cid)
    if existing:
        raise CliError("change_exists", f"change '{cid}' already exists"
                       + (" (archived)" if archived else "") + f" at {rel(existing, ctx['repo'])}")
    cdir = os.path.join(ctx["changes"], cid)
    values = {"id": cid, "title": args.title, "date": TODAY, "level": args.level,
              "archetype": args.archetype or "<archetype>",
              "base": default_base(ctx["repo"]) or "none"}
    for name in ("change.md", "tasks.md"):
        write(os.path.join(cdir, name), _fill(read(os.path.join(TEMPLATES, "change", name)), values))
    out = {"change": cid, "path": rel(cdir, ctx["repo"]),
           "created": [rel(os.path.join(cdir, n), ctx["repo"]) for n in ("change.md", "tasks.md")],
           "next": f"Fill change.md, add records with 'arch.py record', write tasks, then "
                   f"'arch.py status --change {cid}'."}
    emit(out, args.json, lambda r: f"created {r['path']}/ (change.md, tasks.md)\n{r['next']}")


def cmd_record(args):
    ctx = resolve(args)
    require_root(ctx)
    cid, cdir, archived, _ = select_change(ctx, args.change)
    if archived:
        raise CliError("change_archived", f"change '{cid}' is archived; open a new change")
    cpath = os.path.join(cdir, "change.md")
    cfm, _ = frontmatter(cpath)
    kind = args.kind.upper()
    level = args.level or str(cfm.get("level", "software"))
    if level not in LEVELS:
        raise CliError("invalid_level", "level must be enterprise|solution|software")
    rid = next_number(ctx, kind)
    target_dir = ctx["decisions"] if kind == "ADR" else ctx["rfc"]
    path = os.path.join(target_dir, f"{rid}-{slugify(args.title)}.md")
    text = read(os.path.join(TEMPLATES, f"{kind}.md"))
    text = text.replace(f"{kind}-NNNN", rid).replace(f"# {rid}: <title>", f"# {rid}: {args.title}")
    write(path, text)
    set_fm(path, "id", rid)
    set_fm(path, "title", args.title)
    set_fm(path, "level", level)
    set_fm(path, "date", TODAY)
    set_fm(path, "status", "proposed" if kind == "ADR" else "draft")
    affects = as_list(cfm.get("affects"))
    if affects:
        set_fm(path, "affects", affects)
    if kind == "ADR":
        set_status_line(path, "Proposed")
    notes = []
    if args.supersedes:
        old = find_record(ctx, args.supersedes)
        if not old or not args.supersedes.startswith("ADR-"):
            os.remove(path)
            raise CliError("supersedes_not_found", f"no ADR file for {args.supersedes}")
        ofm, _ = frontmatter(old)
        if str(ofm.get("status")) == "superseded":
            os.remove(path)
            raise CliError("already_superseded", f"{args.supersedes} is already superseded by "
                           f"{ofm.get('superseded-by')}")
        set_fm(path, "supersedes", args.supersedes)
        notes.append(f"{args.supersedes} will be marked superseded-by {rid} when the change is archived")
    if args.from_rfc:
        rfc = find_record(ctx, args.from_rfc)
        if not rfc:
            os.remove(path)
            raise CliError("rfc_not_found", f"no RFC file for {args.from_rfc}")
        set_fm(path, "derived-from-rfc", args.from_rfc)
        set_fm(rfc, "resulting-adr", rid)
        notes.append(f"{args.from_rfc} now points to {rid} (resulting-adr)")
    recs = as_list(cfm.get("records"))
    set_fm(cpath, "records", recs + [rid])
    out = {"id": rid, "path": rel(path, ctx["repo"]), "change": cid, "notes": notes,
           "next": "Fill every <placeholder> in the record; status reports it as missing until you do."}
    emit(out, args.json, lambda r: f"created {r['id']} at {r['path']}\n" + "\n".join(r["notes"]))


def cmd_status(args):
    ctx = resolve(args)
    require_root(ctx)
    cid, cdir, archived, how = select_change(ctx, args.change)
    out = change_state(ctx, cid, cdir, archived)
    out["selected_by"] = how
    out["implementation"] = handoff_state(ctx, out)

    def human(r):
        lines = [f"change: {r['change']} — {r['title']}  [{r['state']}]",
                 f"progress: {r['progress']['done']}/{r['progress']['total']} tasks"]
        for h in r["implementation"]:
            lines.append(f"implementation: {_handoff_line(h)}")
        for m in r["missing"]:
            lines.append(f"  missing: {m['artifact']}: {m['problem']}")
        for t in r["tasks"]:
            lines.append(f"  [{'x' if t['done'] else ' '}] {t['text']}  ({t['source']}:{t['line']})")
        lines.append(r["next"])
        return "\n".join(lines)
    emit(out, args.json, human)


def cmd_list(args):
    ctx = resolve(args)
    require_root(ctx)
    rows = []
    for cid in active_changes(ctx):
        s = change_state(ctx, cid, os.path.join(ctx["changes"], cid), False)
        row = {k: s[k] for k in ("change", "title", "state", "archetype", "progress", "path")}
        row["implementation"] = [f"{h['target']}:{h['state']}" for h in handoff_state(ctx, s)]
        rows.append(row)
    emit({"changes": rows}, args.json,
         lambda r: "\n".join(f"{c['change']:<32} {c['state']:<12} {c['progress']['done']}/"
                             f"{c['progress']['total']}  {c['title']}"
                             + (f"  [{', '.join(c['implementation'])}]" if c["implementation"] else "")
                             for c in r["changes"])
         or "no active changes")


# ---------------------------------------------------------------- decision log
def _log_path(ctx):
    return os.path.join(ctx["decisions"], "README.md")


def _split_row(line):
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def _decision_summary(path):
    _, body = frontmatter(path)
    text = strip_comments(sections(body).get("decision", "")).strip()
    first = re.split(r"(?<=[.!?])\s", " ".join(text.split()), maxsplit=1)[0] if text else ""
    first = first.replace("|", "/")
    return (first[:137] + "...") if len(first) > 140 else first


def log_model(ctx):
    path = _log_path(ctx)
    records, _ = inventory(ctx)
    adrs = {r["id"]: r for r in records if r["kind"] == "ADR" and r["id"]}
    model = {"path": rel(path, ctx["repo"]), "exists": os.path.exists(path), "issues": [],
             "header": None, "rows": {}, "adrs": adrs}
    if not model["exists"]:
        model["issues"].append({"severity": "WARNING", "message": "decision log missing", "id": None})
        return model
    lines = read(path).splitlines()
    for i, ln in enumerate(lines):
        if ln.strip().startswith("|"):
            cells = [c.lower() for c in _split_row(ln)]
            if "id" in cells and "status" in cells and model["header"] is None:
                model["header"] = (i, cells)
                continue
            if model["header"] and re.match(r"^\|?\s*:?-{3,}", ln.strip()):
                continue
            if model["header"]:
                m = re.search(r"ADR-\d{4}", ln)
                if m:
                    model["rows"][m.group(0)] = (i, _split_row(ln))
    if model["header"] is None:
        model["issues"].append({"severity": "WARNING", "message": "no table with ID and Status columns",
                                "id": None})
        return model
    cols = model["header"][1]
    for rid, (i, cells) in model["rows"].items():
        if rid not in adrs:
            model["issues"].append({"severity": "WARNING", "id": rid,
                                    "message": f"log row {rid} has no ADR file"})
            continue
        if placeholders(lines[i]):
            model["issues"].append({"severity": "WARNING", "id": rid,
                                    "message": f"log row {rid} still holds template placeholders"})
        st = cells[cols.index("status")] if cols.index("status") < len(cells) else ""
        if st.lower() != (adrs[rid]["status"] or "").lower():
            model["issues"].append({"severity": "WARNING", "id": rid,
                                    "message": f"log says {rid} is '{st}', the file says "
                                               f"'{adrs[rid]['status']}'"})
    for rid in sorted(adrs):
        if rid not in model["rows"]:
            model["issues"].append({"severity": "WARNING", "id": rid,
                                    "message": f"{rid} has no row in the decision log"})
    return model


def _row_for(ctx, cols, rec):
    path = os.path.join(ctx["repo"], rec["path"])
    link = "./" + rel(path, ctx["decisions"])
    cells = []
    for c in cols:
        if c == "id":
            cells.append(f"[{rec['id']}]({link})")
        elif c == "title":
            cells.append(str(rec["title"] or "").replace("|", "/"))
        elif c == "status":
            cells.append(rec["status"] or "")
        elif c == "date":
            cells.append(rec.get("date") or "")
        elif c in ("summary", "description", "decision"):
            cells.append(_decision_summary(path))
        else:
            cells.append("")
    return "| " + " | ".join(cells) + " |"


def log_write(ctx):
    path = _log_path(ctx)
    model = log_model(ctx)
    if not model["exists"]:
        tpl = re.sub(r"^<!--.*?-->\s*", "", read(os.path.join(TEMPLATES, "decision-log.md")), flags=re.S)
        tpl = "\n".join(ln for ln in tpl.splitlines() if not re.search(r"ADR-0001\]\(\./ADR-0001-<slug>", ln))
        write(path, tpl.rstrip() + "\n")
        model = log_model(ctx)
    if model["header"] is None:
        raise CliError("log_unparseable", f"{model['path']} has no table with ID and Status columns; "
                       f"fix it by hand")
    lines = read(path).splitlines()
    cols = model["header"][1]
    changed = []
    for rid, (i, cells) in model["rows"].items():
        rec = model["adrs"].get(rid)
        if not rec:
            continue
        if placeholders(lines[i]):
            lines[i] = _row_for(ctx, cols, rec)
            changed.append(f"rewrote {rid}")
            continue
        new = list(cells) + [""] * (len(cols) - len(cells))
        si = cols.index("status")
        if new[si].lower() != (rec["status"] or "").lower():
            new[si] = rec["status"] or ""
            if "date" in cols:
                new[cols.index("date")] = rec.get("date") or ""
            lines[i] = "| " + " | ".join(new[:len(cols)]) + " |"
            changed.append(f"updated {rid}")
    missing = [rid for rid in sorted(model["adrs"]) if rid not in model["rows"]]
    if missing:
        last = max([i for i, _ in model["rows"].values()] + [model["header"][0] + 1])
        new_rows = [_row_for(ctx, cols, model["adrs"][rid]) for rid in missing]
        lines[last + 1:last + 1] = new_rows
        changed += [f"added {rid}" for rid in missing]
    write(path, "\n".join(lines) + "\n")
    return changed


def cmd_log(args):
    ctx = resolve(args)
    require_root(ctx)
    if args.write:
        changed = log_write(ctx)
        out = {"path": rel(_log_path(ctx), ctx["repo"]), "changed": changed}
        emit(out, args.json, lambda r: "\n".join(r["changed"]) or "decision log already in sync")
        return
    model = log_model(ctx)
    out = {"path": model["path"], "exists": model["exists"], "issues": model["issues"],
           "in_sync": not model["issues"]}
    emit(out, args.json, lambda r: "\n".join(i["message"] for i in r["issues"]) or "decision log in sync")
    if model["issues"]:
        sys.exit(1)


# ---------------------------------------------------------------- verify
LINT_LINE = re.compile(r"^::(error|warning)::\s+(.*?):\s+(.*)$")


def run_lint(ctx, strict):
    cmd = [sys.executable, ctx["validator"], "all", "--root", ctx["root"], "--src", ctx["src"]]
    if strict:
        cmd.append("--strict")
    if ctx["house_profile"]:
        cmd += ["--house", ctx["house_profile"]]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=ctx["repo"], timeout=300)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, str(e), []
    if p.returncode not in (0, 1):
        return None, (p.stderr or p.stdout).strip()[-500:], []
    found = []
    for ln in p.stdout.splitlines():
        m = LINT_LINE.match(ln)
        if m:
            found.append((m.group(1), m.group(2), m.group(3)))
    return p.returncode, None, found


def verify(ctx, cid=None, strict=False):
    checks, issues = [], []

    def check(name, dim, status, reason=""):
        checks.append({"name": name, "dimension": dim, "status": status, "reason": reason})

    def issue(sev, dim, msg, path=None, line=None):
        issues.append({"severity": sev, "dimension": dim, "message": msg, "path": path, "line": line})

    state = None
    if cid:
        cdir, archived = change_dir(ctx, cid)
        if not cdir:
            raise CliError("change_not_found", f"no change '{cid}'", active=active_changes(ctx))
        state = change_state(ctx, cid, cdir, archived)
    base = (state or {}).get("base") or default_base(ctx["repo"])
    if base in ("none",) or (base and base.startswith("<")):
        base = default_base(ctx["repo"])
    changed, added, base_ok = changed_files(ctx["repo"], base)
    in_git = changed is not None
    scope = set(changed or [])
    root_rel = rel(ctx["root"], ctx["repo"])

    # 1. mechanical lint (Conformance)
    rc, err, found = run_lint(ctx, strict)
    if rc is None:
        check("arch_lint", "Conformance", "skipped", f"validator did not run: {err}")
    else:
        n_err = 0
        for level, path, msg in found:
            relp = path.replace(os.sep, "/")  # arch_lint prints paths relative to the repo
            pre = bool(in_git and cid and relp not in scope)
            sev = "CRITICAL" if level == "error" and not pre else "WARNING"
            n_err += sev == "CRITICAL"
            issue(sev, "Conformance", ("pre-existing (not touched by this change): " if pre else "") + msg, relp)
        check("arch_lint", "Conformance", "failed" if n_err else "passed",
              f"{ctx['validator_source']} validator, exit {rc}, {len(found)} finding(s)")

    # 2. decision log
    model = log_model(ctx)
    mine = {r["id"] for r in (state or {}).get("records", [])}
    others = [i for i in model["issues"] if i["id"] not in mine]
    for i in others:
        issue("WARNING", "Conformance", i["message"], model["path"])
    check("decision_log", "Conformance", "failed" if others else "passed",
          ("this change's records are synced on archive" if mine else ""))

    if state:
        # 3. completeness
        for m in state["missing"]:
            issue("CRITICAL", "Completeness", f"{m['artifact']}: {m['problem']}", state["path"])
        open_tasks = [t for t in state["tasks"] if not t["done"]]
        for t in open_tasks:
            issue("CRITICAL", "Completeness", f"task not done: {t['text']}", t["source"], t["line"])
        check("planning", "Completeness", "failed" if state["missing"] else "passed")
        check("tasks", "Completeness", "failed" if open_tasks else "passed",
              f"{state['progress']['done']}/{state['progress']['total']} done")

        # 4. task coverage against the diff
        if not in_git:
            check("task_coverage", "Completeness", "skipped", "not a git repository")
        else:
            unmet = 0
            for t in state["tasks"]:
                if not t["done"]:
                    continue
                for p in t["paths"]:
                    cands = {p.lstrip("./"), f"{root_rel}/{p.lstrip('./')}"}
                    exists = any(os.path.exists(os.path.join(ctx["repo"], c)) for c in cands)
                    if exists and not (cands & scope):
                        unmet += 1
                        issue("WARNING", "Completeness", f"task marked done but `{p}` is unchanged "
                              f"since {base if base_ok else 'the working tree'}: {t['text']}",
                              t["source"], t["line"])
            check("task_coverage", "Completeness", "failed" if unmet else "passed",
                  "" if base_ok else f"base '{base}' not resolved; compared against working tree only")

        # 5. breadcrumbs: code touched by the change references the change's ADRs
        if not in_git:
            check("breadcrumbs", "Traceability", "skipped", "not a git repository")
        else:
            code = [p for p in scope if not (p + "/").startswith(root_rel + "/")
                    and not p.endswith(CODE_SUFFIX_SKIP) and os.path.isfile(os.path.join(ctx["repo"], p))]
            refs = {mid for p in code for _, mid in markers_in(os.path.join(ctx["repo"], p))}
            adrs = [r["id"] for r in state["records"] if r["id"].startswith("ADR-")]
            if not code or not adrs:
                check("breadcrumbs", "Traceability", "passed",
                      "no code touched" if not code else "no ADR in this change")
            else:
                gaps = [a for a in adrs if a not in refs]
                for a in gaps:
                    issue("WARNING", "Traceability", f"{a} is not referenced by an ARCH-REF marker in "
                          f"the {len(code)} code file(s) this change touches")
                check("breadcrumbs", "Traceability", "failed" if gaps else "passed")

        # 6. index: docs this change added are reachable from the root README
        idx = os.path.join(ctx["root"], "README.md")
        if not in_git:
            check("index", "Traceability", "skipped", "not a git repository")
        elif not os.path.exists(idx):
            issue("WARNING", "Traceability", "no index README.md at the docs root", root_rel)
            check("index", "Traceability", "failed")
        else:
            itext = read(idx)
            new_docs = []
            for p in added or []:
                inner, name = p[len(root_rel) + 1:], os.path.basename(p)
                if (p.startswith(root_rel + "/") and p.endswith(".md") and not inner.startswith("changes/")
                        and not name.startswith(("ADR-", "RFC-")) and name.lower() != "readme.md"):
                    new_docs.append((p, inner, name))
            unlisted = [p for p, inner, name in new_docs if inner not in itext and name not in itext]
            for p in unlisted:
                issue("WARNING", "Traceability", f"new document {p} is not linked from the index",
                      rel(idx, ctx["repo"]))
            check("index", "Traceability", "failed" if unlisted else "passed")

        # 7. review flags on HLD/SAD this change touched
        flagged = 0
        for p in scope:
            if p.startswith(root_rel + "/") and p.endswith(".md") and os.path.exists(os.path.join(ctx["repo"], p)):
                fm, _ = frontmatter(os.path.join(ctx["repo"], p))
                if LINT.doc_kind(os.path.join(ctx["repo"], p), fm) in ("HLD", "SAD"):
                    for flag in ("security-reviewed", "cost-reviewed"):
                        if fm.get(flag) is not True:
                            flagged += 1
                            issue("WARNING", "Coherence", f"{flag} is not true; the threat model and "
                                  f"FinOps estimate need sign-off after this change", p)
        check("review_flags", "Coherence", "failed" if flagged else "passed")

        # 8. AD root for archetypes that usually alter it
        if state["archetype"] in AD_ARCHETYPES:
            ad = f"{root_rel}/AD.md"
            if in_git and ad not in scope:
                issue("SUGGESTION", "Coherence", f"archetype '{state['archetype']}' usually adds a "
                      f"stakeholder, concern or view; confirm AD.md needs no change", ad)

        # 9. hand-over: the implementation seed must still match the record (visibility, not a lock)
        hand = _handoff_checks(ctx, state, check, issue)
    else:
        # whole-tree: every change that was ever handed over, archived ones included — that is
        # where a seed quietly falls behind the record once nobody runs status on it any more
        hand = []
        for cid_, cdir_, archived_ in all_changes(ctx):
            st_ = change_state(ctx, cid_, cdir_, archived_)
            if st_["handoff"]:
                hand += _handoff_checks(ctx, st_, check, issue, label=f"handoff:{cid_}")
        if not hand:
            check("handoff", "Implementation", "passed", "no change has been handed over")

    crit = sum(i["severity"] == "CRITICAL" for i in issues)
    skipped = [c for c in checks if c["status"] == "skipped"]
    if crit:
        verdict = "fix_critical"
    elif skipped:
        verdict = "not_fully_verified"
    else:
        verdict = "mechanically_clean"
    return {
        "change": cid, "base": base, "base_resolved": base_ok, "verdict": verdict,
        "summary": {s: sum(i["severity"] == s for i in issues) for s in ("CRITICAL", "WARNING", "SUGGESTION")},
        "checks": checks, "issues": issues, "judgement_gate": JUDGEMENT_GATE, "implementation": hand,
        "note": "mechanically_clean is not ready: the judgement gate is yours to walk, and a "
                "skipped check is never a pass.",
    }


def cmd_verify(args):
    ctx = resolve(args)
    require_root(ctx)
    cid = args.change
    if not cid and not args.tree:
        act = active_changes(ctx)
        cid = act[0] if len(act) == 1 else None
        if len(act) > 1:
            raise CliError("change_required", "name the change with --change, or pass --tree "
                           "for a whole-tree health check", active=act)
    out = verify(ctx, cid, args.strict)

    def human(r):
        lines = [f"verdict: {r['verdict']}  ({r['summary']['CRITICAL']} critical, "
                 f"{r['summary']['WARNING']} warning, {r['summary']['SUGGESTION']} suggestion)"]
        for c in r["checks"]:
            lines.append(f"  {c['status']:<8} {c['dimension']:<13} {c['name']}  {c['reason']}")
        for i in r["issues"]:
            loc = f"{i['path']}:{i['line']}" if i["line"] else (i["path"] or "")
            lines.append(f"  {i['severity']:<10} {i['message']}  {loc}")
        return "\n".join(lines)
    emit(out, args.json, human)
    if out["verdict"] == "fix_critical":
        sys.exit(1)


# ---------------------------------------------------------------- archive
LINK = re.compile(r"(\]\()(\.{1,2}/[^)\s#]+)")


def _move_with_links(src_dir, dst_dir):
    """Move a change folder and re-point its relative links that leave the folder."""
    os.makedirs(os.path.dirname(dst_dir), exist_ok=True)
    shutil.move(src_dir, dst_dir)
    for dp, _, files in os.walk(dst_dir):
        old_dp = os.path.normpath(os.path.join(src_dir, os.path.relpath(dp, dst_dir)))

        def fix(m):
            target = os.path.normpath(os.path.join(old_dp, m.group(2)))
            if target == src_dir or target.startswith(src_dir + os.sep):
                return m.group(0)  # points inside the moved folder: still valid
            new = rel(target, dp)
            return m.group(1) + (new if new.startswith(".") else "./" + new)

        for fn in files:
            if fn.endswith(".md"):
                path = os.path.join(dp, fn)
                text = read(path)
                new = LINK.sub(fix, text)
                if new != text:
                    write(path, new)


def cmd_archive(args):
    ctx = resolve(args)
    require_root(ctx)
    cid, cdir, archived, how = select_change(ctx, args.change)
    if archived:
        raise CliError("change_archived", f"change '{cid}' is already archived at {rel(cdir, ctx['repo'])}")
    state = change_state(ctx, cid, cdir, False)
    refusals = []
    if state["state"] == "blocked":
        refusals.append("planning is incomplete (status: blocked)")
    if state["progress"]["remaining"] and not args.allow_incomplete:
        refusals.append(f"{state['progress']['remaining']} task(s) not done "
                        f"(--allow-incomplete only after the user confirms)")
    report = verify(ctx, cid, False)
    crit = [i for i in report["issues"] if i["severity"] == "CRITICAL"
            and not (args.allow_incomplete and i["message"].startswith("task not done"))]
    if crit:
        refusals.append(f"verify reports {len(crit)} CRITICAL issue(s)")
    actions = []
    recs = [r for r in state["records"] if r.get("path")]
    for r in recs:
        if r["kind"] == "ADR" and r["status"] == "proposed" and not args.leave_proposed:
            actions.append(("accept", r["id"], os.path.join(ctx["repo"], r["path"])))
            if r.get("supersedes"):
                old = find_record(ctx, str(r["supersedes"]))
                if old:
                    actions.append(("supersede", str(r["supersedes"]), old, r["id"]))
    accepted = {a[1] for a in actions if a[0] == "accept"}
    accepted |= {r["id"] for r in recs if r["kind"] == "ADR" and r["status"] == "accepted"}
    for r in recs:
        if r["kind"] == "RFC":
            path = os.path.join(ctx["repo"], r["path"])
            res = str(frontmatter(path)[0].get("resulting-adr") or "")
            if res in accepted:
                actions.append(("accept-rfc", r["id"], path, res))
    dest = os.path.join(ctx["changes"], "archive", f"{TODAY}-{cid}")
    if os.path.exists(dest):
        refusals.append(f"{rel(dest, ctx['repo'])} already exists")
    plan = []
    for a in actions:
        if a[0] == "accept":
            plan.append(f"{a[1]}: status proposed -> accepted, date {TODAY}")
        elif a[0] == "supersede":
            plan.append(f"{a[1]}: status -> superseded, superseded-by {a[3]}")
        else:
            plan.append(f"{a[1]}: status -> accepted (resulting-adr {a[3]})")
    plan += ["decision log: sync rows with the ADR files",
             f"change.md: status -> done, archived {TODAY}",
             f"move {state['path']} -> {rel(dest, ctx['repo'])} (relative links rewritten)"]
    # delivery is reported, never required: the decision stands on its own merits
    hand = report["implementation"]
    for h in hand:
        plan.append(f"implementation ({h['target']}): {h['state']}"
                    + (f" {h['progress']['done']}/{h['progress']['total']} tasks" if h.get("progress") else "")
                    + f" at {h['path'] or h['raw']} — not held back by this archive; the link stays on the change"
                    + ("" if h.get("seed_current") in (True, None) else "; the seed is behind the record"))
    out = {"change": cid, "selected_by": how, "refused": bool(refusals), "refusals": refusals,
           "plan": plan, "applied": False, "implementation": hand,
           "verify": {"verdict": report["verdict"], "summary": report["summary"], "critical": crit}}
    if not refusals and args.yes:
        for a in actions:
            if a[0] == "accept":
                set_fm(a[2], "status", "accepted")
                set_fm(a[2], "date", TODAY)
                fm, _ = frontmatter(a[2])
                sup = fm.get("supersedes")
                set_status_line(a[2], "Accepted" + (f" — supersedes {sup}" if sup else ""))
            elif a[0] == "supersede":
                set_fm(a[2], "status", "superseded")
                set_fm(a[2], "superseded-by", a[3])
                set_status_line(a[2], f"Superseded by {a[3]}")
            else:
                set_fm(a[2], "status", "accepted")
        out["log_changes"] = log_write(ctx)
        cpath = os.path.join(cdir, "change.md")
        set_fm(cpath, "status", "done")
        set_fm(cpath, "archived", TODAY)
        _move_with_links(cdir, dest)
        out["applied"] = True
        out["archived_to"] = rel(dest, ctx["repo"])
        rc, err, found = run_lint(ctx, False)
        out["lint_after"] = {"exit": rc, "errors": [f for f in found if f[0] == "error"], "error": err}

    def human(r):
        lines = [f"archive {r['change']}: " + ("REFUSED" if r["refused"] else
                                               ("done" if r["applied"] else "dry run (pass --yes to apply)"))]
        lines += [f"  refused: {x}" for x in r["refusals"]]
        lines += [f"  - {p}" for p in r["plan"]]
        return "\n".join(lines)
    emit(out, args.json, human)
    if refusals:
        sys.exit(1)


# ---------------------------------------------------------------- init
def cmd_init(args):
    ctx = resolve(args)
    root, repo = ctx["root"], ctx["repo"]
    plan = []
    files = [("README.md", "README.md"), ("AD.md", "AD.md"), ("GLOSSARY.md", "GLOSSARY.md"),
             ("conformance-checklist.md", "conformance-checklist.md"),
             ("decision-log.md", os.path.join(rel(ctx["decisions"], root), "README.md"))]
    for tpl, dst in files:
        target = os.path.join(root, dst)
        plan.append({"action": "keep" if os.path.exists(target) else "create",
                     "path": rel(target, repo), "from": f"assets/templates/{tpl}"})
    if args.with_ci:
        for src, dst in (("tools/arch_lint.py", "tools/arch_lint.py"),
                         ("tools/detect_doc_conventions.py", "tools/detect_doc_conventions.py"),
                         ("workflows/architecture-as-code.yml", ".github/workflows/architecture-as-code.yml")):
            target = os.path.join(repo, dst)
            plan.append({"action": "keep" if os.path.exists(target) else "create",
                         "path": rel(target, repo), "from": f"assets/ci/{src}"})
    out = {"root": rel(root, repo), "root_resolved_by": ctx["root_resolved_by"],
           "plan": plan, "applied": False}
    if args.yes:
        for p in plan:
            if p["action"] != "create":
                continue
            src = os.path.join(SKILL, p["from"])
            dst = os.path.join(repo, p["path"])
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
        idx = os.path.join(root, "README.md")
        if any(p["path"] == rel(idx, repo) and p["action"] == "create" for p in plan):
            text = read(idx).replace("**Docs root:** `docs/architecture/`", f"**Docs root:** `{rel(root, repo)}/`")
            write(idx, text.replace("<YYYY-MM-DD>", TODAY, 1))
        out["applied"] = True
        out["next"] = ("Every created file is a template full of <placeholders>: fill the slice you are "
                       "documenting, delete rows that do not apply, then run arch.py verify --tree.")
    emit(out, args.json, lambda r: "\n".join(f"{p['action']:<7} {p['path']}" for p in r["plan"])
         + ("" if r["applied"] else "\n(dry run — pass --yes to create)"))


# ---------------------------------------------------------------- export
def cmd_export(args):
    import arch_export
    ctx = resolve(args)
    require_root(ctx)
    me = sys.modules[__name__]
    if args.target == "constitution":
        out = arch_export.export_constitution(me, ctx, yes=args.yes, force=args.force, out=args.out)
        emit(out, args.json, lambda r: f"{'wrote' if r['applied'] else 'would write'} {r['dest']} from "
                                       f"{', '.join(r['principles'])} ({r['source']})"
                                       + ("" if r["applied"] else "\n(dry run — pass --yes to write)"))
        return
    cid, cdir, archived, _ = select_change(ctx, args.change)
    state = change_state(ctx, cid, cdir, archived)
    out = arch_export.export(me, ctx, state, args.target, yes=args.yes, force=args.force, out=args.out)

    def human(r):
        lines = [f"{'wrote' if r['applied'] else 'would write'} {r['target']} seed at {r['dest']}/"]
        lines += [f"  {p['action']:<5} {p['path']}" + (f"  ({p['reason']})" if p.get("reason") else
                                                      ("  (overwrites)" if p["overwrites"] else "")) for p in r["plan"]]
        d = r["derived"]
        lines.append(f"derived from: {', '.join(d['records']) or 'no records'}; drivers {', '.join(d['drivers']) or '-'}; "
                     f"quality {', '.join(d['quality']) or '-'}; stories {', '.join(d['stories']) or '-'}; capability {d['capability']}")
        lines += [f"  gap: {g}" for g in r["gaps"]]
        lines.append(f"gate: {r['gate']}")
        if not r["applied"]:
            lines.append("(dry run — pass --yes to write)")
        return "\n".join(lines)
    emit(out, args.json, human)


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(prog="arch.py", description=__doc__.split("\n\n")[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", help="docs root (default: resolved as in SKILL.md Step 0)")
    common.add_argument("--src", help="source tree for ARCH-REF checks")
    common.add_argument("--json", action="store_true", help="machine-readable output")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("context", parents=[common]).set_defaults(fn=cmd_context)
    p = sub.add_parser("consult", parents=[common])
    p.add_argument("--base")
    p.add_argument("--paths", nargs="+")
    p.add_argument("--affects", nargs="+")
    p.set_defaults(fn=cmd_consult)
    p = sub.add_parser("new", parents=[common])
    p.add_argument("change_id")
    p.add_argument("--title", required=True)
    p.add_argument("--level", default="software")
    p.add_argument("--archetype")
    p.set_defaults(fn=cmd_new)
    p = sub.add_parser("record", parents=[common])
    p.add_argument("kind", choices=["adr", "rfc"])
    p.add_argument("--change")
    p.add_argument("--title", required=True)
    p.add_argument("--level")
    p.add_argument("--supersedes")
    p.add_argument("--from-rfc")
    p.set_defaults(fn=cmd_record)
    p = sub.add_parser("status", parents=[common])
    p.add_argument("--change")
    p.set_defaults(fn=cmd_status)
    sub.add_parser("list", parents=[common]).set_defaults(fn=cmd_list)
    p = sub.add_parser("verify", parents=[common])
    p.add_argument("--change")
    p.add_argument("--tree", action="store_true", help="whole-tree health check, no change")
    p.add_argument("--strict", action="store_true")
    p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("log", parents=[common])
    p.add_argument("--write", action="store_true")
    p.set_defaults(fn=cmd_log)
    p = sub.add_parser("archive", parents=[common])
    p.add_argument("--change")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--leave-proposed", action="store_true")
    p.add_argument("--allow-incomplete", action="store_true")
    p.set_defaults(fn=cmd_archive)
    p = sub.add_parser("init", parents=[common])
    p.add_argument("--yes", action="store_true")
    p.add_argument("--with-ci", action="store_true")
    p.set_defaults(fn=cmd_init)
    p = sub.add_parser("export", parents=[common])
    p.add_argument("target", choices=["openspec", "speckit", "constitution"])
    p.add_argument("--change")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--force", action="store_true", help="overwrite seeded files at an existing target")
    p.add_argument("--out", help="target directory (openspec/ or specs/) or file (constitution)")
    p.set_defaults(fn=cmd_export)

    args = ap.parse_args(argv)
    try:
        args.fn(args)
    except CliError as e:
        body = {"error": e.code, "message": e.message}
        body.update(e.extra)
        if getattr(args, "json", False):
            print(json.dumps(body, indent=2))
        else:
            print(f"error ({e.code}): {e.message}", file=sys.stderr)
            if e.extra.get("active"):
                print(f"active changes: {', '.join(e.extra['active'])}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
