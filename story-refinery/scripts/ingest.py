#!/usr/bin/env python3
"""Read a refined ticket back into a bundle. Stdlib only, no network.

  python ingest.py ticket --file description.md --key ABC-123 [--out bundle.json]
  python ingest.py ticket --file out/preview.md [--out bundle.json]

Re-refinement diffs against the stored bundle in `.refinery/bundles/`. In a real
team that bundle is usually on someone else's laptop, or was never kept, and the
refinement then starts from the tracker text - which is the compressed version,
so the second pass is worse than the first.

This reads the rendering back. It recovers the *projections*: the criteria and
their codes, the subtask table, the decision table, the questions, and every agent
brief still sitting in its markers - with the embedded hash checked, which is how
you find out a human edited a brief in the tracker.

It cannot recover the evidence. `evidence`, `intake`, `review`, `tracker_meta` and
`triage` were never in the ticket, so the imported bundle is deliberately
incomplete and says which parts you have to re-derive. Trust the codes; re-read
the code.

Exit codes: 0 imported, 1 imported with a brief whose hash no longer matches,
2 nothing readable.
"""

import argparse
import hashlib
import json
import re
import sys

SECTION_RX = re.compile(r"^##+\s+(.*)$", re.M)
AC_RX = re.compile(r"^\*\*(?P<id>[A-Za-z][\w.-]*?)\s+[—-]\s+(?P<rule>.+?)\*\*$", re.M)
FENCE_RX = re.compile(r"<!--\s*AGENT-BRIEF[^>]*?(\{.*?\})?\s*-->\s*```json\s*(?P<body>.*?)```",
                      re.S)
HASH_RX = re.compile(r'"hash":\s*"([^"]+)"')
TICKET_RX = re.compile(r"\b([A-Z][A-Z0-9]{1,9}-\d+)\b")


def brief_hash(brief):
    return "sha256:" + hashlib.sha256(
        json.dumps(brief, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def sections(text):
    """Heading -> the text under it, for the headings emit.py writes."""
    out, marks = {}, list(SECTION_RX.finditer(text))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out.setdefault(m.group(1).strip().lower(), text[m.end():end].strip())
    return out


def bullets(block):
    return [re.sub(r"^[-*]\s+", "", line).strip()
            for line in (block or "").splitlines() if re.match(r"^[-*]\s+", line.strip())]


def parse_criteria(text):
    criteria, marks = [], list(AC_RX.finditer(text))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        examples = []
        for line in bullets(text[m.end():end]):
            given = re.match(r"Given (.+?) / When (.+?) / Then (.+)$", line)
            if given:
                examples.append({"given": given.group(1), "when": given.group(2),
                                 "then": given.group(3)})
            elif "→" in line:
                case, expect = line.split("→", 1)
                examples.append({"case": case.strip(), "expect": expect.strip()})
            elif line:
                examples.append({"case": line, "expect": ""})
        criteria.append({"id": m.group("id"), "rule": m.group("rule").strip(),
                         "examples": examples})
    return criteria


def parse_table(block):
    rows = [line.strip() for line in (block or "").splitlines()
            if line.strip().startswith("|")]
    if len(rows) < 2:
        return [], []
    cells = lambda r: [c.strip() for c in r.strip("|").split("|")]  # noqa: E731
    return cells(rows[0]), [cells(r) for r in rows[2:]]


def parse_decision_table(block):
    header, rows = parse_table(block)
    if not header or len(header) < 3:
        return None
    conditions = header[:-2]
    values, rules = {c: [] for c in conditions}, []
    for row in rows:
        if len(row) != len(header) or "cannot occur" in row[-2]:
            continue
        when = {}
        for name, value in zip(conditions, row):
            when[name] = value
            if value != "*" and value not in values[name]:
                values[name].append(value)
        rule = {"when": when, "then": row[-2]}
        if row[-1] not in ("—", "-", ""):
            rule["ac"] = row[-1]
        rules.append(rule)
    return {"conditions": [{"id": c, "values": values[c]} for c in conditions],
            "rules": rules, "impossible": []}


def parse_subtask_table(block):
    header, rows = parse_table(block)
    if not header:
        return []
    subs = []
    for row in rows:
        if len(row) < 6:
            continue
        listy = lambda v: [] if v in ("—", "-", "") else [x.strip() for x in v.split(",")]  # noqa: E731
        days = re.sub(r"[^\d.]", "", row[5]) or "0"
        subs.append({"id": row[0], "title": row[1], "repo": row[2],
                     "covers": listy(row[3]), "depends_on": listy(row[4]),
                     "estimate_days": float(days)})
    return subs


def parse_questions(block):
    out = []
    for i, line in enumerate(bullets(block), 1):
        m = re.match(r"(?P<id>Q\d+)?\s*(?P<text>.+?)\s+—\s+owner:\s*(?P<owner>.*?)\s+—\s+"
                     r"blocking:\s*(?P<blocking>yes|no)\s*$", line)
        if m:
            out.append({"id": m.group("id") or "Q%d" % i, "text": m.group("text").strip(),
                        "owner": "" if m.group("owner") == "UNASSIGNED" else m.group("owner"),
                        "blocking": m.group("blocking") == "yes"})
    return out


def parse_briefs(text):
    """Every agent brief still in its markers, and whether it still matches its hash."""
    briefs, edited = [], []
    for match in FENCE_RX.finditer(text):
        try:
            brief = json.loads(match.group("body"))
        except ValueError:
            edited.append(("unparseable", None))
            continue
        stamped = HASH_RX.search(match.group(0))
        stamped = stamped.group(1) if stamped else None
        if stamped and stamped != brief_hash(brief):
            edited.append((brief.get("repo", "?"), brief.get("objective", "")[:60]))
        briefs.append(brief)
    return briefs, edited


def ingest(text, key=None):
    # A preview carries every body at once; a description carries one.
    if text.lstrip().startswith("# Push preview"):
        text = text.split("\n---\n", 1)[-1]
    sec = sections(text)
    story = {"key": key or (TICKET_RX.search(text).group(1) if TICKET_RX.search(text) else ""),
             "source_text": "", "summary_human": sec.get("why / what", "").strip()}

    goal = re.search(r"^\*\*Goal\*\*:\s*(.+)$", text, re.M)
    if goal:
        story["impact"] = {"goal": goal.group(1).strip()}
    criteria = parse_criteria(sec.get("acceptance criteria", ""))
    if criteria:
        story["acceptance_criteria"] = criteria
    if sec.get("non-goals"):
        story["non_goals"] = bullets(sec["non-goals"])
    notes = sec.get("technical notes", "")
    if notes:
        story["technical_notes_human"] = notes.split("**Decisions**")[0].strip()
    nf = {}
    for line in bullets(sec.get("non-functional", "")):
        m = re.match(r"\*\*(.+?)\*\*:\s*(.+)$", line)
        if m:
            nf[m.group(1)] = m.group(2)
    if nf:
        story["non_functional"] = nf

    table = parse_decision_table(sec.get("acceptance criteria", ""))
    if table and table["rules"]:
        story["decision_table"] = table

    bundle = {"schema_version": "1.0", "story": story,
              "open_questions": parse_questions(sec.get("open questions", "")),
              "subtasks": parse_subtask_table(sec.get("subtasks", ""))}

    briefs, edited = parse_briefs(text)
    by_repo = {}
    for brief in briefs:
        by_repo.setdefault(brief.get("repo"), []).append(brief)
    for sub in bundle["subtasks"]:
        pool = by_repo.get(sub.get("repo")) or []
        if pool:
            sub["agent_brief"] = pool.pop(0)
    return bundle, edited


NOT_IN_A_TICKET = ("evidence", "story.intake", "story.tracker_meta", "story.triage",
                   "review", "tailoring")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("ticket", help="read a rendered ticket or preview back into a bundle")
    p.add_argument("--file", required=True, help="the description, or an out/preview.md")
    p.add_argument("--key")
    p.add_argument("--out")
    args = ap.parse_args(argv)

    try:
        with open(args.file, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        print("cannot read %s: %s" % (args.file, exc), file=sys.stderr)
        return 2

    bundle, edited = ingest(text, args.key)
    story = bundle["story"]
    print("recovered %s: %d criterion/criteria, %d subtask(s), %d question(s), %d brief(s)%s"
          % (story.get("key") or "no key found",
             len(story.get("acceptance_criteria") or []), len(bundle["subtasks"]),
             len(bundle["open_questions"]),
             sum(1 for s in bundle["subtasks"] if s.get("agent_brief")),
             ", decision table" if story.get("decision_table") else ""))
    if not story.get("acceptance_criteria") and not bundle["subtasks"]:
        print("nothing recognisable - is this a ticket this skill rendered?", file=sys.stderr)
        return 2

    for repo, objective in edited:
        print("! a brief in %s no longer matches its own hash - somebody edited it in the "
              "tracker: %s. Show the difference and ask before overwriting." % (repo, objective))

    print("\nNot recoverable from a ticket, and not guessed at: %s."
          % ", ".join(NOT_IN_A_TICKET))
    print("Re-derive them. An imported bundle will not validate until you do, which is "
          "correct: the codes came back, the evidence did not.")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(bundle, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        print("wrote %s" % args.out)
    else:
        print(json.dumps(bundle, indent=2, ensure_ascii=False))
    return 1 if edited else 0


if __name__ == "__main__":
    sys.exit(main())
