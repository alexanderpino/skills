#!/usr/bin/env python3
"""Validation stage: run this whenever you believe the work is done — before you say so.

    validate.py TARGET                  # checks for the stopping point the run is at
    validate.py TARGET --json           # same, machine-readable
    validate.py TARGET --changes        # what changed since the last reported stop: the critic's target
    validate.py TARGET --mark-reported  # after you told the user: this state becomes the new baseline

It decides the stopping point from `TARGET/.ssb/state.json`:

  proposal   the proposal is not approved yet: the run is about to stop for approval
  generated   the proposal is approved and studio files exist: the run is about to hand over

and runs every check for that stop, then reads the two independent reviews
(see references/validation.md):

  .ssb/refutation.md  the refutation critic: tried to prove each CHANGE wrong (V91)
  .ssb/validation.md  the validator: traced every item of the REQUEST to evidence (V90)

A review must be newer than everything it reviewed; a review older than the latest change is
stale and does not count. The refutation must also name every changed path (or a folder
containing it): a change nobody tried to refute has not survived anything.

Output: one `V<id> <PASS|CONCERNS|FAIL|NOT ASSESSED> — <what>` line per check with its
evidence, then

    VALIDATE <stop>: FAIL | NOT ASSESSED | CONCERNS | PASS

ranked in that order: a known failure first, then anything that could not be checked, then
weak spots, then a pass. The result is also written to `TARGET/.ssb/validation.json`.
Exit codes: 0 PASS or CONCERNS, 1 FAIL, 3 NOT ASSESSED.

"Done" is a claim this script exists to test. A run may tell the user it is finished only
after it has run this script and quoted its VALIDATE line.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import proposal as proposalmod  # noqa: E402
import ledger  # noqa: E402
import state as statemod  # noqa: E402

RANK = {"FAIL": 3, "NOT ASSESSED": 2, "CONCERNS": 1, "PASS": 0}
STUDIO_MARKERS = (".claude", "CLAUDE.md", "project.yaml", "studio-tests")


class Run:
    def __init__(self):
        self.rows: list[dict] = []

    def add(self, vid, status, what, evidence=None):
        self.rows.append({"id": vid, "status": status, "what": what, "evidence": evidence or []})

    def verdict(self):
        if not self.rows:
            return "NOT ASSESSED"
        return max((r["status"] for r in self.rows), key=RANK.get)


def _read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


SKIP_DIRS = {"__pycache__", ".git", "node_modules"}
SKIP_FILES = {"validation.md", "validation.json", "refutation.md", "baseline.json", "trial.md",
              "final-message.md", ".lock"}
ACCEPTANCE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references", "acceptance.md")


def snapshot(target: str) -> dict:
    """sha256 of every file the run produced, except the validation records themselves."""
    import hashlib
    out = {}
    for base, dirs, files in os.walk(target):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for f in sorted(files):
            if f in SKIP_FILES or f.endswith(".pyc"):
                continue
            p = os.path.join(base, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, target)] = hashlib.sha256(fh.read()).hexdigest()
    return out


def changes(target: str, rd: str) -> tuple[dict, bool]:
    """{path: added|modified|removed} since the baseline; second value says whether a baseline existed."""
    bp = os.path.join(rd, "baseline.json")
    base = {}
    had = os.path.exists(bp)
    if had:
        base = json.loads(_read(bp)).get("files", {})
    cur = snapshot(target)
    out = {}
    for k, h in cur.items():
        if k not in base:
            out[k] = "added"
        elif base[k] != h:
            out[k] = "modified"
    for k in base:
        if k not in cur:
            out[k] = "removed"
    return out, had


def mtime(p):
    try:
        return os.path.getmtime(p)
    except OSError:
        return 0.0


def latest_mtime(paths):
    return max([mtime(p) for p in paths] + [0.0])


def sh(args, cwd=None, env=None):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, cwd=cwd,
                          env={**os.environ, **(env or {})})


def last_verdict(text, prefix="VERDICT:"):
    m = re.findall(rf"^{re.escape(prefix)}\s*([A-Z ]+?)(?:\s{{2,}}|\s*\(|$)", text, re.M)
    return m[-1].strip() if m else None


# ------------------------------------------------------------------ shared checks

def v_state(run, rd):
    try:
        st = statemod.load(rd)
    except (OSError, ValueError) as e:
        run.add("V01", "NOT ASSESSED", "run state is readable", [f"{rd}/state.json: {e}"])
        return None
    ev = [f"phase={st.get('phase')}", f"layers={','.join(st.get('layers', [])) or 'none'}"]
    if not st.get("intake"):
        run.add("V01", "CONCERNS", "run state records the intake answers", ev + ["intake is empty: the answers "
                "(or the defaults taken for an absent user) are not on record"])
    else:
        run.add("V01", "PASS", "run state records the intake answers", ev + [f"intake keys: {', '.join(st['intake'])}"])
    return st


def acceptance_ids(prefix: str) -> list[str]:
    """The criterion ids for a stop (P… or G…), read from references/acceptance.md — derived, not listed here."""
    try:
        return re.findall(rf"^\|\s*({prefix}\d+)\s*\|", _read(ACCEPTANCE), re.M)
    except OSError:
        return []


def v_review(run, rd, reviewed_paths, prefix=""):
    """The independent review (validation.md) must exist, carry a verdict, and be newer than its inputs."""
    p = os.path.join(rd, "validation.md")
    if not os.path.exists(p):
        run.add("V90", "NOT ASSESSED", "independent review of the result against the user's request",
                ["no .ssb/validation.md — run the validator (references/validation.md) after the mechanical checks"])
        return
    text = _read(p)
    v = last_verdict(text, "VALIDATION:")
    newest = latest_mtime(reviewed_paths)
    ev = [f"verdict line: {v or 'missing'}"]
    if re.search(r"^independent:\s*no\b", text, re.M | re.I):
        ev.append("the review says it was NOT independent (no subagent available)")
    unmet = re.findall(r"^\|[^|\n]+\|[^|\n]*\|\s*(Not met|Not assessed)\s*\|", text, re.M | re.I)
    if unmet:
        ev.append(f"request items not met / not assessed: {len(unmet)}")
    if mtime(p) < newest:
        run.add("V90", "NOT ASSESSED", "independent review is current", ev + ["validation.md is older than the "
                "files it reviews — something changed after the review; run the validator again"])
        return
    if v not in RANK:
        run.add("V90", "NOT ASSESSED", "independent review carries a verdict", ev + ["expected a line "
                "`VALIDATION: PASS|CONCERNS|FAIL|NOT ASSESSED`"])
        return
    if prefix:
        ids = acceptance_ids(prefix)
        if not ids:
            run.add("V90", "NOT ASSESSED", "acceptance criteria for this stop", ev + [f"no {prefix}-ids found in "
                    f"{ACCEPTANCE}"])
            return
        missing = [i for i in ids if not re.search(rf"^\|\s*{i}\s*\|", text, re.M)]
        ev.append(f"acceptance criteria covered: {len(ids) - len(missing)}/{len(ids)}")
        if missing:
            run.add("V90", "NOT ASSESSED", "independent review covers every acceptance criterion of this stop",
                    ev + [f"no row for: {', '.join(missing)} (references/acceptance.md)"])
            return
    if v == "PASS" and "NOT independent" in " ".join(ev):
        v = "CONCERNS"
        ev.append("a self-review is capped at CONCERNS")
    run.add("V90", v, "independent review of the result against the user's request and the stop's criteria", ev)


# "12 agents", "10 skills" — a number directly before the noun. "4 baseline skills" is a part, not a total,
# so a qualifier in between is deliberately not matched.
COUNT_RE = re.compile(r"\b(\d+)\s+(agents?|roles?|skills?|rules?|gates?)\b", re.I)


def v_message(run, target, rd, stop, counts: dict, reviewed_paths):
    """V92: the draft final message says nothing the files contradict."""
    p = os.path.join(rd, "final-message.md")
    if not os.path.exists(p):
        run.add("V92", "NOT ASSESSED", "the final message matches the files",
                ["no .ssb/final-message.md — draft the message to the user there before the reviewers run"])
        return
    text = _read(p)
    if mtime(p) < latest_mtime(reviewed_paths):
        run.add("V92", "NOT ASSESSED", "the final message is current", ["final-message.md is older than the files it "
                "describes — redraft it"])
        return
    probs, ev = [], []
    for m in COUNT_RE.finditer(text):
        n, noun = int(m.group(1)), m.group(2).lower().rstrip("s")
        allowed = counts.get(noun)
        if allowed is None:
            continue
        if n not in allowed:
            probs.append(f"says '{m.group(0)}', the files give {' or '.join(str(x) for x in sorted(allowed))}")
        else:
            ev.append(f"'{m.group(0)}' matches")
    if re.search(r"nothing (?:was |has been )?generated", text, re.I):
        early = [m for m in STUDIO_MARKERS if os.path.exists(os.path.join(target, m))]
        if early:
            probs.append(f"says nothing was generated, but {', '.join(early)} exist")
        else:
            ev.append("'nothing generated' matches")
    vp = os.path.join(rd, "validation.md")
    m_rows = len(re.findall(r"^\|\s*M\d+\s*\|", _read(vp), re.M)) if os.path.exists(vp) else 0
    if probs:
        run.add("V92", "FAIL", "the final message matches the files", probs + ev)
    elif not m_rows:
        run.add("V92", "NOT ASSESSED", "the validator checked the final message's claims",
                ev + ["validation.md has no M rows (one per factual claim in final-message.md)"])
    else:
        run.add("V92", "PASS", "the final message matches the files", ev + [f"{m_rows} message claims checked by the "
                "validator"])


def v_trial(run, target, rd):
    """V26: the picked agents and skill were tried, and behaved as their files promise."""
    try:
        import trial as trialmod
        picks = trialmod.pick(target)
    except Exception as e:  # noqa: BLE001
        run.add("V26", "NOT ASSESSED", "trial run of the studio", [f"could not pick: {e.__class__.__name__}: {e}"])
        return
    if not picks:
        run.add("V26", "NOT ASSESSED", "trial run of the studio", ["nothing to trial (trial.py pick is empty)"])
        return
    p = os.path.join(rd, "trial.md")
    if not os.path.exists(p):
        run.add("V26", "NOT ASSESSED", "trial run of the studio",
                [f"no .ssb/trial.md — run the briefs from `trial.py brief` ({len(picks)} picks)"])
        return
    text = _read(p)
    newest = latest_mtime([os.path.join(target, x["path"]) for x in picks])
    if mtime(p) < newest:
        run.add("V26", "NOT ASSESSED", "trial run is current", ["trial.md is older than a file it tried — run again"])
        return
    rows = re.findall(r"^\|\s*T\d+\s*\|(.*)$", text, re.M)
    ev = [f"{len(rows)} trial rows"]
    missing = [x["path"] for x in picks if not any(f"`{x['path']}`" in r for r in rows)]
    fails = [r for r in rows if re.search(r"\|\s*Fail\s*\|", r, re.I)]
    untested = [r for r in rows if re.search(r"\|\s*Could not test\s*\|", r, re.I)]
    if fails:
        run.add("V26", "FAIL", "trial run: a picked file did not behave as it promises",
                ev + [f"Fail: {r.strip()[:140]}" for r in fails])
        return
    if missing:
        run.add("V26", "NOT ASSESSED", "trial run covers every pick",
                ev + [f"not tried: {', '.join(missing)} (from `trial.py pick`)"])
        return
    status = "PASS"
    if untested:
        status = "CONCERNS"
        ev.append(f"could not test: {len(untested)}")
    if re.search(r"^independent:\s*no\b", text, re.M | re.I):
        status = "CONCERNS"
        ev.append("trials were run by the same session (independent: no) — capped at CONCERNS")
    run.add("V26", status, "trial run: the picked agents and skill behave as their files promise", ev)


def v_refutation(run, target, rd):
    """The refutation critic must have attacked every changed path, after the last change."""
    ch, had_base = changes(target, rd)
    p = os.path.join(rd, "refutation.md")
    scope = [f"{len(ch)} changed paths since {'the last reported stop' if had_base else 'the start of the run'}"]
    if not ch:
        run.add("V91", "PASS", "refutation critic: nothing changed since the last reported stop", scope)
        return
    if not os.path.exists(p):
        run.add("V91", "NOT ASSESSED", "refutation critic tried to prove the changes wrong",
                scope + ["no .ssb/refutation.md — run the critic on `validate.py T --changes`"])
        return
    text = _read(p)
    ev = list(scope)
    newest = latest_mtime([os.path.join(target, k) for k, v in ch.items() if v != "removed"])
    if mtime(p) < newest:
        run.add("V91", "NOT ASSESSED", "refutation is current", ev + ["refutation.md is older than a change "
                "it should cover — run the critic again"])
        return
    named = set(re.findall(r"`([^`\n]+?)/?`", text))
    uncovered = []
    for k in ch:
        parts = k.split(os.sep)
        # a file is covered when the critic names it, or a folder of it at least two levels deep
        # (`.claude/agents/`), in backticks; a bare top-level folder (`.claude`) covers nothing
        lo = 1 if len(parts) == 1 else 2
        prefixes = {"/".join(parts[:i]) for i in range(lo, len(parts) + 1)}
        if not prefixes & named:
            uncovered.append(k)
    v = last_verdict(text, "REFUTATION:")
    mapping = {"REFUTED": "FAIL", "CONCERNS": "CONCERNS", "SURVIVED": "PASS", "NOT ASSESSED": "NOT ASSESSED"}
    refuted = len(re.findall(r"\|\s*Refuted\s*\|", text, re.I))
    untested = len(re.findall(r"\|\s*Could not test\s*\|", text, re.I))
    ev += [f"verdict line: {v or 'missing'}", f"attempts that refuted a change: {refuted}",
           f"attempts that could not test: {untested}"]
    if re.search(r"^independent:\s*no\b", text, re.M | re.I):
        ev.append("the critic was NOT independent (no subagent available)")
    if v not in mapping:
        run.add("V91", "NOT ASSESSED", "refutation carries a verdict",
                ev + ["expected `REFUTATION: REFUTED|CONCERNS|SURVIVED|NOT ASSESSED`"])
        return
    status = mapping[v]
    if refuted and status != "FAIL":
        status = "FAIL"
        ev.append("a row says Refuted, so the verdict cannot be better than REFUTED")
    if uncovered:
        status = max(status, "NOT ASSESSED", key=RANK.get)
        ev.append(f"changed paths nobody tried to refute ({len(uncovered)}): " + ", ".join(uncovered[:8])
                  + (" …" if len(uncovered) > 8 else ""))
    if untested and status == "PASS":
        status = "CONCERNS"
    if "NOT independent" in " ".join(ev) and status == "PASS":
        status = "CONCERNS"
        ev.append("a self-critique is capped at CONCERNS")
    run.add("V91", status, "refutation critic tried to prove each change wrong", ev)


# ------------------------------------------------------------------ stop 1: proposal

def validate_proposal(run, target, rd):
    res = os.path.join(rd, "research")
    verdict, obs = ledger.check(res)
    run.add("V10", {"PASS": "PASS", "CONCERNS": "CONCERNS", "FAIL": "FAIL"}.get(verdict, "NOT ASSESSED"),
            "research ledger chains claim → quote → source", obs[:6] + obs[6:][:10])
    rp = os.path.join(res, "report.md")
    if not os.path.exists(rp):
        run.add("V11", "FAIL", "research report exists and cites the ledger", [f"missing {rp}"])
    else:
        cited = set(re.findall(r"\bC\d{3,}\b", _read(rp)))
        known = {c["claim_id"] for c in ledger.rows(res, "claims.jsonl")} if os.path.isdir(res) else set()
        bad = sorted(cited - known)
        if not cited:
            run.add("V11", "CONCERNS", "research report cites the ledger", ["report.md cites no claim ids"])
        elif bad:
            run.add("V11", "FAIL", "research report cites only claims that exist", [f"unknown: {', '.join(bad)}"])
        else:
            run.add("V11", "PASS", "research report cites the ledger", [f"{len(cited)} claim ids cited, all in the ledger"])
    try:
        bp = proposalmod.load(rd)
    except (OSError, ValueError) as e:
        run.add("V12", "NOT ASSESSED", "proposal passes its check", [str(e)])
        return
    v, fail, concern, na = proposalmod.check(bp, res)
    run.add("V12", {"PASS": "PASS", "CONCERNS": "CONCERNS", "FAIL": "FAIL"}.get(v, "NOT ASSESSED"),
            "proposal passes its check", [f"FAIL: {f}" for f in fail][:15] + [f"NOT ASSESSED: {n}" for n in na]
            + [f"{len(concern)} concerns (listed by proposal.py check)"])
    mdp = os.path.join(rd, "proposal.md")
    if not os.path.exists(mdp):
        run.add("V13", "FAIL", "proposal.md is rendered from the current proposal.json", ["proposal.md missing"])
    elif fail:
        run.add("V13", "NOT ASSESSED", "proposal.md is current", ["proposal has structural failures; cannot render"])
    else:
        same = _read(mdp) == proposalmod.render(bp)
        run.add("V13", "PASS" if same else "FAIL", "proposal.md is exactly what proposal.py render produces now",
                ["identical"] if same else ["proposal.md differs from a fresh render — the user would approve a "
                                            "document that is not the proposal; run proposal.py render"])
    early = [m for m in STUDIO_MARKERS if os.path.exists(os.path.join(target, m))]
    run.add("V14", "FAIL" if early else "PASS", "nothing was generated before approval",
            [f"present before approval: {', '.join(early)}"] if early else ["target holds only .ssb/"])
    cp = os.path.join(rd, "critic.md")
    if not os.path.exists(cp):
        run.add("V15", "NOT ASSESSED", "blind critic findings are on record", ["no .ssb/critic.md"])
    else:
        t = _read(cp)
        n_find = len(re.findall(r"^\s*(?:\d+\.|-)\s", t, re.M))
        ev = [f"{n_find} findings listed"]
        status = "PASS"
        if re.search(r"^independent:\s*no\b", t, re.M | re.I):
            ev.append("critic was NOT independent (self-review)")
            status = "CONCERNS"
        if mtime(cp) < mtime(os.path.join(rd, "proposal.json")) and status == "PASS":
            ev.append("proposal.json changed after the critic ran — fine if the changes are the critic's fixes")
        run.add("V15", status, "blind critic findings are on record", ev)
    oq = bp.get("open_questions", [])
    run.add("V16", "PASS", "open questions are listed for the user", [f"{len(oq)} open questions"] + [f"- {q}" for q in oq[:8]])
    v_refutation(run, target, rd)
    reviewed = [os.path.join(rd, "proposal.json"), mdp, rp]
    in_scope = [r for r in bp.get("roles", []) if f"role:{r['id']}" not in set(proposalmod.deferred_items(bp))]
    counts = {"role": {len(bp.get("roles", [])), len(in_scope)}, "agent": {len(bp.get("roles", [])), len(in_scope)},
              "skill": {len(bp.get("skills", [])), len(bp.get("skills", [])) + len(proposalmod.BASELINE_SKILLS)},
              "rule": {len(bp.get("rules", []))}, "gate": {len(bp.get("gates", []))}}
    v_message(run, target, rd, "proposal", counts, reviewed)
    v_review(run, rd, reviewed, "P")


# ------------------------------------------------------------------ stop 2: generated

def validate_generated(run, target, rd, st):
    ok, why = statemod.is_approved(rd)
    run.add("V20", "PASS" if ok else "FAIL", "the generated studio comes from the approved proposal", [why])
    mp = os.path.join(target, ".claude/docs/studio-manifest.json")
    if not os.path.exists(mp):
        run.add("V21", "FAIL", "generation manifest exists", [f"missing {mp}"])
    else:
        m = json.loads(_read(mp))
        cur = statemod.proposal_hash(rd)
        run.add("V21", "PASS" if m.get("proposal_sha256") == cur else "FAIL",
                "the files were generated from the current proposal",
                [f"manifest {str(m.get('proposal_sha256'))[:12]}… vs proposal {str(cur)[:12]}…",
                 f"deferred: {', '.join(m.get('deferred', [])) or 'none'}"])
    missing = [l for l in statemod.LAYERS if l not in st.get("layers", [])]
    run.add("V22", "FAIL" if missing else "PASS", "every layer was generated",
            [f"not generated: {', '.join(missing)}"] if missing else ["all 9 layers"])
    checker = os.path.join(target, ".claude/scripts/check_template.py")
    if not os.path.exists(checker):
        run.add("V23", "NOT ASSESSED", "template checker", ["the studio has no .claude/scripts/check_template.py"])
    else:
        r = sh([checker, target, "--proposal", os.path.join(rd, "proposal.json")], env={"STUDIO_ROOT": target})
        v = last_verdict(r.stdout) or "NOT ASSESSED"
        fails = [l for l in r.stdout.splitlines() if " FAIL — " in l or " NOT ASSESSED — " in l]
        run.add("V23", v if v in RANK else "NOT ASSESSED", "template checker (13 checks incl. the hierarchy and agent-readability)",
                [l for l in r.stdout.splitlines() if l.startswith("VERDICT")] + fails[:10])
    td = os.path.join(target, "studio-tests")
    if not os.path.isdir(td):
        run.add("V24", "NOT ASSESSED", "the studio's own tests", ["no studio-tests/"])
    else:
        r = sh(["-m", "unittest", "discover", "-s", "studio-tests", "-p", "test_*.py"], cwd=target)
        tail = (r.stderr.strip().splitlines() or ["(no output)"])[-3:]
        run.add("V24", "PASS" if r.returncode == 0 else "FAIL", "the studio's own tests pass", tail)
    # drift: files that differ from what the approved proposal renders (KEEP files, hand edits)
    try:
        import generate as genmod
        bp = proposalmod.load(rd)
        drift = []
        for _lay, rel, text, _ex in genmod.plan(bp, rd):
            p = os.path.join(target, rel)
            if os.path.exists(p) and _read(p) != text:
                drift.append(rel)
        run.add("V25", "CONCERNS" if drift else "PASS", "every generated file matches the approved proposal",
                [f"differs (kept or hand-edited): {d}" for d in drift[:15]] or ["no drift"])
    except Exception as e:  # noqa: BLE001
        run.add("V25", "NOT ASSESSED", "drift against the proposal", [f"{e.__class__.__name__}: {e}"])
    reviewed = [os.path.join(rd, "proposal.json")]
    for base, dirs, files in os.walk(os.path.join(target, ".claude")):
        dirs[:] = [d for d in dirs if d != "__pycache__"]  # created by running the checks themselves
        reviewed += [os.path.join(base, f) for f in files if not f.endswith(".pyc")]
    v_trial(run, target, rd)
    v_refutation(run, target, rd)
    import glob as _glob
    n = lambda pat: len(_glob.glob(os.path.join(target, pat)))  # noqa: E731
    counts = {"agent": {n(".claude/agents/*.md")}, "role": {n(".claude/agents/*.md")},
              "skill": {n(".claude/skills/*/SKILL.md")}, "rule": {n(".claude/rules/*.md")},
              "gate": {n(".claude/docs/gates/*.md")}}
    v_message(run, target, rd, "generated", counts, reviewed)
    v_review(run, rd, reviewed, "G")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--changes", action="store_true", help="list what changed since the last reported stop")
    ap.add_argument("--mark-reported", action="store_true",
                    help="record the current state as reported to the user (the next critic's baseline)")
    a = ap.parse_args(argv)
    target = os.path.abspath(a.target)
    rd = os.path.join(target, ".ssb")
    if a.changes:
        ch, had = changes(target, rd)
        print(f"CHANGES since {'the last reported stop' if had else 'the start of the run (no baseline yet)'}: {len(ch)}")
        for k in sorted(ch):
            print(f"{ch[k]:9} {k}")
        return 0
    if a.mark_reported:
        last = os.path.join(rd, "validation.json")
        if not os.path.exists(last):
            print("REFUSED: no validation has run — validate before reporting, then mark")
            return 2
        rec = json.loads(_read(last))
        if rec.get("verdict") == "FAIL":
            print("NOTE: the last validation FAILED; marking records what the user was shown, failures included")
        with open(os.path.join(rd, "baseline.json"), "w", encoding="utf-8") as fh:
            json.dump({"at": _dt.datetime.now().isoformat(timespec="seconds"), "verdict": rec.get("verdict"),
                       "stop": rec.get("stop"), "files": snapshot(target)}, fh, indent=2)
            fh.write("\n")
        print(f"baseline recorded: {len(snapshot(target))} files")
        return 0
    run = Run()
    st = v_state(run, rd)
    if st is None:
        stop = "unknown"
    else:
        approved, _ = statemod.is_approved(rd)
        generated = os.path.exists(os.path.join(target, ".claude/docs/studio-manifest.json")) or st.get("layers")
        stop = "generated" if (approved and generated) else "proposal"
        if stop == "proposal":
            validate_proposal(run, target, rd)
        else:
            validate_generated(run, target, rd, st)
    verdict = run.verdict()
    record = {"stop": stop, "verdict": verdict, "at": _dt.datetime.now().isoformat(timespec="seconds"),
              "checks": run.rows}
    if os.path.isdir(rd):
        with open(os.path.join(rd, "validation.json"), "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2)
            fh.write("\n")
    if a.json:
        print(json.dumps(record, indent=2))
    else:
        for r in run.rows:
            print(f"{r['id']} {r['status']} — {r['what']}")
            for e in r["evidence"]:
                print(f"  {e}")
        print(f"VALIDATE {stop}: {verdict}")
    return {"PASS": 0, "CONCERNS": 0, "FAIL": 1, "NOT ASSESSED": 3}[verdict]


if __name__ == "__main__":
    sys.exit(main())
