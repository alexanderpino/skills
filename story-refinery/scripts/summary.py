#!/usr/bin/env python3
"""One screen a refiner can talk from. Stdlib only, no network.

  python summary.py --bundle bundle.json [--config refinery.yaml] [--out summary.md]
  python summary.py --bundle a.json b.json c.json          # a whole batch

`preview.md` is what you read before pushing: every ticket body, in full. This is
the other artefact - what the work is, in the order it happens, what it hinges on,
who owes an answer, and where it stands. It is meant to be read out loud in a
refinement or a planning session, so it fits on a screen and says nothing twice.

It works on an unfinished bundle on purpose: the moment you most want to discuss
something is before it is finished, and a summary that refuses until the gates
are green is a summary nobody can use.

Exit code is always 0. This reports; `validate.py` decides.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _yaml import load_config  # noqa: E402
from emit import waves  # noqa: E402
from validate import validate  # noqa: E402


def critical_path(subtasks):
    """Longest chain by estimate, which is the earliest this can be done however
    many people you put on it. The total is what a plan usually gets confused with."""
    by_id = {s.get("id"): s for s in subtasks}
    memo = {}

    def longest(node, stack):
        if node in memo:
            return memo[node]
        if node in stack or node not in by_id:
            return 0.0, []
        best, path = 0.0, []
        for dep in by_id[node].get("depends_on") or []:
            days, chain = longest(dep, stack | {node})
            if days > best:
                best, path = days, chain
        own = by_id[node].get("estimate_days") or 0.0
        memo[node] = (best + own, path + [node])
        return memo[node]

    if not by_id:
        return 0.0, []
    return max((longest(i, frozenset()) for i in by_id), key=lambda r: r[0])


def shape(bundle):
    subs = bundle.get("subtasks") or []
    total = sum(s.get("estimate_days") or 0.0 for s in subs)
    path_days, path = critical_path(subs)
    plan = waves(subs)
    repos = sorted({s.get("repo") for s in subs if s.get("repo")})
    return {"subtasks": len(subs), "repos": repos, "total_days": total,
            "critical_days": path_days, "critical_path": path, "waves": plan,
            "widest": max((len(w["subtasks"]) for w in plan), default=0)}


def verdict_line(bundle, cfg):
    rep = validate(json.loads(json.dumps(bundle)), cfg)
    errors = [i for i in rep.items if i["severity"] == "ERROR"]
    if not errors:
        warns = rep.count("WARN")
        return "**Ready.**%s" % ("" if not warns else " %d warning(s) worth a look." % warns)
    blocking = [i for i in errors if i["code"] in ("READY001", "READY003", "INT003", "TRI002")]
    lead = blocking[0] if blocking else errors[0]
    return ("**Not ready** - %d thing(s) block it, starting with: %s _(%s)_. That is the "
            "finding, not a formality." % (len(errors), lead["message"].split(" - ")[0],
                                           lead["code"]))


def questions_by_owner(bundle):
    out = {}
    for q in bundle.get("open_questions") or []:
        if q.get("answer"):
            continue
        out.setdefault(q.get("owner") or "NOBODY", []).append(q)
    return out


def one_story(bundle, cfg, heading="#"):
    story = bundle.get("story") or {}
    s = shape(bundle)
    key = story.get("key", "?")
    out = ["%s %s — %s" % (heading, key, story.get("title", "")), ""]

    goal = (story.get("impact") or {}).get("goal")
    if goal:
        out += ["**Why.** %s" % goal, ""]
    elif story.get("summary_human"):
        out += ["**Why.** %s" % story["summary_human"].split(". ")[0].strip() + ".", ""]

    if s["subtasks"]:
        out += ["**Size.** %d subtask(s) across %s · %.2g day(s) of work · %.2g day(s) end to "
                "end if run in parallel (%s) · widest wave %d."
                % (s["subtasks"], " and ".join(s["repos"]) or "one repo", s["total_days"],
                   s["critical_days"], " → ".join(s["critical_path"]), s["widest"]), ""]
        out += ["**In order.**", ""]
        by_id = {t.get("id"): t for t in bundle.get("subtasks") or []}
        for w in s["waves"]:
            titles = [(by_id.get(i) or {}).get("title", i) for i in w["subtasks"]]
            out.append("%d. %s" % (w["wave"], "; ".join(titles)))
        out.append("")

    locked = [d for d in bundle.get("decisions") or [] if d.get("status") == "locked"]
    deferred = [d for d in bundle.get("decisions") or [] if d.get("status") == "deferred"]
    if locked or deferred:
        out += ["**It hinges on.**", ""]
        for d in locked:
            out.append("- %s → **%s**" % (d.get("question"), d.get("chosen")))
        for d in deferred:
            out.append("- %s → **still open**, waiting for %s (expires %s)"
                       % (d.get("question"), d.get("waiting_for", "?"), d.get("expires", "?")))
        out.append("")

    asked = questions_by_owner(bundle)
    if asked:
        out += ["**Needs an answer.**", ""]
        for owner, qs in sorted(asked.items()):
            out.append("- **%s**" % owner)
            for q in qs:
                out.append("  - %s%s%s"
                           % (q.get("text", ""),
                              " **(blocking)**" if q.get("blocking") else "",
                              "" if q.get("asked") else " — _not asked yet_"))
        out.append("")

    high = [r for r in story.get("risks") or [] if str(r.get("severity")) == "high"]
    if high:
        out += ["**Worth saying out loud.**", ""] + \
               ["- %s — %s" % (r.get("desc"), r.get("mitigation")) for r in high] + [""]

    pending = (bundle.get("evidence") or {}).get("pending") or []
    if pending:
        out += ["**Waits on work that does not exist yet.**", ""]
        out += ["- %s — from %s" % (p.get("claim"), (p.get("provided_by") or {}).get("ticket", "?"))
                for p in pending] + [""]

    follow = story.get("follow_ups") or []
    if follow:
        out += ["**Leaves behind.** " + "; ".join(
            "%s when %s" % (f.get("ticket"), f.get("trigger")) for f in follow), ""]

    out += [verdict_line(bundle, cfg), ""]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bundle", nargs="+", required=True)
    ap.add_argument("--config", default="refinery.yaml")
    ap.add_argument("--out", help="also write it here")
    args = ap.parse_args(argv)

    cfg = load_config(args.config) if os.path.exists(args.config) else {}
    bundles = []
    for path in args.bundle:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                bundles.append(json.load(fh))
        except (OSError, ValueError) as exc:
            print("cannot read %s: %s" % (path, exc), file=sys.stderr)
            return 2

    lines = []
    if len(bundles) > 1:
        total = sum(shape(b)["total_days"] for b in bundles)
        longest = max(shape(b)["critical_days"] for b in bundles)
        ready = sum(1 for b in bundles
                    if not [i for i in validate(json.loads(json.dumps(b)), cfg).items
                            if i["severity"] == "ERROR"])
        owed = {}
        for b in bundles:
            for owner, qs in questions_by_owner(b).items():
                owed.setdefault(owner, []).append((b.get("story") or {}).get("key", "?"))
        lines += ["# %d stories" % len(bundles), "",
                  "%.2g day(s) of work in total, %.2g on the longest single story, %d of %d "
                  "ready." % (total, longest, ready, len(bundles)), ""]
        if owed:
            lines += ["Between them they are waiting on:", ""]
            lines += ["- **%s** — %s" % (owner, ", ".join(sorted(set(keys))))
                      for owner, keys in sorted(owed.items())]
            lines += ["", "Ask each of them once, naming the stories.", ""]
        lines += ["---", ""]

    for b in bundles:
        lines += one_story(b, cfg, heading="##" if len(bundles) > 1 else "#")

    text = "\n".join(lines).strip() + "\n"
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
