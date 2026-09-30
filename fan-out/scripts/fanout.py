#!/usr/bin/env python3
"""fanout.py — deterministic run state for the fan-out skill.

No model calls, no network. Its job is to make the silent failure modes loud (a mutated
shared brief; a verification round that re-reviews approved code) and to give every agent
a stable set of paths.

    fanout.py init "<task>" --mode compete --n 4
    fanout.py plan                            # validate slices.json, measure coupling
    fanout.py seal                            # hash brief + rubric + plan, record base
    fanout.py check                           # fail if any of them changed since seal

    fanout.py lane [<slice>]                  # set up a lane for its strategy
    fanout.py delta <slice> [--findings]      # the per-agent block below the '---'
    fanout.py trespass [<slice>]              # did a lane write outside what it owns?

    fanout.py snapshot <slice> <path>...      # record the bytes under review
    fanout.py scope <slice>                   # in-scope diff / re-opened / out of scope
    fanout.py deciders <slice> [--run]        # the mechanical deciders
    fanout.py gate <slice>                    # 0 done, 1 another round, 2 escalate

    fanout.py integrate [--winner <slice>]    # land the gated lanes in the main tree
    fanout.py calibration [<slice>]           # lint the critique itself (advisory)
    fanout.py followups                       # drain deferred/late/waived to a file
    fanout.py status                          # candidates, verdicts, lanes
"""

import argparse
import difflib
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(".fan-out")
SEALED = ("brief.md", "rubric.md", "slices.json")
BLOCKING = ("blocker", "major")
UNRESOLVED = ("open", "unresolved")   # waived and verified do not block
MAX_ROUNDS = 2

# How a lane is isolated from the others. Each one fixes where the builder writes, where
# its critic looks, how the lane is landed, and how trespass is measured — see SKILL.md,
# "Isolation strategies".
STRATEGIES = ("worktree", "patch", "shared", "read-only")
SLICE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# The seam critic's verdict lives beside the slice verdicts under this id, so gate,
# followups and status treat it like any other. No slice may take the name.
INTEGRATION = "integration"
INTEGRATION_ROUNDS = 1   # a seam that does not close in one round is a wrong contract

# Language keywords. These are never meaningful as names, not even in a definition
# position, where a loose regex can otherwise mistake `if (x)` for a function called `if`.
KEYWORDS = frozenset("""
    int uint float double bool char void const static inline return if else while for
    class struct enum union template typename namespace public private protected virtual
    override final auto using typedef sizeof nullptr true false new delete throw catch
    try def import from lambda self none pass raise yield async await elif print
    let var function export default require module interface extends implements
""".split())

# Generic vocabulary. Too common to signal coupling when it merely appears in a changed
# line — but NOT filtered from definition names: a method genuinely called `Get` or `Add`
# is a real dependency edge, and dropping it would make `scope` miss a re-open, which is
# the one error this design cannot afford.
COMMON = frozenset("""
    the and for not with this that from have has was were will you your are but its
    size data value index count name list dict set get add remove init main test result
    str len type
""".split())

STOPWORDS = KEYWORDS | COMMON

# A `check` must be an observation ("Frame() returns early when entity is invalid"), not
# an instruction ("Add a null guard"). A leading imperative is the mechanical tell, and
# this is the single most common quality leak in the loop — see incremental-review.md.
# Kept deliberately tight: every word here is one no observation ever opens with.
IMPERATIVES = frozenset("""
    add fix improve make use refactor consider ensure remove rename update change
    clarify handle avoid implement replace delete move split extract document simplify
    verify check validate rewrite
""".split())

# A `check` must name the target state ("the body is #C8102E, as in reference.png"), not
# the deviation ("the colour is off"). A deviation restates the claim and leaves the target
# to be guessed — the builder paints the car blue and the round is spent. These are the
# words that describe a gap without ever naming its far side.
DEVIATIONS = frozenset("""
    off wrong incorrect inconsistent inconsistently mismatched mismatch unclear confusing
    insufficient inadequate suboptimal awkward clumsy poor poorly weak weakly unnatural
    improper unpolished sloppy better worse cleaner nicer smoother tighter
    too overly excessive excessively
""".split())

# ...unless the same sentence also carries a target. A number, a quoted or backticked
# literal, a path, a hex colour, or a named referent all give the builder something to aim
# at, and any of them redeems a sentence that also contains a deviation word.
TARGET_TELLS = re.compile(
    r"\d"                                            # any number: value, range, threshold
    r"|[`\"']"                                       # a quoted or backticked literal
    r"|#[0-9A-Fa-f]{3,8}\b"                          # a hex colour
    r"|\b\w+\.(?:png|jpg|svg|md|json|ya?ml|csv|txt|cpp|h|py|ts|tsx|js|rs|go)\b"
    r"|\b(?:matches?|matching|identical|equals?|same as|as in|per the|reference|"
    r"baseline|rubric|brief|spec|specified|exactly)\b",
    re.IGNORECASE)

# Keywords that open a statement rather than a definition. A line starting with one of
# these never defines anything, whatever shape the rest of it has.
STATEMENT_KEYWORDS = frozenset("""
    return if elif else while for switch case do throw raise yield assert
    print del with break continue import from pass await goto
""".split())

BRIEF_TEMPLATE = """# Brief

<!-- SHARED CONTEXT. Byte-identical for every builder AND every critic.
     No agent names, no slice IDs, no timestamps, no run IDs. If it differs
     between agents it goes in the per-agent delta, not here. -->

## Goal

{task}

## Constraints

-

## Out of scope

<!-- What this whole run does not do, for every agent. Per-lane scope — which files a
     lane owns, what belongs to the others — is generated from slices.json into the
     per-agent block by `fanout.py delta`, never written here. -->

-

## Must not

<!-- Hard prohibitions that hold for every agent: APIs that must not change, files
     nobody touches, commands nobody runs. Per-lane prohibitions go in slices.json. -->

-

## Context

<!-- Paths, excerpts, specs, conventions. Everything the agents would otherwise
     each go rediscover on their own. -->

## Visual surface

<!-- Only if there is something to look at: a page, chart, UI state, frame, diagram,
     laid-out document. Give ONE render command and the exact state to render in —
     viewport, seed, theme, sample input, which page. Identical for every agent, or
     the candidates are not comparable. Builders write output to
     renders/<slice-id>/r1/; critics judge that, not the source behind it.
     Delete this section if the work has no visual surface — an invented one costs a
     round and proves nothing. -->

## Acceptance criteria

<!-- Concrete and checkable. "Works well" is not a criterion. -->

-

## Definition of done

-
"""

RUBRIC_TEMPLATE = """# Rubric

<!-- Written BEFORE any builder runs. A rubric written afterwards is a
     rationalisation of the candidate you already liked. -->

## Axes (score 1-5)

<!-- If the brief names a visual surface, at least one axis must be scoreable ONLY
     from the render. Otherwise critics score the source that produces the picture. -->

### <axis-name>
What 5 looks like:
What 1 looks like:
Concrete failure example:

## Blocking conditions

<!-- Any one of these forces verdict=reject regardless of scores. -->

-
"""

# The allocation plan: who does what, in which isolation, against which contracts. It is
# sealed with the brief, because every per-agent block is generated from it.
SLICES_TEMPLATE = {
    "hotspots": [],
    "slices": [
        {
            "id": "",
            "summary": "",
            "task": "",
            "context": "",
            "strategy": "",
            "strategy_reason": "",
            "owns": [],
            "reads": [],
            "out_of_scope": [],
            "must_not": [],
            "provides": [],
            "consumes": [],
            "done_when": [],
        }
    ],
}


# ---------------------------------------------------------------- helpers

def run_dir() -> Path:
    if not ROOT.exists():
        sys.exit("no .fan-out/ directory — run `fanout.py init` first")
    runs = sorted(d for d in ROOT.iterdir() if d.is_dir())
    if not runs:
        sys.exit("no runs found — run `fanout.py init` first")
    return runs[-1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def revisions(d: Path, slice_id: str) -> list:
    base = d / "revisions" / slice_id
    if not base.exists():
        return []
    return sorted(base.glob("v*"), key=lambda p: int(p.name[1:]))


def read_text(path: Path) -> list:
    try:
        return path.read_text(errors="replace").splitlines()
    except OSError:
        return []


def identifiers(lines) -> set:
    out = set()
    for line in lines:
        for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", line):
            if tok.lower() not in STOPWORDS:
                out.add(tok)
    return out


# A change inside a function body must re-open that function's *callers*, and the
# callee's name never appears in the changed lines themselves. So walk back to the
# enclosing definition and add its name to the touched set. Portable heuristics only.
DEF_PATTERNS = (
    re.compile(r"([A-Za-z_][A-Za-z0-9_]*)::([A-Za-z_~][A-Za-z0-9_]*)\s*\("),   # C++ qualified
    re.compile(r"^\s*(?:def|class|fn|func|impl|struct|enum)\s+([A-Za-z_][A-Za-z0-9_]*)"),
    # C-family. The leading type/qualifier is required: without it a bare call statement
    # like `doThing(x)` reads as a definition, which would credit the caller as the definer
    # and cancel the very dependency edge `plan` exists to find.
    re.compile(r"^\s{0,4}[A-Za-z_][\w:<>,&*\s]*\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^;]*\)"
               r"\s*(?:const\s*)?(?:noexcept\s*)?\{?\s*$"),
    re.compile(r"^#{1,6}\s+(.+?)\s*$"),                                        # markdown
)


def enclosing_symbols(lines, idx: int, lookback: int = 300) -> set:
    """Names of the definition containing line `idx`, searching upward."""
    for i in range(min(idx, len(lines) - 1), max(-1, idx - lookback), -1):
        line = lines[i]
        # `return Store().get(s)` otherwise matches the C-family shape and turns a call
        # site into a definition. A statement opening with a keyword never defines.
        head = line.strip().split("(")[0].split()
        if head and head[0].lower() in STATEMENT_KEYWORDS:
            continue
        for pat in DEF_PATTERNS:
            if m := pat.search(line):
                names = {g for g in m.groups() if g}
                out = set()
                for n in names:
                    out |= {t for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", n)
                            if t.lower() not in KEYWORDS}
                if out:
                    return out
    return set()


def definitions(lines) -> set:
    """Symbols this file defines — the ones whose change re-opens every caller."""
    out = set()
    for i in range(len(lines)):
        out |= enclosing_symbols(lines, i, lookback=1)
    return out


def load_verdict(d: Path, slice_id: str) -> dict:
    p = d / "verdicts" / f"{slice_id}.json"
    if not p.exists():
        sys.exit(f"no verdict yet for '{slice_id}' — critics must run first")
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"verdict for '{slice_id}' is not valid JSON: {e}")


def run_meta(d: Path) -> dict:
    return json.loads((d / "run.json").read_text())


# ---------------------------------------------------------------- allocation plan

def load_plan(d: Path, synthesis: bool = True) -> dict:
    """slices.json, normalised; synthesis.json lanes appended when present.

    `files` is the pre-allocation spelling of `owns` and is still read as such.
    """
    spec = d / "slices.json"
    if not spec.exists():
        sys.exit(f"no {spec} — `fanout.py init` writes a skeleton; fill it in")
    try:
        plan = json.loads(spec.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"{spec} is not valid JSON: {e}")
    slices = plan.get("slices", [])
    extra = d / "synthesis.json"
    if synthesis and extra.exists():
        try:
            for s in json.loads(extra.read_text()).get("slices", []):
                slices.append({**s, "synthesis": True})
        except json.JSONDecodeError as e:
            sys.exit(f"{extra} is not valid JSON: {e}")
    for s in slices:
        if "owns" not in s and "files" in s:
            s["owns"] = s["files"]
        for key in ("owns", "reads", "out_of_scope", "must_not", "provides", "consumes",
                    "done_when"):
            s.setdefault(key, [])
        for key in ("task", "context"):
            s.setdefault(key, "")
    plan["slices"] = slices
    plan.setdefault("hotspots", [])
    return plan


def maybe_spec(d: Path, slice_id: str):
    """The slice's plan entry, or None — for commands that also serve runs (and the
    integration verdict) that have no lane."""
    if not (d / "slices.json").exists():
        return None
    try:
        plan = load_plan(d)
    except SystemExit:
        return None
    return next((s for s in plan["slices"] if s.get("id") == slice_id), None)


def hotspot_paths(plan: dict) -> list:
    return [h["path"] if isinstance(h, dict) else h for h in plan["hotspots"]]


def slice_spec(plan: dict, slice_id: str) -> dict:
    for s in plan["slices"]:
        if s.get("id") == slice_id:
            return s
    sys.exit(f"no slice '{slice_id}' in slices.json"
             f"{' or synthesis.json' if any(s.get('synthesis') for s in plan['slices']) else ''}")


def under(path: str, entries) -> str:
    """The entry that covers `path` — an exact file, or a directory given with a
    trailing slash. Empty when none does."""
    for e in entries:
        e = e.rstrip("/")
        if path == e or path.startswith(e + "/"):
            return e
    return ""


def overlaps(a, b) -> set:
    return ({x for x in a if under(x, b)} | {y for y in b if under(y, a)})


def expand(entries) -> list:
    """Files behind the owns entries, for measuring coupling. Directories are walked."""
    out = []
    for e in entries:
        p = Path(e)
        if p.is_dir():
            out += sorted(q for q in p.rglob("*") if q.is_file() and ".git" not in q.parts)
        else:
            out.append(p)
    return out


def validate_plan(plan: dict, mode: str) -> tuple:
    """Errors stop `seal`; warnings are printed and left to judgement."""
    errors, warnings = [], []
    slices = [s for s in plan["slices"] if not s.get("synthesis")]
    ids = [s.get("id", "") for s in plan["slices"]]
    hot = hotspot_paths(plan)

    # Shape first: every check below assumes text is text and lists are lists.
    for s in plan["slices"]:
        tag = s.get("id") or "(no id)"
        for key in ("summary", "task", "context", "strategy", "strategy_reason"):
            if not isinstance(s.get(key, ""), str):
                errors.append(f"{tag}: {key} must be text (one string, newlines allowed)")
        for key in ("owns", "reads", "out_of_scope", "must_not", "provides", "consumes",
                    "done_when"):
            if not isinstance(s[key], list):
                errors.append(f"{tag}: {key} must be a list")
    if errors:
        return errors, warnings

    if len(slices) < 2:
        warnings.append("fewer than two slices — a fan-out of one is a single agent")
    for s in plan["slices"]:
        sid = s.get("id", "")
        tag = sid or "(no id)"
        if not SLICE_ID.match(sid):
            errors.append(f"{tag}: id must be lowercase and hyphenated")
        if sid == INTEGRATION:
            errors.append(f"{tag}: '{INTEGRATION}' is reserved for the seam verdict")
        if ids.count(sid) > 1:
            errors.append(f"{tag}: duplicate id")
        if not (s.get("summary") or "").strip():
            errors.append(f"{tag}: no summary — in compete mode this is the constraint")
        if mode == "partition" and not s.get("synthesis") and not s["task"].strip():
            warnings.append(f"{tag}: no task — the builder gets only the one-line summary")
        strategy = s.get("strategy", "")
        if strategy not in STRATEGIES:
            errors.append(f"{tag}: strategy must be one of {', '.join(STRATEGIES)}")
        if not (s.get("strategy_reason") or "").strip():
            errors.append(f"{tag}: no strategy_reason — the choice is decided per lane, "
                          "so record why")
        if strategy == "read-only" and s["owns"]:
            errors.append(f"{tag}: a read-only lane owns nothing")
        if strategy != "read-only" and not s["owns"]:
            warnings.append(f"{tag}: owns nothing — trespass will flag every write")
        if mode == "compete" and strategy == "shared":
            errors.append(f"{tag}: compete lanes write the same files; 'shared' would "
                          "have them overwrite each other")
        if hit := overlaps(s["owns"], hot):
            errors.append(f"{tag}: owns hotspot(s) {', '.join(sorted(hit))} — hotspots "
                          "belong to no lane and are applied at integration")
        if s.get("synthesis"):
            if strategy != "worktree":
                errors.append(f"{tag}: a synthesis lane starts from the winner's tree, "
                              "so it must be 'worktree'")
            if s.get("from") not in ids:
                errors.append(f"{tag}: synthesis 'from' must name an existing lane")
        for c in s["consumes"]:
            src, sym = c.get("from"), c.get("symbol")
            provider = next((p for p in plan["slices"] if p.get("id") == src), None)
            if provider is None:
                errors.append(f"{tag}: consumes '{sym}' from unknown lane '{src}'")
            elif sym not in {p.get("symbol") for p in provider["provides"]}:
                errors.append(f"{tag}: consumes '{sym}' but {src} does not provide it — "
                              "a seam with no contract has nothing to verify")
        for p in s["provides"]:
            if not (p.get("symbol") and (p.get("contract") or "").strip()):
                errors.append(f"{tag}: every provides entry needs a symbol and a contract")

    if mode == "partition":
        for i, a in enumerate(slices):
            for b in slices[i + 1:]:
                if shared := overlaps(a["owns"], b["owns"]):
                    errors.append(f"{a.get('id')} <-> {b.get('id')}: both own "
                                  f"{', '.join(sorted(shared))} — merge them")
    if order_lanes(plan["slices"]) is None:
        errors.append("consumes edges form a cycle — the lanes in it are one slice, "
                      "or two phases")
    return errors, warnings


def order_lanes(slices) -> list:
    """Providers before consumers, plan order otherwise. None on a cycle."""
    pending = [s["id"] for s in slices if s.get("id")]
    needs = {s["id"]: {c.get("from") for c in s.get("consumes", [])} & set(pending)
             for s in slices if s.get("id")}
    out = []
    while pending:
        ready = [x for x in pending if not (needs[x] - set(out))]
        if not ready:
            return None
        out.append(ready[0])
        pending.remove(ready[0])
    return out


def contracts_between(plan: dict, provider: str, consumer: str) -> set:
    c = slice_spec(plan, consumer)
    return {x.get("symbol") for x in c["consumes"] if x.get("from") == provider}


# ---------------------------------------------------------------- git and lanes

def git(*args, cwd=None, check=True) -> str:
    try:
        res = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit("git is not installed — lanes need it")
    if check and res.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed:\n{res.stderr.strip()}")
    return res.stdout


def in_git() -> bool:
    try:
        return subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                              capture_output=True, text=True).stdout.strip() == "true"
    except FileNotFoundError:
        return False


def git_paths(out: str) -> set:
    return {line for line in out.splitlines() if line.strip()}


def seal_info(d: Path) -> dict:
    p = d / "seal.json"
    if not p.exists():
        sys.exit("not sealed — run `fanout.py seal` before spawning agents")
    data = json.loads(p.read_text())
    # Runs sealed before the allocation plan existed stored a flat name -> hash map.
    return data if "files" in data else {"files": data}


def base_of(d: Path) -> str:
    base = seal_info(d).get("base")
    if not base:
        sys.exit("this run recorded no base commit at seal (not a git repository, or\n"
                 "sealed by an older fanout.py) — lanes cannot be set up or measured")
    return base


def lane_dir(d: Path, slice_id: str) -> Path:
    return d / "lanes" / slice_id


def patch_file(d: Path, slice_id: str) -> Path:
    return d / "lanes" / f"{slice_id}.patch"


def applied_dir(d: Path, slice_id: str) -> Path:
    return d / "lanes" / f"{slice_id}-apply"


def lane_root(d: Path, spec: dict) -> Path:
    """Where this lane's files are to be read, run and snapshotted."""
    if spec.get("strategy") == "worktree":
        return lane_dir(d, spec["id"])
    if spec.get("strategy") == "patch" and applied_dir(d, spec["id"]).exists():
        return applied_dir(d, spec["id"])
    return Path(".")


def patch_paths(text: str) -> set:
    out = set()
    for line in text.splitlines():
        if m := re.match(r"diff --git a/(.+?) b/(.+)$", line):
            out |= {m.group(1), m.group(2)}
        elif line.startswith(("--- a/", "+++ b/")):
            out.add(line[6:].split("\t")[0])
    return out


def lane_patch(d: Path, spec: dict) -> str:
    """The lane's whole change against the base, as a patch `git apply` accepts."""
    strategy, sid = spec.get("strategy"), spec["id"]
    if strategy == "patch":
        p = patch_file(d, sid)
        if not p.exists():
            sys.exit(f"{sid}: no patch at {p}")
        return p.read_text()
    if strategy == "worktree":
        root = lane_dir(d, sid)
        if not root.exists():
            sys.exit(f"{sid}: no worktree at {root} — `fanout.py lane {sid}` first")
        git("add", "-A", cwd=root)   # untracked files belong in the patch too
        return git("diff", "--cached", "--binary", base_of(d), cwd=root)
    return ""


def lane_writes(d: Path, spec: dict):
    """Paths this lane changed, or None when it has not produced anything yet.

    Worktree and patch lanes are measured exactly. Shared and read-only lanes write in
    one tree, so their changes are measured together by `tree_writes`."""
    strategy, sid = spec.get("strategy"), spec["id"]
    if strategy == "patch":
        p = patch_file(d, sid)
        return patch_paths(p.read_text()) if p.exists() else None
    if strategy == "worktree":
        root = lane_dir(d, sid)
        if not root.exists():
            return None
        base = base_of(d)
        return (git_paths(git("diff", "--name-only", base, cwd=root))
                | git_paths(git("ls-files", "--others", "--exclude-standard", cwd=root)))
    return None


def load_applied(d: Path) -> list:
    p = d / "integration" / "applied.json"
    return json.loads(p.read_text()) if p.exists() else []


def tree_writes(d: Path, plan: dict) -> set:
    """What changed in the main tree since the seal, excluding the run directory, what
    was already dirty at seal, and what `integrate` itself put there."""
    info = seal_info(d)
    base = base_of(d)
    paths = (git_paths(git("diff", "--name-only", base))
             | git_paths(git("ls-files", "--others", "--exclude-standard")))
    paths -= set(info.get("dirty", []))
    paths = {p for p in paths if not p.startswith(ROOT.name + "/")}
    applied = load_applied(d)
    if applied:
        landed = set()
        for entry in applied:
            landed |= set(entry.get("paths", []))
        paths -= landed
        # After integration the orchestrator edits hotspots on purpose.
        paths = {p for p in paths if not under(p, hotspot_paths(plan))}
    return paths


def classify(paths, spec: dict, plan: dict) -> list:
    """(path, why) for every write the lane was not allowed to make."""
    out = []
    for path in sorted(paths):
        if spec.get("strategy") != "read-only" and under(path, spec["owns"]):
            continue
        if under(path, hotspot_paths(plan)):
            out.append((path, "hotspot — request the entry in your report instead"))
            continue
        owner = next((o["id"] for o in plan["slices"]
                      if o is not spec and under(path, o["owns"])), None)
        out.append((path, f"owned by {owner}" if owner else "owned by no lane"))
    return out


def trespass_of(d: Path, plan: dict, spec: dict):
    """Violations for one worktree/patch lane, or None if it has nothing yet."""
    writes = lane_writes(d, spec)
    if writes is None:
        return None
    return classify(writes, spec, plan)


def tree_trespass(d: Path, plan: dict) -> list:
    """Violations in the main tree, attributed as far as ownership allows."""
    in_tree = [s for s in plan["slices"] if s.get("strategy") in ("shared", "read-only")]
    allowed = [e for s in in_tree if s.get("strategy") == "shared" for e in s["owns"]]
    union = {"id": "(shared tree)", "strategy": "shared", "owns": allowed}
    return classify(tree_writes(d, plan), union, plan)


def section(text: str, title: str) -> str:
    """Body of the markdown section headed `title`, up to the next heading at its level
    or above. Empty when absent or when it says only 'none'."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if m and m.group(2).strip().lower() == title.lower():
            level, body = len(m.group(1)), []
            for nxt in lines[i + 1:]:
                h = re.match(r"^(#{1,6})\s", nxt)
                if h and len(h.group(1)) <= level:
                    break
                body.append(nxt)
            out = "\n".join(body).strip()
            return "" if re.fullmatch(r"[-*\s]*(none|n/?a|-)?\.?", out, re.I) else out
    return ""


def gate_state(d: Path, slice_id: str) -> str:
    """The gate's answer without its report: pass, blocking, unreasoned, or none."""
    p = d / "verdicts" / f"{slice_id}.json"
    if not p.exists():
        return "none"
    try:
        findings = json.loads(p.read_text()).get("findings", [])
    except json.JSONDecodeError:
        return "none"
    if any(f.get("status") == "waived" and not (f.get("reason") or "").strip()
           for f in findings):
        return "unreasoned"
    if any(f.get("severity") in BLOCKING and f.get("status", "open") in UNRESOLVED
           for f in findings):
        return "blocking"
    return "pass"


# ---------------------------------------------------------------- commands

def cmd_init(args) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    slug = re.sub(r"[^a-z0-9]+", "-", args.task.lower())[:40].strip("-") or "run"
    d = ROOT / f"{stamp}-{slug}"
    (d / "candidates").mkdir(parents=True)
    (d / "verdicts").mkdir()
    (d / "revisions").mkdir()
    (d / "renders").mkdir()

    (d / "brief.md").write_text(BRIEF_TEMPLATE.format(task=args.task))
    (d / "rubric.md").write_text(RUBRIC_TEMPLATE)
    (d / "slices.json").write_text(json.dumps(SLICES_TEMPLATE, indent=2) + "\n")
    (d / "run.json").write_text(
        json.dumps(
            {"task": args.task, "mode": args.mode, "n": args.n,
             "max_rounds": args.max_rounds, "created": stamp},
            indent=2,
        ) + "\n"
    )

    print(f"run:    {d}")
    print(f"mode:   {args.mode}   n: {args.n}   max verification rounds: {args.max_rounds}")
    print(f"brief:  {d / 'brief.md'}")
    print(f"rubric: {d / 'rubric.md'}")
    print(f"plan:   {d / 'slices.json'}")
    print("\nFill all three, run `fanout.py plan`, then: fanout.py seal")


def cmd_seal(args) -> None:
    d = run_dir()
    mode = run_meta(d)["mode"]
    plan = load_plan(d, synthesis=False)
    errors, warnings = validate_plan(plan, mode)
    for w in warnings:
        print(f"  warn: {w}")
    if errors:
        print("\nThe allocation plan does not hold:", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        sys.exit("\nFix slices.json, then seal again. Every per-agent block is generated "
                 "from it, so it cannot be repaired after spawning.")

    info = {"files": {name: digest(d / name) for name in SEALED}}
    strategies = {s["strategy"] for s in plan["slices"]}
    if in_git():
        top = Path(git("rev-parse", "--show-toplevel").strip()).resolve()
        if Path.cwd().resolve() != top:
            sys.exit(f"run fanout.py from the repository root ({top}) — owns paths are "
                     "repo-relative and lanes are measured from there")
        info["base"] = git("rev-parse", "HEAD", check=False).strip() or None
        if not info["base"]:
            sys.exit("the repository has no commit yet — lanes branch from one")
        dirty = (git_paths(git("diff", "--name-only", "HEAD"))
                 | git_paths(git("ls-files", "--others", "--exclude-standard")))
        info["dirty"] = sorted(p for p in dirty if not p.startswith(ROOT.name + "/"))
        if info["dirty"]:
            print(f"  warn: {len(info['dirty'])} uncommitted path(s) at seal. They are "
                  "excluded from shared-tree\n        trespass checks, so a lane writing "
                  "one of them goes unnoticed.")
            if strategies & {"worktree", "patch"}:
                print("        Worktree and patch lanes start from the base commit and will "
                      "NOT see them —\n        commit or stash first if a lane needs them "
                      "(the user's call).")
    elif strategies - {"read-only"}:
        sys.exit("lanes that write need git: the base commit is what worktrees branch "
                 "from, patches apply to, and trespass is measured against")

    (d / "seal.json").write_text(json.dumps(info, indent=2) + "\n")
    for name, h in info["files"].items():
        print(f"sealed {name}  {h[:12]}")
    if info.get("base"):
        print(f"base   {info['base'][:12]}")
    print("\nBrief, rubric and plan are now immutable. Per-agent text comes from\n"
          "`fanout.py delta <slice-id>` and goes below the '---' separator.")


def cmd_check(args) -> None:
    d = run_dir()
    lock = seal_info(d)["files"]
    drift = [n for n, h in lock.items() if digest(d / n) != h]
    if drift:
        print("DRIFT: " + ", ".join(drift), file=sys.stderr)
        print(
            "\nThe shared block changed mid-run. Agents spawned before and after this\n"
            "edit worked from different ground truths, so their outputs are not\n"
            "comparable and the cached prefix is dead. Finish this round, then start a\n"
            "new sealed run with the corrected brief.",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"clean — {', '.join(lock)} unchanged since seal")


def cmd_snapshot(args) -> None:
    """Record the exact bytes under review. Must run BEFORE the builder edits."""
    d = run_dir()
    n = len(revisions(d, args.slice)) + 1
    dest = d / "revisions" / args.slice / f"v{n}"
    dest.mkdir(parents=True)

    # A worktree lane's files live in its own tree; the same relative path in the main
    # tree is the base, not the candidate. Resolve against the lane so both agree.
    spec = maybe_spec(d, args.slice)
    if spec and spec.get("strategy") == "patch" and not applied_dir(d, args.slice).exists():
        shutil.rmtree(dest)
        sys.exit(f"{args.slice} is a patch lane: its files exist only once applied.\n"
                 f"Run `fanout.py lane {args.slice} --materialize` first (again after every "
                 "new patch), then snapshot.")
    root = lane_root(d, spec) if spec else Path(".")

    manifest = {}
    for raw in args.paths:
        src = Path(raw) if Path(raw).is_absolute() else root / raw
        if not src.exists():
            shutil.rmtree(dest)
            sys.exit(f"missing: {src}")
        key = hashlib.sha256(str(src.resolve()).encode()).hexdigest()[:12]
        shutil.copy2(src, dest / key)
        manifest[key] = {"path": str(src), "sha": digest(src)}

    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"snapshot {args.slice} v{n}  ({len(manifest)} file(s))")
    for meta in manifest.values():
        print(f"  {meta['sha'][:12]}  {meta['path']}")
    if n == 1:
        print("\nThis is the baseline. Snapshot again after the builder's fix, then `scope`.")


def cmd_scope(args) -> None:
    """Partition the artifact into in-scope / re-opened / out-of-scope."""
    d = run_dir()
    revs = revisions(d, args.slice)
    if len(revs) < 2:
        sys.exit(
            f"need two snapshots of '{args.slice}' to compute a delta (have {len(revs)}).\n"
            "Snapshot before the builder's fix and again after."
        )
    old, new = revs[-2], revs[-1]
    old_m = json.loads((old / "manifest.json").read_text())
    new_m = json.loads((new / "manifest.json").read_text())

    changed, unchanged, touched = [], [], set()

    for key, meta in new_m.items():
        prev = old_m.get(key)
        if prev is None:
            changed.append((meta["path"], ["(new file)"]))
            touched |= identifiers(read_text(new / key))
            continue
        if prev["sha"] == meta["sha"]:
            unchanged.append((meta["path"], key))
            continue

        a, b = read_text(old / key), read_text(new / key)
        hunks, delta = [], []
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
            if op == "equal":
                continue
            enclosing = enclosing_symbols(b, j1) | enclosing_symbols(a, i1)
            label = f"lines {j1 + 1}-{max(j2, j1 + 1)} ({op})"
            if enclosing:
                label += f"  in {'/'.join(sorted(enclosing))}"
            hunks.append(label)
            delta += a[i1:i2] + b[j1:j2]
            touched |= enclosing
        changed.append((meta["path"], hunks))
        touched |= identifiers(delta)

    for key, meta in old_m.items():
        if key not in new_m:
            changed.append((meta["path"], ["(removed)"]))

    print(f"scope for {args.slice}   {old.name} -> {new.name}")
    print(f"\nIN SCOPE — changed, review fully ({len(changed)}):")
    for path, hunks in changed or [("(nothing changed)", [])]:
        print(f"  {path}")
        for h in hunks:
            print(f"      {h}")

    reopened, clear = [], []
    for path, key in unchanged:
        body = read_text(new / key)
        hits = sorted({s for s in touched
                       if any(re.search(rf"\b{re.escape(s)}\b", ln) for ln in body)})
        (reopened if hits else clear).append((path, hits))

    print(f"\nRE-OPENED — unchanged but reference a touched symbol ({len(reopened)}):")
    print("  Ask only: did this change break you? Not a fresh general review.")
    for path, hits in reopened or [("(none)", [])]:
        print(f"  {path}")
        if hits:
            print(f"      via: {', '.join(hits[:6])}{' ...' if len(hits) > 6 else ''}")

    print(f"\nOUT OF SCOPE — do not read ({len(clear)}):")
    for path, _ in clear or [("(none)", [])]:
        print(f"  {path}")

    approved = load_verdict(d, args.slice).get("approved", [])
    if approved:
        print(f"\nprior approvals on record: {len(approved)}")
    print(f"\ntouched symbols: {len(touched)}")
    print("Re-opening over-approximates on purpose; a false re-open costs tokens, a\n"
          "missed one ships a regression. Overrule sparingly and note it in the fold.")


def cmd_deciders(args) -> None:
    """Print the mechanical deciders for a slice's unresolved findings.

    A `check` is an observation, and an observation a shell command can settle costs
    nothing: the finding closes before a verifier is spawned at all. By default this only
    PRINTS those commands. The strings were written by a critic agent, so `--run`, which
    executes them, is for after you have read them — never on sight. They run in the
    lane's own tree, since that is where the candidate is.
    """
    d = run_dir()
    verdict = load_verdict(d, args.slice)
    spec = maybe_spec(d, args.slice)
    cwd = lane_root(d, spec) if spec else Path(".")
    findings = [f for f in verdict.get("findings", [])
                if f.get("status", "open") in UNRESOLVED]
    if not findings:
        print(f"{args.slice}: no unresolved findings — nothing to decide.")
        return

    mechanical = [f for f in findings if (f.get("check_cmd") or "").strip()]
    judgement = [f for f in findings if not (f.get("check_cmd") or "").strip()]

    print(f"deciders {args.slice}   round {verdict.get('round', 1)}   "
          f"{len(mechanical)}/{len(findings)} mechanised")

    if mechanical:
        print(f"\nRun these in {cwd}. Exit 0 means the check holds.\n")
        for f in mechanical:
            print(f"  # [{f.get('severity')}] {f.get('id')}  {f.get('check', '')}")
            print(f"  {f['check_cmd'].strip()}\n")
            if getattr(args, "run", False):
                print("  Running automated decider...")
                try:
                    res = subprocess.run(f['check_cmd'].strip(), shell=True, cwd=cwd,
                                         capture_output=True, text=True, timeout=30)
                    if res.returncode == 0:
                        print(f"  SUCCESS! Setting {f['id']} to verified.")
                        f['status'] = 'verified'
                        f['reason'] = f"Automated decider succeeded:\n{res.stdout.strip()[:200]}"
                    else:
                        print(f"  FAILED. (exit {res.returncode})\n{res.stderr.strip()[:200]}")
                except Exception as e:
                    print(f"  FAILED TO RUN: {e}")
        if getattr(args, "run", False):
            (d / "verdicts" / f"{args.slice}.json").write_text(json.dumps(verdict, indent=2))
            print("\nUpdated verdicts file with automated results.")
        else:
            print("A command that exits 0 closes its finding here: set status to 'verified'\n"
                  "with a reason naming the command and what it printed. The verifier never\n"
                  "sees it. A non-zero exit is not a fix attempt gone wrong — it is the\n"
                  "finding still standing, so leave it open and send it to the builder.")
        print("\nDo not close a finding on a visual axis this way. A render is decided by\n"
              "looking at it beside the previous one, and a command that proves the file\n"
              "exists has not looked.")

    if judgement:
        print(f"\nNo decider ({len(judgement)}) — these cost a verifier round:\n")
        for f in judgement:
            print(f"  [{f.get('severity')}] {f.get('id')}  {f.get('check', '')}")
        print("\nSome of these are genuinely judgement. Where one is not — a condition a\n"
              "grep or a test would settle — write the command onto the finding as\n"
              "`check_cmd` yourself rather than paying an agent to read for it.")


def cmd_gate(args) -> None:
    """Stop condition. 0 = done, 1 = another round, 2 = escalate."""
    d = run_dir()
    meta = json.loads((d / "run.json").read_text())
    cap = meta.get("max_rounds", MAX_ROUNDS)
    if args.slice == INTEGRATION:
        # A seam that stays open after one fix means the contract itself was wrong, and
        # no builder can repair a plan. That is the orchestrator's to escalate.
        cap = INTEGRATION_ROUNDS
    verdict = load_verdict(d, args.slice)
    findings = verdict.get("findings", [])
    rnd = verdict.get("round", 1)

    def bucket(sev):
        return [f for f in findings
                if f.get("severity") == sev and f.get("status", "open") in UNRESOLVED]

    blocking = [f for sev in BLOCKING for f in bucket(sev)]
    deferred = [f for sev in ("minor", "nit") for f in bucket(sev)]
    late = [f for f in findings if f.get("late")]
    verified = [f for f in findings if f.get("status") == "verified"]
    waived = [f for f in findings if f.get("status") == "waived"]

    print(f"gate {args.slice}   round {rnd}/{cap + 1}")
    print(f"  verified:  {len(verified)}")
    print(f"  blocking:  {len(blocking)}   (blocker/major still open)")
    print(f"  deferred:  {len(deferred)}   (minor/nit — follow-ups, never block)")
    unreasoned = [f for f in waived if not (f.get("reason") or "").strip()]
    if waived:
        print(f"  waived:    {len(waived)}   (shipped as known issues)")
        for f in waived:
            reason = f.get("reason")
            print(f"      {f.get('id')}: {reason or 'NO REASON GIVEN'}")
    if late:
        print(f"  late:      {len(late)}   (raised outside scope — round 1 under-reviewed)")

    # A finding that arrives at a verification round already `unresolved` has survived a
    # builder attempt against its check alone. Naming a remedy is the one place this loop
    # lets a critic say *how*, and it is earned by evidence that saying *what* did not
    # land — see incremental-review.md, "When the check alone stops working".
    unguided = [f for f in blocking
                if f.get("status") == "unresolved" and not (f.get("remedy") or "").strip()]

    for f in blocking:
        anchor = f.get("anchor", {})
        where = anchor.get("symbol") or anchor.get("file") or "?"
        print(f"\n  [{f.get('severity')}] {f.get('id')}  {where}")
        print(f"      claim: {f.get('claim', '')}")
        # observed → check is the delta. Printed adjacent so a target that never moves
        # while the observation does is visible at a glance across rounds.
        if observed := f.get("observed"):
            print(f"      observed: {observed}")
        print(f"      check: {f.get('check', '')}")
        if sites := f.get("sites"):
            print(f"      sites: {', '.join(str(s) for s in sites)}")
        if cmd := f.get("check_cmd"):
            print(f"      check_cmd: {cmd}")
        if reason := f.get("reason"):
            print(f"      reason: {reason}")
        if remedy := f.get("remedy"):
            print(f"      remedy: {remedy}   (non-binding — the check is the contract)")

    if unguided:
        print(f"\n  {len(unguided)} unresolved finding(s) carry no remedy.")
        print("  Each has now survived a builder round against its check. Ask the next\n"
              "  verifier for a remedy on them, or say they are not closeable here — a\n"
              "  third identical round is the expensive way to learn the same thing.")

    # Waiving is the one path where a blocker leaves the loop by decision rather than by
    # fix. An unreasoned waive is therefore a silent ship, and the fold report has nothing
    # to carry. Cheap to enforce, and the only place the gate second-guesses the operator.
    if unreasoned:
        print(f"\nSTOP — {len(unreasoned)} waived finding(s) carry no reason.")
        print("A waive ships a known issue on your authority; the reason is what makes\n"
              "that decision reviewable. Record one on each, then re-run the gate.")
        sys.exit(2)

    if not blocking:
        print("\nPASS — no open blockers or majors.")
        if deferred:
            print("Run `fanout.py followups` to drain the deferred findings before folding.")
        sys.exit(0)

    if rnd > cap:
        print(f"\nESCALATE — {rnd - 1} verification rounds spent, still blocking.")
        print("Three attempts failing points at the brief or the slice cut, not the\n"
              "builder. Take the disagreement to the user rather than spawning another.")
        if remedies := [f for f in blocking if (f.get("remedy") or "").strip()]:
            print("\nCarry these remedies into the escalation — they are the critic's own\n"
                  "account of what it would take, and the user is deciding, not guessing:")
            for f in remedies:
                print(f"  {f.get('id')}: {f['remedy']}")
        sys.exit(2)

    print("\nANOTHER ROUND — snapshot, send only these findings, then `scope`.")
    sys.exit(1)


def cmd_followups(args) -> None:
    """Drain the findings that leave the run unfixed, into one file.

    Every other path through this loop has an outlet: a finding gets fixed, or it holds
    the gate. Deferred, late and waived findings have neither — without somewhere to go
    they stay inside verdict JSON that nobody opens after the fold, which is how a run
    'ships clean' while carrying a dozen things a critic actually flagged.
    """
    d = run_dir()
    meta = json.loads((d / "run.json").read_text())
    names = sorted(p.stem for p in (d / "verdicts").glob("*.json"))
    if not names:
        sys.exit("no verdicts yet — nothing to drain")

    waived, late, deferred = [], [], []
    for name in names:
        for f in load_verdict(d, name).get("findings", []):
            entry = (name, f)
            holds_gate = (f.get("severity") in BLOCKING
                          and f.get("status", "open") in UNRESOLVED)
            if f.get("status") == "waived":
                waived.append(entry)
            elif holds_gate:
                # Still work, not a follow-up — a late blocker reopens the round rather
                # than draining. The gate is where it belongs until it resolves.
                continue
            elif f.get("late"):
                late.append(entry)
            elif f.get("severity") in ("minor", "nit"):
                deferred.append(entry)

    def render(title, note, items):
        if not items:
            return []
        out = [f"## {title}", "", note, ""]
        for slice_id, f in items:
            anchor = f.get("anchor", {})
            where = anchor.get("symbol") or anchor.get("file") or "?"
            out.append(f"- **[{f.get('severity')}] {f.get('id')}** "
                       f"({slice_id} — {where}) {f.get('claim', '')}")
            if observed := f.get("observed"):
                out.append(f"  - observed: {observed}")
            if check := f.get("check"):
                out.append(f"  - check: {check}")
            if sites := f.get("sites"):
                out.append(f"  - sites: {', '.join(str(s) for s in sites)}")
            if cmd := f.get("check_cmd"):
                out.append(f"  - check_cmd: `{cmd}`")
            if reason := f.get("reason"):
                out.append(f"  - reason: {reason}")
            # Whoever picks this up later did not watch the rounds that produced it.
            if remedy := f.get("remedy"):
                out.append(f"  - remedy (non-binding): {remedy}")
        out.append("")
        return out

    lines = [f"# Follow-ups — {meta['task']}", "",
             f"Drained from {len(names)} verdict(s) by `fanout.py followups`. Everything "
             "here was seen by a critic and deliberately not fixed in this run. Nothing "
             "here blocked the gate; that is the point of writing it down.", ""]
    lines += render("Shipped as known issues", "Waived on the orchestrator's authority. "
                    "The reason is the record of that decision.", waived)
    lines += render("Raised late", "Surfaced after round 1, outside the scope the ratchet "
                    "guard allows. A cluster here means round 1 under-reviewed.", late)
    lines += render("Deferred", "Minor findings and nits. Never actioned in this run by "
                    "design.", deferred)
    if not (waived or late or deferred):
        lines += ["Nothing deferred, waived or late. The run closed clean.", ""]

    # The builders' own report sections. Collected, not verified: whether a critic
    # checked each one is exactly what the fold has to say.
    reported = []
    for cand in sorted((d / "candidates").glob("*.md")):
        text = cand.read_text(errors="replace")
        for title in ("Assumptions", "Scope deviations", "Open questions"):
            if body := section(text, title):
                reported.append((cand.stem, title, body))
    if reported:
        lines += ["## Builder-reported", "",
                  "Copied from each candidate's report. Nobody has verified these by "
                  "being listed here — the fold report says which ones a critic checked.",
                  ""]
        for slice_id, title, body in reported:
            lines += [f"### {slice_id} — {title}", "", body, ""]
    lines += ["---", "",
              "Drained mechanically. What no tool can say is which builder assumptions a "
              "critic actually checked — see the fold report step in SKILL.md."]

    dest = d / "follow-ups.md"
    dest.write_text("\n".join(lines) + "\n")
    total = len(waived) + len(late) + len(deferred)
    print(f"wrote {dest}  ({total} item(s): "
          f"{len(waived)} waived, {len(late)} late, {len(deferred)} deferred)")
    if total:
        print("Fold this file into the report rather than restating it from memory.")


def cmd_calibration(args) -> None:
    """Lint the critique, not the work.

    Every signal here is a documented failure mode of a critic, computed from the verdict
    JSON alone. By default it is ADVISORY and exits 0: miscalibration is a reason to read
    a verdict yourself before folding on it, never a reason to hold a slice, and the gate
    never consults it. `--strict` exits 1 on any flag, for callers that want a flagged
    verdict repaired before they go on.
    """
    d = run_dir()
    if getattr(args, "slice", None):
        names = [args.slice]
    else:
        names = sorted(p.stem for p in (d / "verdicts").glob("*.json"))
    if not names:
        sys.exit("no verdicts yet — critics must run first")

    total_flags = 0
    for name in names:
        v = load_verdict(d, name)
        findings = v.get("findings", [])
        evidence = v.get("evidence", [])
        approved = v.get("approved", [])
        blocking = [f for f in findings if f.get("severity") in BLOCKING]
        counts = {sev: sum(1 for f in findings if f.get("severity") == sev)
                  for sev in ("blocker", "major", "minor", "nit")}

        flags = []
        # Severity has stopped discriminating: everything is urgent, so nothing is.
        if len(findings) >= 4 and len(blocking) / len(findings) >= 0.75:
            flags.append(("INFLATION",
                          f"{len(blocking)}/{len(findings)} findings block the gate",
                          "Re-read them: a preference filed as major spends a builder "
                          "round on taste."))
        # The opposite failure: a pass with nothing behind it.
        if v.get("verdict") == "accept" and len(evidence) < 2:
            flags.append(("RUBBER-STAMP",
                          f"verdict 'accept' on {len(evidence)} evidence entr"
                          f"{'y' if len(evidence) == 1 else 'ies'}",
                          "An accept this thin is unproven; treat it as unreviewed."))
        # Approval claims must be proportional to what was actually examined.
        if len(approved) > 3 * max(len(evidence), 1):
            flags.append(("OVER-APPROVED",
                          f"{len(approved)} approved against {len(evidence)} evidence",
                          "Step 5 will not look at approved scope again — this is where "
                          "a regression walks through."))
        # A blocker nobody can mechanically resolve, or one that will lose its anchor.
        for f in blocking:
            check = (f.get("check") or "").strip()
            first = re.sub(r"[^a-z]", "", check.split(" ")[0].lower()) if check else ""
            if not check:
                flags.append(("UNCHECKABLE", f"{f.get('id')} has no check",
                              "A blocker with no observation cannot be verified or "
                              "closed."))
            # Half a finding: the builder is told where to land but not where it stands,
            # and re-measures — differently — what the critic just measured.
            if check and not (f.get("observed") or "").strip():
                flags.append(("NO-DELTA", f"{f.get('id')} has a check but no observed",
                              "Record what you measured, in the check's own units. The "
                              "builder cannot see what you saw."))
            elif first in IMPERATIVES:
                flags.append(("CHECK-AS-DEMAND", f"{f.get('id')}: {check[:60]!r}",
                              "Phrase it as what would be observably true once fixed."))
            # A check that describes the gap without naming its far side. The builder can
            # only guess at the target, and the critic can reject every guess.
            elif (words := {re.sub(r"[^a-z]", "", w.lower()) for w in check.split()}
                  ) & DEVIATIONS and not TARGET_TELLS.search(check):
                worst = sorted(words & DEVIATIONS)[0]
                flags.append(("NO-TARGET", f"{f.get('id')}: {check[:60]!r}",
                              f"'{worst}' says what is wrong, not what right looks like. "
                              "Name the value, threshold or reference — or, if nothing "
                              "fixes it, say the brief is underspecified instead."))
            anchor = f.get("anchor", {})
            if not anchor.get("symbol") and not anchor.get("quote"):
                flags.append(("THIN-ANCHOR", f"{f.get('id')} has only a line hint",
                              "Line numbers move on the first edit; this finding will "
                              "be lost."))

        hist = "  ".join(f"{sev} {counts[sev]}" for sev in
                         ("blocker", "major", "minor", "nit") if counts[sev])
        print(f"{name}   {v.get('verdict', '?')}   round {v.get('round', 1)}")
        print(f"  findings: {hist or 'none'}")
        print(f"  evidence: {len(evidence)}   approved: {len(approved)}")
        # Reported, never flagged: some findings are genuinely judgement, and a critic
        # inventing commands to raise this number would cost more than it saves.
        if blocking:
            mech = sum(1 for f in blocking if (f.get("check_cmd") or "").strip())
            print(f"  mechanised: {mech}/{len(blocking)} blocking finding(s) carry a "
                  "check_cmd")
        for tag, what, why in flags:
            print(f"  [{tag}] {what}\n      {why}")
        total_flags += len(flags)
        print()

    if total_flags:
        print(f"{total_flags} calibration flag(s) across {len(names)} verdict(s).")
        if getattr(args, "strict", False):
            print("STRICT — exiting 1. Read the flagged verdicts in full and repair or\n"
                  "overrule each flag (an overrule goes in the fold report), then re-run.")
            sys.exit(1)
        print("Advisory — read those verdicts yourself before folding on them.\n"
              "The gate is unaffected; it still turns on open blockers and majors.")
    else:
        print(f"No calibration flags across {len(names)} verdict(s).")


def cmd_plan(args) -> None:
    """Validate the allocation plan, then measure coupling between its slices.

    Coupling has four tiers, strongest first. WRITE and DEP are categorical — not
    heuristics but restatements of rules the run already enforces elsewhere. CONTRACT is
    a DEP edge the plan has pinned with a stated contract, which is what lets a coupled
    pair stay split.
    """
    d = run_dir()
    mode = run_meta(d)["mode"]
    plan = load_plan(d, synthesis=False)
    slices = plan["slices"]

    errors, warnings = validate_plan(plan, mode)
    print(f"allocation plan — {mode}, {len(slices)} lane(s)\n")
    for s in slices:
        print(f"  {s.get('id') or '(no id)':<20} {s.get('strategy') or '?':<10} "
              f"{s.get('strategy_reason') or '(no reason)'}")
    if hot := hotspot_paths(plan):
        print(f"  hotspots: {', '.join(hot)}   (no lane owns these; applied at integration)")
    for w in warnings:
        print(f"  warn: {w}")
    for e in errors:
        print(f"  ERROR: {e}")
    print()

    if errors:
        sys.exit("fix the plan before its coupling can be measured")
    if mode == "compete":
        # Competing lanes own the same files on purpose; coupling between them is the
        # point of the mode, not a defect. Isolation is what keeps them apart.
        print("compete mode: lanes share their files by design, so coupling is not measured.\n"
              "Each lane needs its own isolation — worktree, patch or read-only.")
        return
    if len(slices) < 2:
        sys.exit("need at least two slices to measure coupling")

    defs, uses, files = {}, {}, {}
    for s in slices:
        paths = expand(s["owns"])
        if missing := [str(p) for p in paths if not p.exists()]:
            print(f"  note: {s['id']} owns new path(s): {', '.join(missing)}",
                  file=sys.stderr)
        body, defined = [], set()
        for p in paths:
            lines = read_text(p)
            body += lines
            defined |= definitions(lines)
        defs[s["id"]] = defined
        uses[s["id"]] = identifiers(body)
        files[s["id"]] = s["owns"]

    # Vocabulary shared by every slice discriminates nothing; keep the rare names.
    spread = {}
    for names in uses.values():
        for n in names:
            spread[n] = spread.get(n, 0) + 1
    cutoff = max(2, len(slices) // 2)
    rare = {sid: {n for n in names if spread[n] <= cutoff} for sid, names in uses.items()}

    rows, edges = [], []
    for a, b in ((slices[i], slices[j])
                 for i in range(len(slices)) for j in range(i + 1, len(slices))):
        ia, ib = a["id"], b["id"]
        shared_files = overlaps(files[ia], files[ib])

        # A defines it, B calls it: changing A re-opens B. This is not a guess — it is
        # exactly the rule `scope` applies, run before the fact instead of after.
        dep_ab = defs[ia] & uses[ib] - defs[ib]
        dep_ba = defs[ib] & uses[ia] - defs[ia]
        # ...unless the plan pins those symbols with a contract. The provider promises
        # not to move them, so its revisions stop re-opening the consumer.
        loose_ab = dep_ab - contracts_between(plan, ia, ib)
        loose_ba = dep_ba - contracts_between(plan, ib, ia)

        vocab = (rare[ia] & rare[ib]) - defs[ia] - defs[ib]
        floor = min(len(rare[ia]), len(rare[ib])) or 1
        ratio = len(vocab) / floor

        if shared_files:
            tier, detail = "WRITE", f"shared write targets: {', '.join(sorted(shared_files))}"
        elif loose_ab or loose_ba:
            arrows = []
            if loose_ab:
                arrows.append(f"{ia} -> {ib} via {', '.join(sorted(loose_ab)[:4])}")
            if loose_ba:
                arrows.append(f"{ib} -> {ia} via {', '.join(sorted(loose_ba)[:4])}")
            tier, detail = "DEP", "; ".join(arrows)
        elif dep_ab or dep_ba:
            pinned = sorted(dep_ab | dep_ba)
            tier, detail = "CONTRACT", f"pinned by contract: {', '.join(pinned[:4])}"
        elif ratio >= args.threshold:
            shown = sorted(vocab)[:6]
            tier = "VOCAB"
            detail = f"shared rare symbols: {', '.join(shown)}{' ...' if len(vocab) > 6 else ''}"
        else:
            tier, detail = "", f"vocabulary overlap {ratio:.2f}"

        rows.append((tier, ratio, ia, ib, detail))
        if tier in ("WRITE", "DEP", "VOCAB"):
            edges.append((ia, ib))

    order = {"WRITE": 0, "DEP": 1, "CONTRACT": 2, "VOCAB": 3, "": 4}
    rows.sort(key=lambda r: (order[r[0]], -r[1]))

    print(f"coupling across {len(slices)} proposed slices "
          f"(vocabulary threshold {args.threshold:.2f})\n")
    print("  WRITE     same file — violates slice disjointness, merge")
    print("  DEP       one defines what the other calls — revising either re-opens the "
          "other, merge")
    print("  CONTRACT  a DEP edge pinned by provides/consumes — may stay split while the "
          "contract holds")
    print("  VOCAB     shared rare names only — advisory, judge it yourself\n")
    for tier, _, ia, ib, detail in rows:
        if not tier:
            continue
        print(f"  {tier:<9} {ia} <-> {ib}")
        print(f"            {detail}")
    if quiet := [r for r in rows if not r[0]]:
        top = max(quiet, key=lambda r: r[1])
        print(f"  --        {len(quiet)} pair(s) below threshold "
              f"(highest {top[1]:.2f}: {top[2]} <-> {top[3]})")

    # Coupling is transitive here: if A must merge with B and B with C, splitting A
    # from C still cascades re-opens through B.
    group = {s["id"]: s["id"] for s in slices}

    def root(x):
        while group[x] != x:
            group[x] = group[group[x]]
            x = group[x]
        return x

    for ia, ib in edges:
        ra, rb = root(ia), root(ib)
        if ra != rb:
            group[rb] = ra

    clusters = {}
    for s in slices:
        clusters.setdefault(root(s["id"]), []).append(s["id"])

    print(f"\nsuggested grouping — N = {len(clusters)} (proposed {len(slices)}):")
    for members in clusters.values():
        print(f"  {'MERGE  ' if len(members) > 1 else '       '}{' + '.join(members)}")

    if len(clusters) == 1 and len(slices) > 1:
        print("\nEverything collapsed into one group. Either the work is more coupled\n"
              "than the proposed cut admits, or this is not fan-out work at all.")
    elif len(clusters) < len(slices):
        print("\nSplitting a merged pair means two agents rebuilding the same model, and\n"
              "every later revision re-opening the other's approved regions. Merge, or\n"
              "pin the edge with a provides/consumes contract the provider can keep.")
    else:
        print("\nNo coupling above threshold — the cut is clean.")

    # The floor, measured. Only existing files count — a slice that creates its files
    # has no size yet — so a new-code partition can read small here and not be.
    existing = [p for s in slices for p in expand(s["owns"]) if p.exists()]
    total_lines = sum(len(read_text(p)) for p in existing)
    if existing and total_lines < 100:
        print(f"\nFLOOR — the slices touch {total_lines} existing line(s) in total. That is\n"
              "less than the brief each agent would read. Stop here and do the task\n"
              "directly, unless most of the work is new files this count cannot see.")


def ignored_hint() -> list:
    """Ignored paths present in the main tree — what a fresh worktree will lack."""
    out = git("ls-files", "--others", "--ignored", "--exclude-standard", "--directory",
              check=False)
    return sorted(p.rstrip("/") for p in git_paths(out)
                  if not p.startswith(ROOT.name + "/"))


def add_worktree(d: Path, path: Path, base: str, branch: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if branch:
        exists = git("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}",
                     check=False).strip()
        if exists:
            git("worktree", "add", str(path), branch)
        else:
            git("worktree", "add", "-b", branch, str(path), base)
    else:
        git("worktree", "add", "--detach", str(path), base)


def apply_patch(text: str, cwd: Path, check_only: bool = False, reverse: bool = False):
    """git apply in `cwd`; returns (ok, stderr)."""
    cmd = ["git", "apply", "--binary"]
    if check_only:
        cmd.append("--check")
    if reverse:
        cmd.append("-R")
    res = subprocess.run(cmd, cwd=cwd, input=text, capture_output=True, text=True)
    return res.returncode == 0, res.stderr.strip()


def cmd_lane(args) -> None:
    """Set up (or tear down) the isolation a lane's strategy calls for."""
    d = run_dir()
    plan = load_plan(d)
    base = base_of(d)
    targets = [slice_spec(plan, args.slice)] if args.slice else plan["slices"]

    for spec in targets:
        sid, strategy = spec["id"], spec["strategy"]
        if args.remove:
            for path in (lane_dir(d, sid), applied_dir(d, sid)):
                if path.exists():
                    git("worktree", "remove", "--force", str(path))
                    print(f"{sid}: removed {path}")
            branch = f"fanout/{d.name}/{sid}"
            if git("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}",
                   check=False).strip():
                git("branch", "-D", branch)
                print(f"{sid}: deleted branch {branch}")
            continue

        if args.materialize:
            if strategy != "patch":
                sys.exit(f"{sid}: --materialize is for patch lanes; this one is {strategy}")
            text = lane_patch(d, spec)
            path = applied_dir(d, sid)
            if path.exists():
                git("worktree", "remove", "--force", str(path))
            add_worktree(d, path, base)
            ok, err = apply_patch(text, path)
            if not ok:
                git("worktree", "remove", "--force", str(path))
                sys.exit(f"{sid}: the patch does not apply to the base commit:\n{err}\n"
                         "That is a failed candidate, not a merge problem — send it back.")
            print(f"{sid}: patch applied in {path}")
            print("  Disposable: critics and deciders read and run here; the patch stays "
                  "the candidate.\n  Materialize again after every new patch.")
            continue

        if strategy == "worktree":
            path = lane_dir(d, sid)
            if path.exists():
                print(f"{sid}: worktree already at {path}")
                continue
            branch = f"fanout/{d.name}/{sid}"
            add_worktree(d, path, base, branch)
            print(f"{sid}: worktree {path}  (branch {branch}, from {base[:12]})")
            if src := spec.get("from"):
                # A synthesis lane starts from the winner's tree, not from the base.
                ok, err = apply_patch(lane_patch(d, slice_spec(plan, src)), path)
                if not ok:
                    sys.exit(f"{sid}: could not start from {src}:\n{err}")
                print(f"  started from {src}'s change")
        elif strategy == "patch":
            patch_file(d, sid).parent.mkdir(parents=True, exist_ok=True)
            print(f"{sid}: patch lane — the builder writes {patch_file(d, sid)}; the "
                  "repository stays untouched")
        else:
            print(f"{sid}: {strategy} — works in the main tree, nothing to set up")

    if not args.remove and not args.materialize and any(
            s["strategy"] in ("worktree",) for s in targets):
        if hint := ignored_hint():
            shown = ", ".join(hint[:8]) + (" ..." if len(hint) > 8 else "")
            print(f"\nNot in any worktree (ignored in the main tree): {shown}")
            print("Install or copy what a lane's build and render recipe need before you "
                  "spawn its builder.")


STRATEGY_TEXT = {
    "worktree": (
        "Your working directory is {root}, a git worktree of your own. Every path below "
        "is relative to it. Write nothing in the main tree except your candidate and "
        "renders in the run directory. Build and test here; nobody else writes this tree."
    ),
    "patch": (
        "Do not modify the repository. Deliver your change as one unified diff in git "
        "format — a/ and b/ prefixes, paths relative to the repository root — at {patch}. "
        "It must apply with `git apply` to commit {base}. Work in a scratch copy outside "
        "the repository if you need one."
    ),
    "shared": (
        "You work in the main tree, which other lanes are writing at the same time. Write "
        "only the paths under Scope. Run nothing that writes shared state — installs, "
        "whole-tree builds or formatters, lockfile updates — without saying so in your "
        "report first."
    ),
    "read-only": (
        "Do not modify any file in the repository. Your only output is your candidate "
        "in the run directory."
    ),
}


def lane_block(d: Path, plan: dict, spec: dict, mode: str) -> list:
    sid, strategy = spec["id"], spec["strategy"]
    info = seal_info(d)
    root = lane_dir(d, sid) if strategy == "worktree" else Path(".")
    out = [f"YOUR SLICE: {sid} — {spec['summary']}"]

    def listing(title, items):
        if items:
            out.extend(["", title] + [f"  - {x}" for x in items])

    def text(title, body):
        if body.strip():
            out.extend(["", title] + [f"  {line}".rstrip() for line in body.strip().splitlines()])

    text("Task:", spec["task"])
    text("Context:", spec["context"])
    out.extend(["", f"Isolation: {strategy}. " + STRATEGY_TEXT[strategy].format(
        root=root.resolve(), patch=patch_file(d, sid).resolve(),
        base=(info.get("base") or "?")[:12])])

    if strategy != "read-only":
        listing("Scope — you may write:", spec["owns"])
    listing("Read for context — do not write:", spec["reads"])
    others = []
    if mode == "partition":
        others = [f"{e} (owned by {o['id']})" for o in plan["slices"]
                  if o is not spec and not o.get("synthesis") for e in o["owns"]]
    listing("Out of scope — do not do, and do not write:", spec["out_of_scope"] + others)
    listing("Hotspots — no lane writes these; list what you need under "
            "'Hotspot entries' in your report:", hotspot_paths(plan))
    listing("Must not:", spec["must_not"])
    listing("You provide — others build against this; do not change it:",
            [f"{p['symbol']}: {p['contract']}" for p in spec["provides"]])
    consumed = []
    for c in spec["consumes"]:
        provider = slice_spec(plan, c["from"])
        contract = next((p["contract"] for p in provider["provides"]
                         if p.get("symbol") == c["symbol"]), "?")
        consumed.append(f"{c['symbol']} from {c['from']}: {contract}")
    listing("You consume — build against this contract, not the code you find today "
            "(it is being changed in parallel):", consumed)
    listing("Done when:", spec["done_when"])
    if spec.get("from"):
        out.extend(["", f"You start from {spec['from']}'s change, already in your tree."])
    return out


FIX_ONLY = (
    "Fix only these findings. If a fix requires changing something outside them, say so "
    "in your report instead of doing it silently — an unexplained out-of-scope edit "
    "re-opens everything it touches. A finding's own `sites` are part of that finding — "
    "fix all of them, and that is not an out-of-scope edit. Where a finding carries a "
    "`remedy`, it is one route and not the target: satisfy the `check` your own way if "
    "you have a better one, and say in your report why."
)


def findings_block(d: Path, slice_id: str) -> list:
    """Open blocking findings for the lane — its own, plus seam findings it owns."""
    items = []
    for name in (slice_id, INTEGRATION):
        p = d / "verdicts" / f"{name}.json"
        if not p.exists():
            continue
        for f in json.loads(p.read_text()).get("findings", []):
            if name == INTEGRATION and f.get("owner") != slice_id:
                continue
            if f.get("severity") in BLOCKING and f.get("status", "open") in UNRESOLVED:
                items.append(f)
    if not items:
        return ["", "No open blocking findings."]
    out = ["", FIX_ONLY, ""]
    for f in items:
        anchor = f.get("anchor", {})
        where = " / ".join(str(x) for x in (anchor.get("file"), anchor.get("symbol"))
                           if x) or "?"
        out.append(f"[{f.get('severity')}] {f.get('id')}  at {where}")
        if quote := anchor.get("quote"):
            out.append(f"    quote:    {quote}")
        out.append(f"    claim:    {f.get('claim', '')}")
        if observed := f.get("observed"):
            out.append(f"    observed: {observed}")
        out.append(f"    check:    {f.get('check', '')}")
        if sites := f.get("sites"):
            out.append(f"    sites:    {', '.join(str(s) for s in sites)}")
        if remedy := f.get("remedy"):
            out.append(f"    remedy:   {remedy}   (non-binding)")
    return out


def cmd_delta(args) -> None:
    """Print the per-agent block — everything below the '---' — for one lane."""
    d = run_dir()
    plan = load_plan(d)
    spec = slice_spec(plan, args.slice)
    lines = ["---"] + lane_block(d, plan, spec, run_meta(d)["mode"])
    if args.findings:
        lines += findings_block(d, args.slice)
    print("\n".join(lines))


def cmd_trespass(args) -> None:
    """Did a lane write outside what it owns? Exit 1 if any did."""
    d = run_dir()
    plan = load_plan(d)
    targets = [slice_spec(plan, args.slice)] if args.slice else plan["slices"]
    bad = 0
    tree_done = False

    for spec in targets:
        sid = spec["id"]
        if spec["strategy"] in ("worktree", "patch"):
            found = trespass_of(d, plan, spec)
            if found is None:
                print(f"{sid}: nothing produced yet")
                continue
        else:
            # One tree, several writers: ownership is the only attribution there is.
            if tree_done:
                continue
            tree_done = True
            writers = [s["id"] for s in plan["slices"]
                       if s["strategy"] in ("shared", "read-only")]
            sid = f"main tree ({', '.join(writers)})"
            found = tree_trespass(d, plan)
        if not found:
            print(f"{sid}: clean")
            continue
        bad += len(found)
        print(f"{sid}: {len(found)} write(s) outside scope")
        for path, why in found:
            print(f"    {path}   {why}")

    if bad:
        print("\nA trespassing lane goes back to its builder before any critic sees it:\n"
              "revert the listed writes, or justify each in the report and let the\n"
              "orchestrator decide. A write to another lane's file is a slicing error\n"
              "when it was needed — merge the lanes next run rather than resolving it here.")
        sys.exit(1)


def cmd_integrate(args) -> None:
    """Land the gated lanes in the main tree, providers first. Nothing is committed."""
    d = run_dir()
    mode = run_meta(d)["mode"]
    plan = load_plan(d)
    applied = load_applied(d)
    idir = d / "integration"

    if args.revert:
        if not applied:
            sys.exit("nothing integrated — nothing to revert")
        for entry in reversed(applied):
            text = (idir / f"{entry['id']}.patch").read_text()
            ok, err = apply_patch(text, Path("."), reverse=True)
            if not ok:
                sys.exit(f"could not revert {entry['id']}:\n{err}\n"
                         "Something edited those files after integration; revert by hand.")
            print(f"reverted {entry['id']}")
        (idir / "applied.json").unlink()
        print("\nMain tree is back to its pre-integration state. Shared lanes were never\n"
              "applied, so they are untouched.")
        return

    if applied:
        sys.exit(f"already integrated: {', '.join(e['id'] for e in applied)}.\n"
                 "Run `fanout.py integrate --revert` first, then integrate again.")

    if mode == "compete":
        if not args.winner:
            sys.exit("compete mode lands one lane: pass --winner <slice-id> (the winner, "
                     "or the synthesis lane)")
        chosen = [slice_spec(plan, args.winner)]
    else:
        if args.winner:
            sys.exit("--winner is for compete mode; partition integrates every gated lane")
        chosen = [slice_spec(plan, sid) for sid in order_lanes(plan["slices"])]

    landing, skipped = [], []
    for spec in chosen:
        sid = spec["id"]
        if spec["strategy"] == "read-only":
            continue
        state = gate_state(d, sid)
        if state != "pass" and not args.force:
            skipped.append((sid, state))
            continue
        landing.append(spec)

    for sid, state in skipped:
        print(f"skip {sid}: gate is '{state}' (--force lands it anyway, and the fold says so)")
        if slice_spec(plan, sid)["strategy"] == "shared":
            print(f"     {sid} is shared: its writes are in the main tree whether or not it "
                  "lands.\n     Revert its owned paths by hand, or fix it, before the fold.")
    if not landing:
        sys.exit("no lane passed its gate — nothing to integrate")

    # Scope before merge: a conflict between disjoint lanes can only be a trespass, and
    # it is the lane's to fix, never the integrator's to resolve by hand.
    stop = []
    for spec in landing:
        if spec["strategy"] in ("worktree", "patch"):
            stop += [(spec["id"], p, w) for p, w in (trespass_of(d, plan, spec) or [])]
    if any(s["strategy"] == "shared" for s in landing):
        stop += [("main tree", p, w) for p, w in tree_trespass(d, plan)]
    if stop:
        for sid, path, why in stop:
            print(f"TRESPASS {sid}: {path}   {why}")
        sys.exit("\nSend these back to their lanes (`fanout.py trespass` for detail).")

    patches = {}
    for spec in landing:
        if spec["strategy"] in ("worktree", "patch"):
            text = lane_patch(d, spec)
            if not text.strip():
                print(f"note {spec['id']}: empty change")
                continue
            ok, err = apply_patch(text, Path("."), check_only=True)
            if not ok:
                sys.exit(f"{spec['id']} does not apply to the main tree:\n{err}\n"
                         "Between disjoint lanes that means the main tree moved under it "
                         "or the lane trespassed. Send it back; do not hand-merge.")
            patches[spec["id"]] = text

    print("integration order: " + " -> ".join(s["id"] for s in landing))
    if args.check:
        print("\n--check: every lane applies. Nothing was changed.")
        return

    idir.mkdir(exist_ok=True)
    record = []
    for spec in landing:
        sid = spec["id"]
        if sid not in patches:
            if spec["strategy"] == "shared":
                print(f"  {sid:<20} shared — already in place")
            continue
        (idir / f"{sid}.patch").write_text(patches[sid])
        ok, err = apply_patch(patches[sid], Path("."))
        if not ok:
            (idir / "applied.json").write_text(json.dumps(record, indent=2) + "\n")
            sys.exit(f"{sid} failed to apply after its check passed:\n{err}\n"
                     "The lanes before it are applied and recorded; "
                     "`fanout.py integrate --revert` undoes them.")
        paths = sorted(patch_paths(patches[sid]))
        record.append({"id": sid, "strategy": spec["strategy"], "paths": paths})
        print(f"  {sid:<20} {spec['strategy']:<9} applied ({len(paths)} path(s))")
    (idir / "applied.json").write_text(json.dumps(record, indent=2) + "\n")

    requests = []
    for spec in landing:
        cand = d / "candidates" / f"{spec['id']}.md"
        if cand.exists() and (body := section(cand.read_text(errors="replace"),
                                              "Hotspot entries")):
            requests.append((spec["id"], body))
    if requests:
        print("\nHotspot entries requested — apply these yourself, mechanically:")
        for sid, body in requests:
            print(f"\n  [{sid}]")
            print("\n".join(f"    {line}" for line in body.splitlines()))

    seams = [(p["symbol"], s["id"], c["id"], p["contract"])
             for s in landing for p in s["provides"]
             for c in landing if any(x.get("from") == s["id"] and
                                     x.get("symbol") == p["symbol"] for x in c["consumes"])]
    if seams:
        print("\nSeams to verify — each contract is a check for the integration critic:")
        for sym, prov, cons, contract in seams:
            print(f"  {sym}: {prov} -> {cons}   {contract}")

    print("\nNext: run the full oracles (build, whole test suite) on the main tree, render\n"
          "the merged result if there is a visual surface, then spawn the integration\n"
          f"critic. Its verdict goes to verdicts/{INTEGRATION}.json; each seam finding names\n"
          "its `owner` lane. Nothing is committed — that stays the user's call.")


def cmd_status(args) -> None:
    d = run_dir()
    meta = json.loads((d / "run.json").read_text())
    cands = sorted(p.stem for p in (d / "candidates").glob("*") if p.is_file())
    verds = sorted(p.stem for p in (d / "verdicts").glob("*.json"))

    print(f"run:    {d}")
    print(f"task:   {meta['task']}")
    print(f"mode:   {meta['mode']}   expected: {meta['n']}")
    print(f"sealed: {'yes' if (d / 'seal.json').exists() else 'NO'}")

    if (d / "slices.json").exists():
        try:
            plan = load_plan(d)
        except SystemExit:
            plan = None
        if plan:
            applied = {e["id"] for e in load_applied(d)}
            print(f"\nlanes ({len(plan['slices'])}):")
            for s in plan["slices"]:
                sid, strategy = s.get("id") or "?", s.get("strategy") or "?"
                if strategy == "worktree":
                    where = "worktree ready" if lane_dir(d, sid).exists() else "no worktree"
                elif strategy == "patch":
                    where = "patch written" if patch_file(d, sid).exists() else "no patch"
                else:
                    where = "main tree"
                landed = "  integrated" if sid in applied else ""
                print(f"  {sid:<20} {strategy:<10} {where}{landed}")

    print(f"\ncandidates ({len(cands)}): {', '.join(cands) or '-'}")
    print(f"verdicts   ({len(verds)}): {', '.join(verds) or '-'}")

    # Renders are reported only once some slice has one: a run with no visual surface
    # should not be nagged about pictures it was never supposed to produce.
    rendered = {}
    for slice_dir in sorted((d / "renders").glob("*")):
        rounds = sorted(p.name for p in slice_dir.glob("r*") if p.is_dir())
        if rounds:
            rendered[slice_dir.name] = rounds
    if rendered:
        print("renders:    " + "  ".join(
            f"{name}({','.join(rounds)})" for name, rounds in rendered.items()))
        if unrendered := [c for c in cands if c not in rendered]:
            print(f"  no render: {', '.join(unrendered)}"
                  "   — critics judge the render; produce it before spawning them")

    if missing := [c for c in cands if c not in verds]:
        print(f"\nawaiting critique: {', '.join(missing)}")

    if verds:
        print("\nverdicts:")
        for name in verds:
            try:
                v = json.loads((d / "verdicts" / f"{name}.json").read_text())
            except (json.JSONDecodeError, OSError):
                print(f"  {name:<20} unreadable")
                continue
            findings = v.get("findings", [])
            blocking = sum(1 for f in findings
                           if f.get("severity") in BLOCKING
                           and f.get("status", "open") in UNRESOLVED)
            revs = len(revisions(d, name))
            print(f"  {name:<20} {v.get('verdict', '?'):<8} "
                  f"round {v.get('round', 1)}  "
                  f"blocking {blocking}/{len(findings)}  snapshots {revs}")


# ---------------------------------------------------------------- cli

def main() -> None:
    p = argparse.ArgumentParser(prog="fanout.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("init", help="create a run directory")
    i.add_argument("task")
    i.add_argument("--mode", choices=["partition", "compete"], default="compete")
    i.add_argument("--n", type=int, default=4,
                   help="expected slice count — a hint; `plan` determines the real one")
    i.add_argument("--max-rounds", type=int, default=MAX_ROUNDS,
                   help="verification rounds before escalating (default 2)")
    i.set_defaults(func=cmd_init)

    pl = sub.add_parser("plan", help="validate the allocation plan, measure coupling")
    pl.add_argument("--threshold", type=float, default=0.35,
                    help="merge slices coupled at or above this (default 0.35)")
    pl.set_defaults(func=cmd_plan)

    ln = sub.add_parser("lane", help="set up the isolation a lane's strategy calls for")
    ln.add_argument("slice", nargs="?", help="omit to set up every lane")
    ln.add_argument("--materialize", action="store_true",
                    help="patch lanes: apply the patch in a disposable worktree")
    ln.add_argument("--remove", action="store_true",
                    help="remove the lane's worktrees and branch (discards its work)")
    ln.set_defaults(func=cmd_lane)

    dl = sub.add_parser("delta", help="the per-agent block below the '---'")
    dl.add_argument("slice")
    dl.add_argument("--findings", action="store_true",
                    help="append the lane's open blocking findings, for a fix round")
    dl.set_defaults(func=cmd_delta)

    tp = sub.add_parser("trespass", help="writes outside what a lane owns")
    tp.add_argument("slice", nargs="?", help="omit to check every lane")
    tp.set_defaults(func=cmd_trespass)

    ig = sub.add_parser("integrate", help="land the gated lanes in the main tree")
    ig.add_argument("--winner", help="compete mode: the one lane to land")
    ig.add_argument("--check", action="store_true", help="verify every lane applies; change nothing")
    ig.add_argument("--revert", action="store_true", help="undo the last integration")
    ig.add_argument("--force", action="store_true", help="land lanes whose gate has not passed")
    ig.set_defaults(func=cmd_integrate)

    s = sub.add_parser("snapshot", help="record the bytes under review")
    s.add_argument("slice")
    s.add_argument("paths", nargs="+")
    s.set_defaults(func=cmd_snapshot)

    c = sub.add_parser("calibration", help="lint the critique itself (advisory)")
    c.add_argument("slice", nargs="?", help="omit to lint every verdict in the run")
    c.add_argument("--strict", action="store_true", help="exit non-zero if critical flags are found")
    c.set_defaults(func=cmd_calibration)

    for name, fn, helptext, needs_slice in (
        ("seal", cmd_seal, "hash brief + rubric + plan, record the base commit", False),
        ("check", cmd_check, "fail if the shared block drifted", False),
        ("scope", cmd_scope, "in-scope / re-opened / out-of-scope", True),
        ("deciders", cmd_deciders, "mechanical deciders for the open findings", True),
        ("gate", cmd_gate, "stop condition for a slice", True),
        ("followups", cmd_followups, "drain deferred/late/waived findings to a file", False),
        ("status", cmd_status, "candidates, verdicts, open findings", False),
    ):
        sp = sub.add_parser(name, help=helptext)
        if needs_slice:
            sp.add_argument("slice")
        if name == "deciders":
            sp.add_argument("--run", action="store_true",
                            help="execute the deciders in the lane's tree (read them first)")
        sp.set_defaults(func=fn)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    # Agents pipe this output; a truncated pipe is not an error.
    try:
        main()
    except BrokenPipeError:
        try:
            sys.stdout.close()
        finally:
            sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(130)
