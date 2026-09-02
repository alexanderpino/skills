#!/usr/bin/env python3
"""Render a refinement bundle into tracker payloads. Stdlib only. No network.

  python emit.py bundle.json --config refinery.yaml --out out/

Writes:
  out/preview.md          human review artefact - show this before pushing
  out/push-plan.json      exactly what would be created, and where
  out/payloads/*.json     one payload per issue, adapter-shaped
  out/briefs/*.json       agent briefs, when the sink is attachment or repo_file
  out/comments/*.md       agent briefs, when the sink is comment
  out/context/*.md        the shared context every subtask implementor reads first

Pushing is a separate, explicitly approved step. This script never calls an API.
"""

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _yaml import get, load_config  # noqa: E402
from markup import render_markup  # noqa: E402
from validate import validate  # noqa: E402

SINKS = ("description_tail", "comment", "attachment", "repo_file", "custom_field")
CAPABILITIES = {
    # [?] defaults - probe the live tracker before trusting these.
    "jira":         {"markup": "adf", "subtasks": "native", "attachments": True,
                     "comments": True, "custom_fields": True, "max_description_chars": 32767,
                     "links": True, "link_types": {"blocks": "Blocks", "blocked_by": "is blocked by",
                                                   "relates": "Relates", "duplicates": "Duplicate"}},
    "github":       {"markup": "markdown", "subtasks": "task_list", "attachments": False,
                     "comments": True, "custom_fields": False, "max_description_chars": 65536,
                     "links": False, "link_types": {}},
    "gitlab":       {"markup": "markdown", "subtasks": "task_list", "attachments": False,
                     "comments": True, "custom_fields": False, "max_description_chars": 1000000,
                     "links": True, "link_types": {"blocks": "blocks", "blocked_by": "is blocked by",
                                                   "relates": "relates_to", "duplicates": None}},
    "linear":       {"markup": "markdown", "subtasks": "native", "attachments": True,
                     "comments": True, "custom_fields": False, "max_description_chars": 65536,
                     "links": True, "link_types": {"blocks": "blocks", "blocked_by": "blocked_by",
                                                   "relates": "related", "duplicates": "duplicate"}},
    "azure-devops": {"markup": "html", "subtasks": "native", "attachments": True,
                     "comments": True, "custom_fields": True, "max_description_chars": 100000,
                     "links": True, "link_types": {"blocks": "Successor", "blocked_by": "Predecessor",
                                                   "relates": "Related", "duplicates": "Duplicate"}},
    "markdown":     {"markup": "markdown", "subtasks": "none", "attachments": False,
                     "comments": False, "custom_fields": False, "max_description_chars": 10 ** 9,
                     "links": False, "link_types": {}},
}


def brief_hash(brief):
    return "sha256:" + hashlib.sha256(
        json.dumps(brief, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def fence(brief, key, cfg):
    begin = get(cfg, "tracker.agent_brief.marker_begin", "<!-- AGENT-BRIEF v1 BEGIN -->")
    end = get(cfg, "tracker.agent_brief.marker_end", "<!-- AGENT-BRIEF v1 END -->")
    head = begin.replace("-->", '%s -->' % json.dumps({"ticket": key, "hash": brief_hash(brief)}))
    return "%s\n```json\n%s\n```\n%s" % (head, json.dumps(brief, indent=2), end)


# ------------------------------------------------------------------- rendering

def render_decision_table(table):
    """The table is the part of a refinement a tester reads first, so it goes in the
    ticket as a table and not as a JSON blob."""
    conditions = [c for c in table.get("conditions") or [] if c.get("id")]
    rules = table.get("rules") or []
    if not conditions or not rules:
        return []
    header = [c["id"] for c in conditions]
    out = ["**Decision table**", "",
           "| " + " | ".join(header + ["Outcome", "AC"]) + " |",
           "|" + "|".join("---" for _ in range(len(header) + 2)) + "|"]
    for rule in rules:
        when = rule.get("when") or {}
        cells = [str(when.get(cid, "*")) for cid in header]
        out.append("| " + " | ".join(cells + [str(rule.get("then", "")),
                                              rule.get("ac") or "—"]) + " |")
    for imp in table.get("impossible") or []:
        cells = [str(imp.get(cid, "*")) for cid in header]
        out.append("| " + " | ".join(cells + ["_cannot occur_", "—"]) + " |")
    if table.get("note"):
        out += ["", "_%s_" % table["note"]]
    return out + [""]


def render_story(bundle):
    s = bundle["story"]
    out = ["## Why / What", "", s.get("summary_human", "").strip(), ""]
    goal = (s.get("impact") or {}).get("goal")
    if goal:
        out += ["**Goal**: %s" % goal, ""]
    if s.get("complexity"):
        c = s["complexity"]
        import complexity as CX
        out += ["**Complexity**: %s - %s" % (c.get("band"), ", ".join(
            "%s %s" % (c.get("metrics", {}).get(d), CX.NAMES.get(d, d)) if d in (c.get("metrics") or {})
            else CX.NAMES.get(d, d) for d in c.get("drivers") or []) or "nothing reaches medium"), ""]
    out += render_prerequisites(bundle)
    out += ["## Acceptance criteria", ""]
    for ac in s.get("acceptance_criteria") or []:
        out.append("**%s — %s**" % (ac.get("id"), ac.get("rule")))
        for ex in ac.get("examples") or []:
            if isinstance(ex, dict) and ex.get("given"):
                out.append("- Given %s / When %s / Then %s"
                           % (ex.get("given"), ex.get("when"), ex.get("then")))
            elif isinstance(ex, dict):
                out.append("- %s → %s" % (ex.get("case", ""), ex.get("expect", "")))
            else:
                out.append("- %s" % ex)
        out.append("")
    if s.get("decision_table"):
        out += render_decision_table(s["decision_table"])
    if s.get("non_goals"):
        out += ["## Non-goals", ""] + ["- %s" % g for g in s["non_goals"]] + [""]
    out += ["## Technical notes", "", s.get("technical_notes_human", "").strip(), ""]
    if bundle.get("decisions"):
        out.append("**Decisions**")
        for d in bundle["decisions"]:
            if d.get("status") == "locked":
                out.append("- %s %s → **%s**. %s"
                           % (d.get("id"), d.get("question"), d.get("chosen"), d.get("rationale")))
            else:
                out.append("- %s %s → deferred to spike %s." % (d.get("id"), d.get("question"),
                                                                d.get("spike")))
        out.append("")
    if bundle.get("decisions"):
        for d in bundle["decisions"]:
            if d.get("status") == "deferred" and d.get("expires"):
                out.append("- %s stays open until: %s. Expires %s."
                           % (d.get("id"), d.get("waiting_for") or "?", d["expires"]))
        out.append("")
    if s.get("risks"):
        out.append("**Risks**")
        out += ["- %s %s → %s%s" % (r.get("id"), r.get("desc"), r.get("mitigation"),
                                    " _(detected by: %s)_" % r["detection"]
                                    if r.get("detection") else "")
                for r in s["risks"]]
        out.append("")
    if bundle.get("open_questions"):
        out += ["## Open questions", ""]
        out += ["- %s %s — owner: %s — blocking: %s"
                % (q.get("id"), q.get("text"), q.get("owner") or "UNASSIGNED",
                   "yes" if q.get("blocking") else "no")
                for q in bundle["open_questions"]]
        out.append("")
    out += ["## Subtasks", "", "| # | Title | Repo | Covers | Depends on | Est |",
            "|---|-------|------|--------|------------|-----|"]
    for st in bundle.get("subtasks") or []:
        out.append("| %s | %s | %s | %s | %s | %sd |" % (
            st.get("id"), st.get("title"), st.get("repo"),
            ", ".join(st.get("covers") or []) or "—",
            ", ".join(st.get("depends_on") or []) or "—",
            st.get("estimate_days", "?")))
    out.append("")
    nf = s.get("non_functional") or {}
    if nf:
        out += ["## Non-functional", ""] + ["- **%s**: %s" % (k, v) for k, v in nf.items()] + [""]
    if bundle.get("blast_radius"):
        br = bundle["blast_radius"]
        out.append("_Blast radius: %s repo(s), %s primary + %s secondary file(s), %s contract(s)._"
                   % (br.get("repos"), br.get("files_primary"), br.get("files_secondary"),
                      br.get("contracts")))
    return "\n".join(out).strip() + "\n"


def plan_links(bundle, caps, warnings):
    """The links the tracker must carry, in the adapter's own vocabulary.

    A follow-up story is refined against work that has not been implemented yet.
    Inside one story the wave plan holds the order; across stories nothing does
    except a link, so an unlinked prerequisite is an ordering that exists only in
    the head of whoever refined it."""
    story = bundle["story"]
    key = story.get("key")
    existing = {l.get("key") for l in (story.get("tracker_meta") or {}).get("links") or []}
    types = caps.get("link_types") or {}
    plan = []
    for link in story.get("links") or []:
        target, kind = link.get("key"), link.get("type")
        entry = {"from": key, "type": kind, "to": target, "why": link.get("why"),
                 "already_present": target in existing,
                 "adapter_type": types.get(kind)}
        if not caps.get("links"):
            entry["degraded"] = ("tracker has no typed issue links - stated in the description "
                                 "under Prerequisites instead")
        elif types.get(kind) is None:
            entry["degraded"] = ("adapter has no %r link type - falls back to 'relates' plus the "
                                 "Prerequisites line" % kind)
        plan.append(entry)
    unsupported = [e for e in plan if e.get("degraded")]
    if unsupported:
        warnings.append("%d link(s) cannot be expressed by this tracker - the ordering they carry "
                        "is in the description only, where nothing enforces it" % len(unsupported))
    return plan


def render_prerequisites(bundle):
    """What must exist before this story can start, for a human and for the pusher.

    This is where a refinement of a follow-up story is honest: some of what it
    cites does not exist yet, and this says which item is going to create it."""
    story = bundle["story"]
    blocked = [l for l in story.get("links") or [] if l.get("type") == "blocked_by"]
    blocked += [l for l in (story.get("tracker_meta") or {}).get("links") or []
                if str(l.get("type", "")).lower().replace(" ", "_").endswith("blocked_by")]
    pending = (bundle.get("evidence") or {}).get("pending") or []
    if not blocked and not pending:
        return []
    out = ["## Prerequisites", ""]
    for link in blocked:
        out.append("- Blocked by **%s**%s" % (link.get("key"),
                                              " — %s" % link["why"] if link.get("why") else ""))
    for p in pending:
        provider = p.get("provided_by") or {}
        out.append("- **Does not exist yet**: %s — created by %s%s%s"
                   % (p.get("claim"), provider.get("ticket", "?"),
                      " / %s" % provider["subtask"] if provider.get("subtask") else "",
                      ". %s" % p["note"] if p.get("note") else ""))
    out += ["", "_Everything above is specified work that has not landed. Citations to it point "
            "at the item that creates it, not at a line in the repo._", ""]
    return out


def render_shared_context(bundle):
    """One document every subtask implementor reads, identical for all of them.

    Two reasons it is a separate artefact rather than repeated per brief. It is
    what refinement *learned* and the ticket does not say - conventions, the
    glossary, and above all what is absent - so an implementor does not re-derive
    it, and each re-derivation risks a different answer. And being byte-identical
    across subtasks, it is a stable prefix: a fan-out runner that puts it first
    pays for it once."""
    story = bundle["story"]
    ev = bundle.get("evidence") or {}
    key = story.get("key", "")
    out = ["# Shared context — %s %s" % (key, story.get("title", "")), "",
           "Read this once before your subtask brief. It is identical for every "
           "subtask on this story: the facts refinement established, including the "
           "ones that are absences.", "",
           "## The outcome this serves", "",
           (story.get("impact") or {}).get("goal") or story.get("summary_human", ""), ""]

    pending = ev.get("pending") or []
    if pending:
        out += ["## Not there yet", "",
                "These are cited by the briefs and do not exist in the repo at the time of "
                "writing. Do not go looking for them, and do not substitute something that "
                "looks similar - check the item that creates them.", ""]
        for p in pending:
            provider = p.get("provided_by") or {}
            out.append("- **%s** — from %s%s%s"
                       % (p.get("claim"), provider.get("ticket", "?"),
                          " / %s" % provider["subtask"] if provider.get("subtask") else "",
                          ". %s" % p["note"] if p.get("note") else ""))
        out.append("")

    if ev.get("glossary"):
        out += ["## Glossary", "",
                "Domain words in this story mean this here, whatever they mean elsewhere.", ""]
        for term in ev["glossary"]:
            out.append("- **%s** — %s%s" % (term.get("term"), term.get("means", ""),
                                            " (`%s`)" % term["evidence"]
                                            if term.get("evidence") else ""))
        out.append("")

    if ev.get("conventions"):
        out += ["## House conventions, with the code that shows them", "",
                "Each is cited. Read the citation rather than trusting the sentence, and "
                "match the code you find.", ""]
        out += ["- %s — `%s`" % (c.get("rule"), c.get("evidence")) for c in ev["conventions"]]
        out.append("")

    if ev.get("ruled_out"):
        out += ["## Already ruled out", "",
                "Refinement looked for these and did not find them. Do not spend budget "
                "re-checking, and do not substitute something that merely looks similar.", ""]
        for r in ev["ruled_out"]:
            looked = ", ".join("`%s`" % x for x in r.get("looked_in") or [])
            out.append("- **%s** — looked in %s. %s"
                       % (r.get("claim"), looked or "unrecorded", r.get("conclusion", "")))
        out.append("")

    if ev.get("contracts"):
        out += ["## Contracts that cross a boundary", ""]
        for c in ev["contracts"]:
            out.append("- `%s` (%s) — produced by %s, consumed by %s"
                       % (c.get("path", c.get("id", "?")), c.get("id", ""),
                          ", ".join(c.get("producers") or []) or "?",
                          ", ".join(c.get("consumers") or []) or "?"))
        out.append("")

    decided = [d for d in bundle.get("decisions") or [] if d.get("status") == "locked"]
    if decided:
        out += ["## Decided already — do not re-open", ""]
        out += ["- %s → **%s**. %s" % (d.get("question"), d.get("chosen"), d.get("rationale"))
                for d in decided]
        out.append("")
    deferred = [d for d in bundle.get("decisions") or [] if d.get("status") == "deferred"]
    if deferred:
        out += ["## Deliberately still open — do not decide it in passing", ""]
        out += ["- %s (spike %s, waiting for %s)" % (d.get("question"), d.get("spike"),
                                                     d.get("waiting_for", "?"))
                for d in deferred]
        out.append("")

    provenance = sorted({p for st in bundle.get("subtasks") or []
                         for p in (st.get("agent_brief") or {}).get("provenance") or []})
    out += ["## Freshness", "",
            "This was true at: %s." % (", ".join("`%s`" % p for p in provenance) or "unrecorded"),
            "",
            "If your brief's preflight fails, the code has moved since. Stop and report it "
            "rather than implementing against the brief - a stale anchor is the one case "
            "where the ticket is wrong and you are right.", ""]
    return "\n".join(out).strip() + "\n"


def render_subtask(st, bundle, cfg, sink):
    parent = bundle["story"].get("key", "")
    out = ["Parent: %s · Covers: %s · Depends on: %s · Est: %sd · Kind: %s" % (
        parent, ", ".join(st.get("covers") or []) or "—",
        ", ".join(st.get("depends_on") or []) or "—",
        st.get("estimate_days", "?"), st.get("kind", "feature")), "",
        "## For the developer", "", (st.get("human") or "").strip(), "", "## Done when", ""]
    for d in (st.get("agent_brief") or {}).get("done_when") or []:
        if d.get("type") == "command":
            out.append("- [ ] `%s` → %s" % (d.get("cmd"), d.get("expect", "exit 0")))
        else:
            out.append("- [ ] %s" % d.get("text"))
    out.append("")
    # Preflight and stop_and_ask stay in the brief, not here. The ticket body is
    # read by a developer who already knows to check whether the file moved; the
    # agent is the one that needs it written down, and it has the brief.
    out += ["_Shared context for every subtask on this story: `context/%s-context.md`._"
            % parent, ""]
    if st.get("needs_coordination"):
        out.append("> Crosses a team boundary: %s. Coordinate before starting."
                   % st.get("coordination_with", "unknown team"))
        out.append("")
    if sink == "description_tail":
        out += ["---", "", fence(st.get("agent_brief") or {},
                                 "%s/%s" % (parent, st.get("id")), cfg)]
    elif sink == "attachment":
        out.append("_Agent brief attached as `%s`._"
                   % get(cfg, "tracker.agent_brief.filename", "agent-brief.json"))
    elif sink == "comment":
        out.append("_Agent brief in the first comment._")
    elif sink == "repo_file":
        out.append("_Agent brief: `%s/%s-%s.json` in `%s`._"
                   % (get(cfg, "tracker.agent_brief.repo_file_dir", ".refinery/briefs"),
                      parent, st.get("id"), st.get("repo")))
    return "\n".join(out).strip() + "\n"


# -------------------------------------------------------------------- adapters

def payloads_for(bundle, cfg, adapter, caps, sinks, default_sink):
    story = bundle["story"]
    project = get(cfg, "tracker.project", "")
    prefix = get(cfg, "tracker.labels_prefix", "refinery:")
    # The item's own labels are somebody's decision - triage routing, an escalation,
    # a compliance marker. A push that sends only our labels silently deletes them.
    meta = story.get("tracker_meta") or {}
    existing = [str(x) for x in (meta.get("labels") or []) if x]
    items = [{
        "role": "parent", "id": story.get("key"), "title": story.get("title"),
        "issue_type": meta.get("issue_type") or get(cfg, "tracker.story_issue_type", "Story"),
        "project": project, "body": render_story(bundle),
        "labels": existing + ["%sstory" % prefix],
        "labels_preexisting": existing,
    }]
    subtask_type = get(cfg, "tracker.subtask_issue_type", "Sub-task")
    for st in bundle.get("subtasks") or []:
        items.append({
            "role": "subtask", "id": st.get("id"), "title": st.get("title"),
            "issue_type": subtask_type, "project": project, "parent": story.get("key"),
            "body": render_subtask(st, bundle, cfg, sinks.get(st.get("id"), default_sink)),
            "labels": ["%s%s" % (prefix, st.get("kind", "feature")),
                       "%srepo-%s" % (prefix, st.get("repo"))],
            "repo": st.get("repo"), "depends_on": st.get("depends_on") or [],
        })
    if caps["subtasks"] in ("task_list", "none"):
        checklist = "\n".join("- [ ] %s" % st.get("title") for st in bundle.get("subtasks") or [])
        items[0]["body"] += "\n\n## Subtask checklist\n\n" + checklist + "\n"
        if caps["subtasks"] == "none":
            items[0]["degraded"] = "tracker has no subtask concept - rendered as a checklist"
    return items


def resolve_sink(cfg, caps):
    chain = [get(cfg, "tracker.agent_brief.sink", "description_tail")]
    chain += list(get(cfg, "tracker.agent_brief.fallback", []) or [])
    notes = []
    for sink in chain:
        if sink not in SINKS:
            notes.append("unknown sink %r skipped" % sink)
            continue
        if sink == "attachment" and not caps["attachments"]:
            notes.append("attachment unsupported by %s" % caps.get("_name"))
            continue
        if sink == "comment" and not caps["comments"]:
            notes.append("comments unsupported by %s" % caps.get("_name"))
            continue
        if sink == "custom_field" and not (caps["custom_fields"]
                                           and get(cfg, "tracker.agent_brief.custom_field")):
            notes.append("custom_field unavailable or unconfigured")
            continue
        return sink, notes
    return "repo_file", notes + ["fell all the way through to repo_file"]


def resolve_per_subtask_sinks(bundle, cfg, caps, default_sink, warnings):
    """Degrade per subtask when a description would exceed the tracker's limit.

    The previous version warned that the brief had been moved and then did not move
    it. This one actually moves it, or says plainly that the human text is too long.
    """
    limit = caps["max_description_chars"]
    sinks = {}
    for st in bundle.get("subtasks") or []:
        sid = st.get("id")
        sink = default_sink
        if len(render_subtask(st, bundle, cfg, sink)) > limit:
            for alt in ("attachment", "comment", "repo_file"):
                if alt == "attachment" and not caps["attachments"]:
                    continue
                if alt == "comment" and not caps["comments"]:
                    continue
                if len(render_subtask(st, bundle, cfg, alt)) <= limit:
                    warnings.append("%s exceeded %d chars - agent brief moved to %s"
                                    % (sid, limit, alt))
                    sink = alt
                    break
            else:
                warnings.append("%s exceeds %d chars even without the brief - shorten the "
                                "human text" % (sid, limit))
        sinks[sid] = sink
    return sinks


def triage_section(bundle):
    """What the ticket already said about itself, and what that changed. Whoever
    approves the push is usually the person who put those labels there."""
    story = bundle.get("story") or {}
    meta, triage = story.get("tracker_meta") or {}, story.get("triage") or {}
    if not meta:
        return []
    out = ["## Triage", "",
           "Labels: %s · components: %s · type: %s · priority: %s"
           % (", ".join(meta.get("labels") or []) or "none",
              ", ".join(meta.get("components") or []) or "none",
              meta.get("issue_type") or "?", meta.get("priority") or "?"), ""]
    if meta.get("links"):
        out += ["Linked: %s" % ", ".join(
            "%s %s" % (l.get("type", "relates to"), l.get("key", "?"))
            for l in meta["links"]), ""]
    matched = triage.get("matched") or []
    if matched:
        out += ["These labels changed the refinement:", ""]
        for m in matched:
            out.append("- **%s** (from %s)" % (m.get("id"), ", ".join(m.get("matched_on") or [])))
        consequences = [(k, triage[k]) for k in
                        ("route", "kind", "profile", "require_dimensions",
                         "mandatory_subtask_kinds", "must_answer_nfr", "add_critics")
                        if triage.get(k)]
        for key, value in consequences:
            out.append("  - %s: %s" % (key.replace("_", " "),
                                       ", ".join(value) if isinstance(value, list) else value))
        out.append("")
    elif triage:
        out += ["No label on this item changes the refinement.", ""]
    if triage.get("unknown_labels"):
        out += ["> Unclassified labels: %s. Nobody has decided whether these matter."
                % ", ".join(triage["unknown_labels"]), ""]
    return out


def review_section(bundle):
    """What the critics found, in the artefact the user approves the push from.

    Accepted risks and rebuttals are decisions someone other than the author should
    see before this reaches a board, which makes the preview the right place."""
    review = bundle.get("review") or {}
    if not review:
        return ["## Review", "",
                "**No adversarial review recorded.** Nothing hostile has read this "
                "story or its subtasks. Say so out loud before anyone implements it.",
                ""]
    findings = review.get("findings") or []
    critics = review.get("critics") or []
    method = review.get("method", "?")
    lines = ["## Review", "",
             "Method: **%s** · critics: %s · findings: %d"
             % (method, ", ".join("%s (%s)" % (c.get("id"), c.get("context", "?"))
                                  for c in critics) or "none", len(findings)), ""]
    if method == "rubber-duck":
        lines += ["> Rubber-ducked, not reviewed by a blind panel: one voice with full "
                  "context. Lower assurance, stated here rather than left to be assumed.",
                  ""]
    carried = [f for f in findings if f.get("status") in ("open", "accepted", "disputed")]
    if carried:
        lines += ["These findings were not fixed. They are what you are approving:", ""]
        for f in carried:
            lines.append("- **%s %s** (%s, `%s`): %s"
                         % (f.get("status", "?"), f.get("id", "?"), f.get("severity", "?"),
                            f.get("locator", "?"), f.get("claim", "")))
            if f.get("resolution"):
                lines.append("  - %s%s" % (f["resolution"],
                                           " — %s" % f["accepted_by"]
                                           if f.get("accepted_by") else ""))
        lines.append("")
    fixed = [f.get("id") for f in findings if f.get("status") == "fixed"]
    if fixed:
        lines += ["Fixed before handover: %s." % ", ".join(fixed), ""]
    return lines


def waves(subtasks):
    """Topological layers. Everything in one wave can run in parallel, which is what a
    fan-out runner needs and what a sprint board should show."""
    remaining = {s.get("id"): set(s.get("depends_on") or []) for s in subtasks}
    done, out = set(), []
    while remaining:
        layer = sorted(n for n, deps in remaining.items() if not (deps - done))
        if not layer:
            out.append({"wave": len(out) + 1, "subtasks": sorted(remaining),
                        "note": "cycle - not schedulable"})
            break
        out.append({"wave": len(out) + 1, "subtasks": layer})
        done |= set(layer)
        for n in layer:
            remaining.pop(n)
    return out


def diff_bundles(prev, cur):
    """What a re-refinement changes. Stories get refined more than once; the second
    pass must update a ticket tree rather than duplicate it."""
    prev_subs = {s.get("id"): s for s in prev.get("subtasks") or []}
    cur_subs = {s.get("id"): s for s in cur.get("subtasks") or []}
    blob = lambda d: json.dumps(d, sort_keys=True)  # noqa: E731
    changed = [i for i in sorted(set(cur_subs) & set(prev_subs))
               if blob(prev_subs[i]) != blob(cur_subs[i])]
    prev_ac = {a.get("id"): a.get("rule") for a in
               (prev.get("story") or {}).get("acceptance_criteria") or []}
    cur_ac = {a.get("id"): a.get("rule") for a in
              (cur.get("story") or {}).get("acceptance_criteria") or []}
    story_fields = ("title", "summary_human", "technical_notes_human", "acceptance_criteria",
                    "non_goals", "risks", "non_functional")
    story_changed = any(blob((prev.get("story") or {}).get(f)) != blob((cur.get("story") or {}).get(f))
                        for f in story_fields) or blob(prev.get("decisions")) != blob(cur.get("decisions"))
    return {
        "story_changed": story_changed,
        "subtasks_added": sorted(set(cur_subs) - set(prev_subs)),
        "subtasks_removed": sorted(set(prev_subs) - set(cur_subs)),
        "subtasks_changed": changed,
        "criteria_added": sorted(set(cur_ac) - set(prev_ac)),
        "criteria_removed": sorted(set(prev_ac) - set(cur_ac)),
        "criteria_reworded": sorted(i for i in set(cur_ac) & set(prev_ac)
                                    if cur_ac[i] != prev_ac[i]),
        "brief_hash_changed": sorted(
            i for i in set(cur_subs) & set(prev_subs)
            if brief_hash(cur_subs[i].get("agent_brief") or {})
            != brief_hash(prev_subs[i].get("agent_brief") or {})),
    }


# ------------------------------------------------------------------------ main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle")
    ap.add_argument("--config", default="refinery.yaml")
    ap.add_argument("--out", default="out")
    ap.add_argument("--adapter", help="override tracker.adapter")
    ap.add_argument("--markup", choices=["markdown", "wiki", "adf", "html", "plaintext"],
                    help="override the output markup; defaults to the adapter's own")
    ap.add_argument("--allow-not-ready", action="store_true",
                    help="render a bundle that does not validate. The preview stays useful for "
                         "discussion; the push plan is stamped not-ready either way")
    ap.add_argument("--previous", help="a previous bundle.json - emit an update plan "
                                       "instead of a create plan")
    args = ap.parse_args(argv)

    with open(args.bundle, "r", encoding="utf-8") as fh:
        bundle = json.load(fh)
    cfg = load_config(args.config) if os.path.exists(args.config) else {}
    adapter = args.adapter or get(cfg, "tracker.adapter", "markdown")
    caps = dict(CAPABILITIES.get(adapter, CAPABILITIES["markdown"]))
    caps["_name"] = adapter
    override = get(cfg, "tracker.max_description_chars")
    if override:
        caps["max_description_chars"] = override

    sink, warnings = resolve_sink(cfg, caps)
    sinks = resolve_per_subtask_sinks(bundle, cfg, caps, sink, warnings)
    items = payloads_for(bundle, cfg, adapter, caps, sinks, sink)

    for sub in (args.out, os.path.join(args.out, "payloads"),
                os.path.join(args.out, "briefs"), os.path.join(args.out, "comments")):
        os.makedirs(sub, exist_ok=True)

    key = bundle["story"].get("key", "STORY")
    # An explicit --adapter must not inherit the markup of the adapter it replaced.
    if args.markup:
        target_markup = args.markup
    elif args.adapter:
        target_markup = caps["markup"]
    else:
        target_markup = get(cfg, "tracker.markup", caps["markup"])
    if sink == "description_tail" and target_markup not in ("markdown", "plaintext"):
        warnings.append("agent brief is embedded in a %s description - the JSON survives but "
                        "reads badly; attachment or comment is a better sink here"
                        % target_markup)
    for item in items:
        item["markup"] = target_markup
        item["body_rendered"] = render_markup(item["body"], target_markup)
        name = "%s-story.json" % key if item["role"] == "parent" else "%s-%s.json" % (key, item["id"])
        with open(os.path.join(args.out, "payloads", name), "w", encoding="utf-8") as fh:
            json.dump(item, fh, indent=2)

    for st in bundle.get("subtasks") or []:
        brief = st.get("agent_brief") or {}
        stem = "%s-%s" % (key, st.get("id"))
        st_sink = sinks.get(st.get("id"), sink)
        if st_sink in ("attachment", "repo_file"):
            with open(os.path.join(args.out, "briefs", stem + ".json"), "w", encoding="utf-8") as fh:
                json.dump(brief, fh, indent=2)
        elif st_sink == "comment":
            with open(os.path.join(args.out, "comments", stem + ".md"), "w", encoding="utf-8") as fh:
                fh.write(fence(brief, stem, cfg) + "\n")

    ctx_dir = os.path.join(args.out, "context")
    os.makedirs(ctx_dir, exist_ok=True)
    ctx_name = "%s-context.md" % key
    with open(os.path.join(ctx_dir, ctx_name), "w", encoding="utf-8") as fh:
        fh.write(render_shared_context(bundle))

    links = plan_links(bundle, caps, warnings)
    plan_waves = waves(bundle.get("subtasks") or [])
    delta, prior_progress = None, None
    if args.previous:
        with open(args.previous, "r", encoding="utf-8") as fh:
            prior = json.load(fh)
        prior_progress = (prior.get("story") or {}).get("progress") or {}
        delta = diff_bundles(prior, bundle)

    report = validate(json.loads(json.dumps(bundle)), cfg)
    blocking = [i for i in report.items if i["severity"] == "ERROR"]
    preview = ["# Push preview — %s %s" % (key, bundle["story"].get("title", "")), ""]
    if blocking:
        preview += ["> **This story is not ready.** %d finding(s) block it, starting with "
                    "`%s` %s. Everything below is real and worth discussing; none of it is "
                    "worth pushing yet."
                    % (len(blocking), blocking[0]["code"], blocking[0]["message"]), ""]
    preview += ["",
               "Adapter: **%s** · markup: %s · subtasks: %s · agent brief sink: **%s**"
               % (adapter, caps["markup"], caps["subtasks"], sink), ""]
    tailoring = bundle.get("tailoring") or {}
    if tailoring.get("source"):
        line = "Refined under **%s**%s." % (tailoring["source"],
                                            " v%s" % tailoring["version"]
                                            if tailoring.get("version") else "")
        overrides = tailoring.get("overrides") or []
        if overrides:
            line += " Overrides in force: " + "; ".join(
                "%s (%s — %s)" % (o.get("rule", "?"), o.get("reason", "no reason"),
                                  o.get("authorised_by", "unauthorised"))
                for o in overrides)
        preview += [line, ""]
    elif bundle.get("tailoring") is not None or get(cfg, "tailoring.source", ""):
        preview += ["_Untailored: no team house rules were applied to this refinement._", ""]
    if warnings:
        preview += ["> Notes:"] + ["> - %s" % w for w in warnings] + [""]
    if delta:
        preview += ["## Re-refinement", "",
                    "This is an update, not a first pass. Update the existing tree; do not "
                    "create a second one.", ""]
        preview.append("- **parent story**: %s" % ("changed - update it"
                                                    if delta["story_changed"] else "unchanged"))
        for label, ids in sorted(delta.items()):
            if isinstance(ids, list) and ids:
                preview.append("- **%s**: %s" % (label.replace("_", " "), ", ".join(ids)))
        preview.append("")
    if links:
        preview += ["## Links to create", "",
                    "| From | Type | To | As the tracker calls it | Already there |",
                    "|---|---|---|---|---|"]
        for l in links:
            preview.append("| %s | %s | %s | %s | %s |"
                           % (l["from"], l["type"], l["to"],
                              l.get("adapter_type") or "_unsupported_",
                              "yes" if l["already_present"] else "no"))
        for l in links:
            if l.get("degraded"):
                preview.append("")
                preview.append("> %s → %s: %s" % (l["type"], l["to"], l["degraded"]))
        preview.append("")
    preview += ["## Execution waves", "",
                "Everything inside a wave can run in parallel. No two subtasks in the same "
                "wave write the same file.", ""]
    for w in plan_waves:
        preview.append("- **Wave %d**: %s%s" % (w["wave"], ", ".join(w["subtasks"]),
                                                " — %s" % w["note"] if w.get("note") else ""))
    preview += [""] + triage_section(bundle) + review_section(bundle)
    preview += ["", "_Field names and issue types below are unverified `[?]` until probed "
                "against the live tracker._", "", "---", ""]
    for item in items:
        preview += ["## %s — %s (%s)" % (item["id"], item["title"], item["issue_type"]), "",
                    item["body"], "", "---", ""]
    with open(os.path.join(args.out, "preview.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(preview))

    # A push plan for a bundle that does not validate must not look pushable. It is
    # still rendered - a preview is how you discuss a story that is not ready yet -
    # but nothing downstream gets to mistake it for a green one.
    report = validate(json.loads(json.dumps(bundle)), cfg)
    blocking = [i for i in report.items if i["severity"] == "ERROR"]

    plan = {
        "ready": not blocking,
        "blocking": [{"code": i["code"], "where": i["where"], "message": i["message"]}
                     for i in blocking[:10]],
        "adapter": adapter, "project": get(cfg, "tracker.project", ""),
        "capabilities": {k: v for k, v in caps.items() if not k.startswith("_")},
        "agent_brief_sink": sink,
        "agent_brief_sink_per_subtask": sinks,
        "warnings": warnings,
        "mode": "update" if delta else "create",
        "diff": delta,
        # In update mode the parent already exists: it is never created again.
        "creates": [{"id": i["id"], "title": i["title"], "issue_type": i["issue_type"],
                     "parent": i.get("parent")} for i in items
                    if (not delta and True) or (delta and i["role"] == "subtask"
                                                and i["id"] in delta["subtasks_added"])],
        "updates": ([key] if delta and delta["story_changed"] else [])
                   + [i["id"] for i in items if delta and i["role"] == "subtask"
                      and i["id"] in delta["subtasks_changed"]],
        "orphans": delta["subtasks_removed"] if delta else [],
        # An orphan nobody has touched is a plan change. An orphan that shipped is a
        # deletion of work that exists, and the two must not read the same.
        "orphans_already_underway": sorted(
            sid for sid in (delta["subtasks_removed"] if delta else [])
            if ((prior_progress or {}).get("subtasks") or {}).get(sid) in ("done", "started")),
        "waves": plan_waves,
        "shared_context": "context/%s" % ctx_name,
        "links": links,
        "idempotency": "search for existing subtasks by exact title under %s before creating" % key,
        "network": "none - this file is a plan, not an action",
    }
    with open(os.path.join(args.out, "push-plan.json"), "w", encoding="utf-8") as fh:
        json.dump(plan, fh, indent=2)

    print("wrote %s/preview.md, push-plan.json, context/%s, %d payload(s), default sink=%s, "
          "%d wave(s)" % (args.out, ctx_name, len(items), sink, len(plan_waves)))
    if delta and plan["orphans_already_underway"]:
        print("  ! %s were dropped from the plan and are already done or in progress. That is "
              "not a plan change, it is deleting work that exists - say so before pushing."
              % ", ".join(plan["orphans_already_underway"]))
    if delta:
        print("  mode=update: +%d subtask(s), ~%d changed, -%d orphaned"
              % (len(delta["subtasks_added"]), len(delta["subtasks_changed"]),
                 len(delta["subtasks_removed"])))
    for w in warnings:
        print("  note: %s" % w)
    if blocking:
        print("NOT READY  %d blocking finding(s); push-plan.json is stamped ready=false."
              % len(blocking))
        print("Show preview.md and the findings. Do not push. Run validate.py for the list.")
        return 0 if args.allow_not_ready else 1
    print("Show preview.md to the user. Do not push until they approve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
