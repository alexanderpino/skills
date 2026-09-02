#!/usr/bin/env python3
"""Adversarial review for a story-refinery bundle. Stdlib only, no network.

  python review.py brief  --bundle bundle.json [--critic implementer] [--out reviews/]
  python review.py digest --bundle bundle.json [--stamp]
  python review.py check  --bundle bundle.json

`brief` prints the sealed packet one critic judges: their mandate, the finding
contract, and only the slice of the bundle that mandate covers. Blindness is the
whole point - a critic who can see why you chose something grades your reasoning
instead of the artefact - so the packet carries no transcript, no decision
rationale and no self-score. Hand it to a sub-agent verbatim.

`digest` stamps the content hash the review was made against. `validate.py`
REV007 rejects a review whose bundle has changed since, because a review of an
older artefact is not a review of this one.

Exit codes: check -> 0 clean, 1 a blocking finding is still open, 2 usage/parse
error. brief and digest -> 0, or 2 on a bad bundle or unknown critic.
"""

import argparse
import hashlib
import json
import os
import re
import sys

SEVERITIES = ("blocking", "major", "minor")
STATUSES = ("open", "fixed", "accepted", "disputed")

# Fields excluded from the content digest: the review is about the rest of the
# bundle, and a re-render must not invalidate a review that is still valid.
DIGEST_EXCLUDE = ("review", "generated_at")

FINDING_CONTRACT = """\
## What you must return

A list of findings. Each one:

    id        F1, F2, ...
    severity  blocking | major | minor
    locator   a path into the bundle - story.acceptance_criteria[1],
              subtasks[3].agent_brief.done_when[0]. It must resolve; an
              unresolvable locator is dropped by validate.py (REV005).
    claim     what is wrong, in one sentence
    failure   the concrete thing that goes wrong downstream if it ships as is:
              who does what, and what they get. Not "this is unclear" - name
              the wrong turn the reader takes.

Rules of this panel:

- Your prior is that this refinement is wrong somewhere. Find where.
- "Looks good" is not a verdict. If you genuinely cannot break it, say what you
  tried and why it held - that goes in `attempted`, and it is the only accepted
  form of a clean report (REV004).
- No locator, no finding. Harshness without a locator is vibes, and this skill
  holds you to the same evidence rule it holds the refinement to.
- Do not propose the implementation. You are judging whether the package can be
  implemented correctly by someone who was not in the room, not writing it.
- Judge only what is in this packet. If something you need is missing from it,
  that absence is itself a finding.
"""

CRITICS = {
    "implementer": {
        "title": "The Implementer",
        "voice": "a competent engineer, or an agent, with zero context beyond this "
                 "packet, who will follow the brief literally",
        "mandate": "Take each subtask in turn and try to execute it from the brief "
                   "alone. Every point where you would have to guess, ask, or open a "
                   "file the brief never named is a finding.",
        "hunt": [
            "the first ambiguity that would make you stop and ask",
            "a `done_when` you cannot actually run, or whose result you cannot predict",
            "an objective that needs a file `read_first` never mentions",
            "an instruction wide enough to justify touching code outside change_surface",
            "two subtasks that would both plausibly claim the same edit",
        ],
        "slice": lambda b: {
            "subtasks": [{k: s.get(k) for k in
                          ("id", "title", "repo", "kind", "estimate_days", "human",
                           "depends_on", "agent_brief")}
                         for s in b.get("subtasks") or []],
        },
    },
    "tester": {
        "title": "The Tester",
        "voice": "a QA engineer who has to turn every criterion into a test that can "
                 "fail",
        "mandate": "Try to write a failing test for each acceptance criterion. Any "
                   "criterion you cannot make binary - pass here, fail there - is a "
                   "finding, and so is any behaviour the criteria never pin down.",
        "hunt": [
            "a criterion with no observable outcome, or one that restates the title",
            "a missing boundary: the empty case, the maximum, the duplicate, the retry",
            "failure paths nobody specified - what happens when the dependency is down",
            "concurrency: two of these at once, or the same one twice",
            "a non-functional row left blank rather than answered 'unchanged'",
        ],
        "slice": lambda b: {
            "acceptance_criteria": (b.get("story") or {}).get("acceptance_criteria"),
            "non_functional": (b.get("story") or {}).get("non_functional"),
            "non_goals": (b.get("story") or {}).get("non_goals"),
            "done_when": [{"subtask": s.get("id"),
                           "done_when": (s.get("agent_brief") or {}).get("done_when")}
                          for s in b.get("subtasks") or []],
        },
    },
    "archaeologist": {
        "title": "The Archaeologist",
        "voice": "a reviewer who trusts nothing and re-opens every file cited",
        "mandate": "Open every citation in this packet in the repos on disk. A path "
                   "that does not exist, a line that does not say what it is claimed to "
                   "say, or a convention asserted without a citation is a finding - "
                   "severity blocking, because everything downstream trusts these.",
        "hunt": [
            "a path:line citation that cannot be re-opened",
            "a symbol named in the notes that the file does not contain",
            "a convention presented as a house rule that is really a training prior",
            "an index-derived claim not marked [?] when the index is stale",
            "a file in a brief's change_surface that evidence never recorded",
        ],
        "slice": lambda b: {
            "repos": (b.get("evidence") or {}).get("repos"),
            "change_surface": (b.get("evidence") or {}).get("change_surface"),
            "contracts": (b.get("evidence") or {}).get("contracts"),
            "conventions": (b.get("evidence") or {}).get("conventions"),
            "technical_notes_human": (b.get("story") or {}).get("technical_notes_human"),
            "brief_conventions": [{"subtask": s.get("id"),
                                   "conventions": (s.get("agent_brief") or {}).get("conventions"),
                                   "change_surface": (s.get("agent_brief") or {}).get("change_surface")}
                                  for s in b.get("subtasks") or []],
        },
    },
    "sequencer": {
        "title": "The Sequencer",
        "voice": "the person who has to schedule this work and watch it land",
        "mandate": "Attack the plan as a plan. Take each wave and ask whether "
                   "everything in it can genuinely start at the same time, and whether "
                   "each subtask leaves the system working when it lands alone.",
        "hunt": [
            "a subtask that cannot really start when the graph says it can",
            "a dependency recorded only because the subtasks were written in that order",
            "a slice that leaves the system broken until a later subtask lands",
            "an estimate that is a wish - count the files and the unknowns",
            "a consumer scheduled before its contract producer",
            "two subtasks in one wave that will both write the same file",
        ],
        "slice": lambda b: {
            "profile": b.get("profile"),
            "subtasks": [{"id": s.get("id"), "title": s.get("title"), "repo": s.get("repo"),
                          "kind": s.get("kind"), "estimate_days": s.get("estimate_days"),
                          "depends_on": s.get("depends_on"), "covers": s.get("covers"),
                          "produces_contracts": s.get("produces_contracts"),
                          "consumes_contracts": s.get("consumes_contracts"),
                          "writes": [e.get("path") for e in
                                     (s.get("agent_brief") or {}).get("change_surface") or []
                                     if e.get("role") in ("create", "modify", "delete")]}
                         for s in b.get("subtasks") or []],
            "contracts": (b.get("evidence") or {}).get("contracts"),
            "blast_radius": b.get("blast_radius"),
        },
    },
    "stakeholder": {
        "title": "The Stakeholder",
        "voice": "the person who wrote the original ask and has not seen the refinement",
        "mandate": "Compare the original text against what is being planned. Name what "
                   "was asked for and is missing, and what is being built that nobody "
                   "asked for.",
        "hunt": [
            "an outcome in the source text that no criterion covers",
            "scope that appears in the plan but not in the source text or a non-goal",
            "a constraint from the source text quietly dropped",
            "a question answered by assumption where the answer was the point of asking",
        ],
        "slice": lambda b: {
            "source_text": (b.get("story") or {}).get("source_text"),
            "title": (b.get("story") or {}).get("title"),
            "summary_human": (b.get("story") or {}).get("summary_human"),
            "acceptance_criteria": (b.get("story") or {}).get("acceptance_criteria"),
            "non_goals": (b.get("story") or {}).get("non_goals"),
            "subtask_titles": [s.get("title") for s in b.get("subtasks") or []],
            "open_questions": b.get("open_questions"),
        },
    },
}

DEFAULT_PANEL = ["implementer", "tester", "archaeologist", "sequencer"]


# ---------------------------------------------------------------------- digest

def content_digest(bundle):
    """Hash of everything the review is about. Canonical JSON, so key order and
    whitespace cannot change it - only content can."""
    body = {k: v for k, v in bundle.items() if k not in DIGEST_EXCLUDE}
    blob = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


LOCATOR_RX = re.compile(r"([A-Za-z_][\w-]*)|\[(\d+)\]")


def resolve_locator(bundle, locator):
    """Walk a locator like `subtasks[2].agent_brief.done_when[0]` into the bundle.

    Returns (True, value) or (False, None). Used by validate.py REV005: a finding
    that points nowhere cannot be acted on, and is usually a critic describing a
    bundle it was not shown."""
    if not locator or not isinstance(locator, str):
        return False, None
    text = locator.strip().lstrip("$").lstrip(".")
    if not text:
        return False, None
    node = bundle
    pos = 0
    for match in LOCATOR_RX.finditer(text):
        if match.start() > pos and text[pos:match.start()] not in (".", ""):
            return False, None
        pos = match.end()
        key, index = match.group(1), match.group(2)
        if key is not None:
            if not isinstance(node, dict) or key not in node:
                return False, None
            node = node[key]
        else:
            if not isinstance(node, list) or int(index) >= len(node):
                return False, None
            node = node[int(index)]
    return (pos == len(text)), (node if pos == len(text) else None)


# ----------------------------------------------------------------------- brief

def render_brief(bundle, critic_id):
    spec = CRITICS[critic_id]
    story = bundle.get("story") or {}
    packet = spec["slice"](bundle)
    lines = [
        "# Critic packet - %s (`%s`)" % (spec["title"], critic_id),
        "",
        "Story: **%s %s**" % (story.get("key", "?"), story.get("title", "")),
        "Bundle digest: `%s`" % content_digest(bundle),
        "",
        "You are %s." % spec["voice"],
        "",
        "## Your mandate",
        "",
        spec["mandate"],
        "",
        "## What to hunt for",
        "",
    ]
    lines += ["- %s" % h for h in spec["hunt"]]
    lines += [
        "",
        "## Withheld deliberately",
        "",
        "You are not being shown the conversation that produced this, the rationale "
        "behind any decision, or the author's own assessment. If a choice only makes "
        "sense with context you do not have, that is a finding, not a gap in this "
        "packet.",
        "",
        FINDING_CONTRACT,
        "## The artefact",
        "",
        "```json",
        json.dumps(packet, indent=2, ensure_ascii=False),
        "```",
        "",
    ]
    return "\n".join(lines)


# ----------------------------------------------------------------------- check

def summarize(bundle):
    review = bundle.get("review") or {}
    findings = review.get("findings") or []
    by = {}
    for f in findings:
        by.setdefault((f.get("severity"), f.get("status")), []).append(f.get("id"))
    open_blocking = [f.get("id") for f in findings
                     if f.get("severity") == "blocking" and f.get("status") == "open"]
    stale = review and review.get("bundle_digest") != content_digest(bundle)
    return review, findings, by, open_blocking, stale


def cmd_check(bundle):
    review, findings, by, open_blocking, stale = summarize(bundle)
    if not review:
        print("no review recorded - the story and subtasks have not been criticised")
        return 1
    print("method: %s   critics: %d   findings: %d"
          % (review.get("method", "?"), len(review.get("critics") or []), len(findings)))
    for critic in review.get("critics") or []:
        found = [f["id"] for f in findings if f.get("critic") == critic.get("id")]
        print("  %-14s context=%-12s findings=%s"
              % (critic.get("id", "?"), critic.get("context", "?"),
                 ", ".join(found) if found else "none (attempted: %s)"
                 % ("yes" if critic.get("attempted") else "NOT RECORDED")))
    for (severity, status), ids in sorted(by.items(), key=lambda kv: str(kv[0])):
        print("  %-9s %-9s %s" % (severity, status, ", ".join(ids)))
    if stale:
        print("STALE  the bundle changed after this review - re-run the panel or "
              "re-stamp with `review.py digest --stamp`")
    if open_blocking:
        print("NOT CLEAR  blocking finding(s) still open: %s" % ", ".join(open_blocking))
        return 1
    print("CLEAR  no blocking finding is open")
    return 0


# ------------------------------------------------------------------------ main

def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_brief = sub.add_parser("brief", help="print the sealed packet for a critic")
    p_brief.add_argument("--bundle", default="bundle.json")
    p_brief.add_argument("--critic", action="append",
                         help="critic id; repeatable. Default: the standard panel")
    p_brief.add_argument("--out", help="write one file per critic into this directory")

    p_digest = sub.add_parser("digest", help="content hash the review is made against")
    p_digest.add_argument("--bundle", default="bundle.json")
    p_digest.add_argument("--stamp", action="store_true",
                          help="write it into review.bundle_digest")

    p_check = sub.add_parser("check", help="summarise findings; exit 1 if one blocks")
    p_check.add_argument("--bundle", default="bundle.json")

    args = ap.parse_args(argv)
    try:
        bundle = load(args.bundle)
    except (OSError, ValueError) as exc:
        print("cannot read bundle: %s" % exc, file=sys.stderr)
        return 2

    if args.cmd == "digest":
        digest = content_digest(bundle)
        if args.stamp:
            bundle.setdefault("review", {})["bundle_digest"] = digest
            with open(args.bundle, "w", encoding="utf-8") as fh:
                json.dump(bundle, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
            print("stamped %s" % digest)
        else:
            print(digest)
        return 0

    if args.cmd == "check":
        return cmd_check(bundle)

    ids = args.critic or DEFAULT_PANEL
    unknown = [c for c in ids if c not in CRITICS]
    if unknown:
        print("unknown critic(s): %s (known: %s)"
              % (", ".join(unknown), ", ".join(sorted(CRITICS))), file=sys.stderr)
        return 2
    if args.out:
        os.makedirs(args.out, exist_ok=True)
    for cid in ids:
        text = render_brief(bundle, cid)
        if args.out:
            path = os.path.join(args.out, "critic-%s.md" % cid)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            print("wrote %s" % path)
        else:
            print(text)
    if args.out:
        print("Hand each packet to a separate critic in fresh context. Do not add the "
              "story's rationale to it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
