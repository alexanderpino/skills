#!/usr/bin/env python3
"""Mechanical readiness gate for a story-refinery bundle. Stdlib only.

  python validate.py bundle.json --config refinery.yaml [--json] [--strict]

Exit codes: 0 ready, 1 errors found, 2 usage/parse error.
Readiness is decided here, not in a meeting. A failing bundle is a finding:
report the specific questions, do not delete them to pass the gate.
"""

import argparse
import itertools
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _yaml import get, load_config  # noqa: E402
from review import SEVERITIES, STATUSES, content_digest, resolve_locator  # noqa: E402
from triage import policy_for as triage_policy  # noqa: E402

DEFAULT_LEXICON = [
    "etc.", "and so on", "as needed", "appropriately", "properly",
    "handle gracefully", "should probably", "if necessary", "where applicable",
    "user-friendly", "robust", "various", "improve performance",
]
UNCOVERED_OK_KINDS = {"enabling", "spike", "rollout"}
PATH_RX = re.compile(r"\b[\w.-]+(?:/[\w.-]+)+\.[A-Za-z0-9]{1,6}\b")
DEFAULT_NFR_KEYS = ["performance", "concurrency", "failure", "data", "security",
                    "observability", "compatibility"]
# Quality attributes where an answer without a number is not an answer. The rest
# (security, compatibility, observability) are answered categorically.
DEFAULT_MEASURED_NFR_KEYS = ["performance", "concurrency", "failure"]
UNCHANGED_RX = re.compile(r"\bunchanged\b|\bongewijzigd\b|\bn\.?v\.?t\.?\b|\bnone\b|\bgeen\b", re.I)
# Threshold language: a rule that draws a line needs an example standing on it.
THRESHOLD_RX = re.compile(
    r"\d|\bmore than\b|\bless than\b|\bat least\b|\bat most\b|\bexceed\w*\b|\babove\b|"
    r"\bbelow\b|\bover\b|\bunder\b|\blimit\b|\bmaximum\b|\bminimum\b|\bolder than\b|"
    r"\bmeer dan\b|\bminder dan\b|\bminimaal\b|\bmaximaal\b|\blimiet\b|\bboven\b|\bouder dan\b",
    re.I)
BOUNDARY_RX = re.compile(r"boundary|grens|edge case|randgeval", re.I)
CYNEFIN_DOMAINS = ("clear", "complicated", "complex", "chaotic")
# What a team-tailoring skill may never relax. Each exists to stop the output being
# confidently wrong; see references/tailoring.md. Every gate in this skill can be
# switched off in config - `disclosure` is what keeps that legitimate.
INVARIANTS = ("evidence-or-assumption", "no-invented-metadata", "not-ready-is-reported",
              "no-decomposition-without-intake", "stop-at-the-seam", "disclosure")
# Beyond this, the table is telling you the story is too big to refine as one.
MAX_TABLE_COMBINATIONS = 512

# Every key the scripts actually read. Anything else in refinery.yaml is a typo or a
# leftover, and is reported rather than silently ignored.
CONFIG_SPEC = {
    "": {"version", "profile", "tailoring", "decomposition", "budgets", "tracker",
         "evidence", "intake", "triage", "gates", "review", "validation"},
    "decomposition": {"one_repo_per_subtask", "one_pr_per_subtask", "title_pattern",
                      "mandatory", "spike_when_unresolved", "spike_timebox_days"},
    "decomposition.mandatory[]": {"kind", "when"},
    "budgets": {"story_summary_words", "technical_notes_words", "subtask_words",
                "max_subtasks", "max_files_per_subtask", "max_subtask_days",
                "min_acceptance_criteria", "max_acceptance_criteria"},
    "tracker": {"adapter", "project", "markup", "story_issue_type", "subtask_issue_type",
                "parent_field", "max_description_chars", "labels_prefix", "agent_brief"},
    "tracker.agent_brief": {"sink", "fallback", "filename", "repo_file_dir", "custom_field",
                            "marker_begin", "marker_end"},
    "evidence": {"sources", "repos", "contract_globs", "split_thresholds"},
    "evidence.sources[]": {"type", "path", "adapter", "dir", "ttl_days",
                           "budget_files", "budget_seconds"},
    "evidence.repos[]": {"name", "path"},
    "evidence.split_thresholds": {"repos", "files", "breaking_contracts", "owner_teams"},
    "gates": {"design_decisions", "push", "adversarial_review"},
    "tailoring": {"source", "version", "skill"},
    "triage": {"capture", "ignore", "labels"},
    "triage.labels[]": {"id", "match", "field", "kind", "profile", "route",
                        "require_dimensions", "mandatory_subtask_kinds", "add_critics",
                        "must_answer_nfr", "ask"},
    "review": {"method", "panel", "min_critics", "rubber_duck_max_subtasks",
               "require_fresh_context"},
    "intake": {"feature_required", "feature_recommended", "bug_required", "bug_recommended",
               "min_anchors"},
    "validation": {"fail_on", "require_command_done_when", "require_coverage_matrix",
                   "vagueness_lexicon", "non_functional_keys", "definition_of_done",
                   "require_intake", "measured_non_functional_keys"},
    "validation.definition_of_done[]": {"id", "applies_to_kinds",
                                        "expect_command_matching", "severity"},
}


class Report:
    def __init__(self):
        self.items = []

    def add(self, severity, code, where, message):
        self.items.append({"severity": severity, "code": code, "where": where,
                           "message": message})

    error = lambda self, c, w, m: self.add("ERROR", c, w, m)   # noqa: E731
    warn = lambda self, c, w, m: self.add("WARN", c, w, m)     # noqa: E731

    def count(self, severity):
        return sum(1 for i in self.items if i["severity"] == severity)


def words(text):
    return len((text or "").split())


def find_vague(text, lexicon):
    low = (text or "").lower()
    return [term for term in lexicon if term in low]


# ------------------------------------------------------------------ validators

def check_structure(b, rep):
    for key in ("schema_version", "story", "subtasks"):
        if key not in b:
            rep.error("STRUCT001", "$", "missing top-level key %r" % key)
    story = b.get("story") or {}
    for key in ("key", "title", "summary_human", "acceptance_criteria"):
        if not story.get(key):
            rep.error("STRUCT002", "story", "missing or empty %r" % key)
    if not b.get("subtasks"):
        rep.error("STRUCT003", "subtasks", "no subtasks - nothing was decomposed")


def check_questions_and_decisions(b, rep):
    for q in b.get("open_questions") or []:
        where = "open_questions.%s" % q.get("id", "?")
        if q.get("blocking"):
            rep.error("READY001", where,
                      "blocking question unresolved: %s (owner: %s)"
                      % (q.get("text", "?"), q.get("owner") or "UNASSIGNED"))
        if not q.get("owner"):
            rep.warn("READY002", where, "question has no owner - it will not get answered")
        # A question filed in a bundle nobody has read is a note to yourself. The
        # asking is the deliverable; the record is only proof it happened.
        if not q.get("asked") and not q.get("answer"):
            if q.get("blocking"):
                rep.error("READY003", where, "blocking question that was never put to anyone - "
                          "ask it now, with your best guess attached, rather than filing it "
                          "and continuing")
            else:
                rep.warn("READY003", where, "recorded but never asked - put it to someone "
                         "while you still have their attention, or say why it can wait")

    by_id = {s.get("id"): s for s in b.get("subtasks") or []}
    ids = set(by_id)
    for d in b.get("decisions") or []:
        where = "decisions.%s" % d.get("id", "?")
        status = d.get("status")
        if status not in ("locked", "deferred"):
            rep.error("DEC001", where, "status must be 'locked' or 'deferred', got %r" % status)
        if status == "locked":
            if not d.get("chosen"):
                rep.error("DEC002", where, "locked decision has no 'chosen' option")
            if not d.get("rationale"):
                rep.error("DEC003", where, "locked decision has no rationale - it cannot be challenged later")
        if status == "deferred":
            spike = d.get("spike")
            if not spike:
                rep.error("DEC004", where, "deferred decision has no spike subtask")
            elif spike not in ids:
                rep.error("DEC005", where, "spike %r is not a subtask in this bundle" % spike)
            elif by_id[spike].get("kind") != "spike":
                rep.error("DEC006", where, "subtask %s is kind %r, not 'spike' - a deferred "
                          "decision needs a timeboxed question, not ordinary work"
                          % (spike, by_id[spike].get("kind")))
            # Real Options [P: Maassen & Matts, Commitment, 2013]: an option has value
            # only while it is open, and every option expires. Deferring without an
            # expiry is not keeping your choices open, it is forgetting to choose.
            if not d.get("expires"):
                rep.error("DEC007", where, "deferred with no expiry - name the event or date "
                          "after which deferring costs more than deciding, or this is not a "
                          "held option, it is an unmade decision")
            if not d.get("waiting_for"):
                rep.error("DEC008", where, "deferred without naming what it is waiting for - "
                          "an option nobody can tell has matured never gets exercised")


def check_acceptance_criteria(b, cfg, rep):
    lexicon = get(cfg, "validation.vagueness_lexicon", DEFAULT_LEXICON) or DEFAULT_LEXICON
    lo = get(cfg, "budgets.min_acceptance_criteria", 2)
    hi = get(cfg, "budgets.max_acceptance_criteria", 7)
    acs = (b.get("story") or {}).get("acceptance_criteria") or []
    if len(acs) < lo:
        rep.error("AC001", "story.acceptance_criteria",
                  "%d criteria, minimum %d" % (len(acs), lo))
    if len(acs) > hi:
        rep.warn("AC002", "story.acceptance_criteria",
                 "%d criteria (>%d) - this reads like a story that should be split" % (len(acs), hi))
    seen = set()
    for ac in acs:
        where = "AC %s" % ac.get("id", "?")
        if not ac.get("id"):
            rep.error("AC003", where, "criterion has no id")
        elif ac["id"] in seen:
            rep.error("AC004", where, "duplicate criterion id")
        else:
            seen.add(ac["id"])
        if not ac.get("rule"):
            rep.error("AC005", where, "criterion has no rule text")
        if not ac.get("examples"):
            rep.error("AC006", where, "rule has no concrete example - it is not understood yet")
        vague = find_vague(ac.get("rule", ""), lexicon)
        if vague:
            rep.error("AC007", where, "vague terms in an acceptance criterion: %s"
                      % ", ".join(vague))


def check_example_coverage(b, rep):
    """Examples are not illustrations, they are the test cases. A rule that names
    three inputs and shows one has two branches nobody has thought about, and a rule
    that draws a line with no example standing on it will be implemented off by one.
    `[P: Myers, equivalence partitioning and boundary value analysis, 1979]`"""
    lang = ((b.get("story") or {}).get("intake") or {}).get("lang")
    connector = r"\bof\b" if lang == "nl" else r"\bor\b"
    for ac in (b.get("story") or {}).get("acceptance_criteria") or []:
        where = "AC %s" % ac.get("id", "?")
        rule, examples = ac.get("rule") or "", ac.get("examples") or []
        alternatives = len(re.findall(connector, rule, re.I)) + 1
        if alternatives > 1 and len(examples) < alternatives:
            rep.warn("AC008", where, "the rule names %d alternatives but carries %d "
                     "example(s) - partition the inputs and show one per class"
                     % (alternatives, len(examples)))
        if THRESHOLD_RX.search(rule) and not any(
                BOUNDARY_RX.search(str(e.get("case", ""))) for e in examples):
            rep.warn("AC009", where, "the rule draws a line but no example stands on it - "
                     "add the value exactly at the threshold, or it will be implemented "
                     "off by one")


def check_decision_table(b, rep):
    """A decision table is the only form that can be proved complete: every
    combination of conditions is a rule, an impossibility, or a hole `[F]`."""
    table = (b.get("story") or {}).get("decision_table")
    if not table:
        return
    conditions = table.get("conditions") or []
    if not conditions:
        rep.error("DT002", "story.decision_table", "table with no conditions")
        return
    values = {}
    for cond in conditions:
        cid, vals = cond.get("id"), cond.get("values") or []
        if not cid or not vals:
            rep.error("DT002", "story.decision_table",
                      "condition %r has no id or no values" % cid)
            continue
        values[cid] = [str(v) for v in vals]
    if not values:
        return

    ac_ids = {a.get("id") for a in (b.get("story") or {}).get("acceptance_criteria") or []}
    rules = table.get("rules") or []
    for i, rule in enumerate(rules):
        where = "story.decision_table.rules[%d]" % i
        for cid, val in (rule.get("when") or {}).items():
            if cid not in values:
                rep.error("DT002", where, "unknown condition %r" % cid)
            elif str(val) != "*" and str(val) not in values[cid]:
                rep.error("DT002", where, "condition %r has no value %r (known: %s)"
                          % (cid, val, ", ".join(values[cid])))
        if not rule.get("then"):
            rep.error("DT002", where, "rule has no outcome")
        if rule.get("ac") and rule["ac"] not in ac_ids:
            rep.error("DT002", where, "cites unknown criterion %r" % rule["ac"])

    total = 1
    for vals in values.values():
        total *= len(vals)
    if total > MAX_TABLE_COMBINATIONS:
        rep.warn("DT004", "story.decision_table", "%d combinations - a table this wide is "
                 "a story that should be split, not a story that should be refined" % total)
        return

    def matches(spec, combo):
        for cid, val in (spec or {}).items():
            if str(val) == "*":
                continue
            if combo.get(cid) != str(val):
                return False
        return True

    ordered = sorted(values)
    uncovered = []
    for point in itertools.product(*(values[c] for c in ordered)):
        combo = dict(zip(ordered, point))
        hits = [r for r in rules if matches(r.get("when"), combo)]
        if not hits:
            if not any(matches(imp, combo) for imp in table.get("impossible") or []):
                uncovered.append(combo)
            continue
        outcomes = {str(r.get("then")) for r in hits}
        if len(outcomes) > 1:
            rep.error("DT003", "story.decision_table",
                      "%s matches %d rules with different outcomes - the table contradicts "
                      "itself" % (", ".join("%s=%s" % kv for kv in sorted(combo.items())),
                                  len(hits)))
    for combo in uncovered[:5]:
        rep.error("DT001", "story.decision_table",
                  "no rule and no impossibility for %s - a branch nobody wrote is a branch "
                  "nobody implements" % ", ".join("%s=%s" % kv for kv in sorted(combo.items())))
    if len(uncovered) > 5:
        rep.error("DT001", "story.decision_table",
                  "%d further uncovered combinations" % (len(uncovered) - 5))


def check_risks(b, rep):
    """A premortem that produced no risks was not a premortem `[P: Klein, 2007]`.
    A risk you cannot detect is a risk you will hear about from a customer."""
    risks = (b.get("story") or {}).get("risks") or []
    subs = b.get("subtasks") or []
    exposed = ((b.get("blast_radius") or {}).get("repos") or 0) > 1 or \
        any(s.get("kind") in ("rollout", "migration") for s in subs)
    if not risks and exposed and subs:
        rep.warn("RSK003", "story.risks", "no risks recorded on a change that crosses repos "
                 "or ships behind a rollout - run the premortem: it is three months later "
                 "and this caused an incident, write the postmortem")
    for r in risks:
        where = "risk %s" % r.get("id", "?")
        if not r.get("mitigation"):
            rep.error("RSK001", where, "risk with no mitigation - it is a worry, not a plan")
        if str(r.get("severity", "")).lower() == "high" and not r.get("detection"):
            rep.warn("RSK002", where, "high risk with no detection signal - name the alert, "
                     "metric or report that tells you it is happening")


def check_domain(b, rep):
    """Cynefin `[P: Snowden & Boone, 2007]`. Enough information is not the same as
    enough knowledge: in a complex domain the honest output is a probe, not a plan."""
    intake = (b.get("story") or {}).get("intake") or {}
    if not intake:
        return
    domain = intake.get("domain")
    subs = b.get("subtasks") or []
    if domain is None:
        if subs:
            rep.warn("CYN003", "story.intake.domain", "nobody said whether this problem is "
                     "knowable up front - classify it %s" % " | ".join(CYNEFIN_DOMAINS))
        return
    if domain not in CYNEFIN_DOMAINS:
        rep.error("CYN003", "story.intake.domain", "domain must be %s, got %r"
                  % (" | ".join(CYNEFIN_DOMAINS), domain))
        return
    if domain == "complex" and subs and not any(s.get("kind") == "spike" for s in subs):
        rep.error("CYN001", "story.intake.domain", "domain is 'complex' and the bundle plans "
                  "%d subtask(s) with no spike - in a complex domain the answer is not "
                  "knowable in advance; probe first and decompose what the probe returns"
                  % len(subs))
    if domain == "chaotic" and subs:
        rep.warn("CYN002", "story.intake.domain", "domain is 'chaotic' - refinement is the "
                 "wrong instrument; act to stabilise, then refine what is left")


def check_impact(b, rep):
    """The intake gate catches a mechanism with no outcome. This is the other half:
    once someone answers, the answer is recorded as a chain, not as prose
    `[P: Adzic, Impact Mapping, 2012]`."""
    intake = (b.get("story") or {}).get("intake") or {}
    flags = [str(f) for f in intake.get("flags") or []]
    impact = (b.get("story") or {}).get("impact")
    if any("mechanism" in f for f in flags) and not impact:
        rep.warn("IMP001", "story.impact", "intake flagged this as a mechanism with no stated "
                 "outcome - record goal, actor, impact and deliverable so the mechanism can "
                 "be argued with")
    if not impact:
        return
    if not (impact.get("goal") or "").strip():
        rep.error("IMP002", "story.impact", "no goal - an impact map without a measurable "
                  "goal is a feature list")
    if not THRESHOLD_RX.search(impact.get("goal") or ""):
        rep.warn("IMP002", "story.impact", "the goal carries no number - 'fewer manual "
                 "refunds' cannot tell you afterwards whether this worked")


def check_budgets(b, cfg, rep):
    lexicon = get(cfg, "validation.vagueness_lexicon", DEFAULT_LEXICON) or DEFAULT_LEXICON
    story = b.get("story") or {}
    limits = [
        ("summary_human", get(cfg, "budgets.story_summary_words", 120)),
        ("technical_notes_human", get(cfg, "budgets.technical_notes_words", 200)),
    ]
    for field, limit in limits:
        n = words(story.get(field))
        if limit and n > limit:
            rep.warn("BUD001", "story.%s" % field,
                     "%d words (budget %d) - cut what a colleague already knows" % (n, limit))
        vague = find_vague(story.get(field), lexicon)
        if vague:
            rep.warn("BUD002", "story.%s" % field, "vague terms: %s" % ", ".join(vague))
    if not story.get("technical_notes_human"):
        rep.error("BUD003", "story.technical_notes_human",
                  "empty - a refinement with no technical notes is a reworded ticket")
    if not story.get("non_goals"):
        rep.warn("BUD004", "story.non_goals",
                 "no non-goals - cheapest scope control available, and the most useful "
                 "single field for an agent implementor")
    if not story.get("source_text"):
        rep.warn("BUD005", "story.source_text",
                 "the original ask was not recorded - scope creep cannot be checked "
                 "against anything")


def check_evidence(b, rep):
    ev = b.get("evidence") or {}
    surface = ev.get("change_surface") or []
    if not surface:
        rep.error("EVI001", "evidence.change_surface",
                  "empty - Phase 2 was skipped; go read the code")
    for i, entry in enumerate(surface):
        where = "evidence.change_surface[%d]" % i
        if not entry.get("repo") or not entry.get("path"):
            rep.error("EVI002", where, "entry needs both repo and path")
        if entry.get("role") not in ("touch", "read", "create", "modify", "delete", None):
            rep.warn("EVI003", where, "unusual role %r" % entry.get("role"))
    if not ev.get("repos"):
        rep.warn("EVI004", "evidence.repos", "no repos recorded - provenance is unverifiable")

    known = {"%s/%s" % (e.get("repo"), e.get("path")) for e in surface}
    known |= {e.get("path") for e in surface}
    notes = (b.get("story") or {}).get("technical_notes_human") or ""
    for path in set(PATH_RX.findall(notes)):
        if not any(path in k for k in known if k):
            rep.warn("EVI005", "story.technical_notes_human",
                     "path %r cited in notes but absent from change_surface - verify it exists" % path)

    # Negative results are the most expensive thing a refinement learns and the
    # first thing compression throws away. An implementor who does not know a
    # helper is absent will go looking for it, and may "find" the wrong one.
    ruled_out = ev.get("ruled_out") or []
    if (b.get("blast_radius") or {}).get("repos", 0) > 1 and not ruled_out and b.get("subtasks"):
        rep.warn("EVI008", "evidence.ruled_out", "nothing was ruled out on a change across "
                 "more than one repo - you cannot have read two codebases and learned nothing "
                 "that is absent; record what you looked for and did not find")
    for i, entry in enumerate(ruled_out):
        where = "evidence.ruled_out[%d]" % i
        if not entry.get("looked_in"):
            rep.error("EVI009", where, "a negative result with no record of where you looked "
                      "is a rumour - name the paths, globs or queries")
        if not entry.get("conclusion"):
            rep.error("EVI009", where, "no conclusion - say what an implementor should do "
                      "given the absence, not just that it is absent")

    br = b.get("blast_radius") or {}
    if br.get("repos", 0) > 1 and not (ev.get("contracts") or []):
        rep.error("EVI006", "evidence.contracts",
                  "%d repos change but no contract recorded - find the seam and order across it"
                  % br.get("repos"))


def check_subtasks(b, cfg, rep):
    max_days = get(cfg, "budgets.max_subtask_days", 1.0)
    max_files = get(cfg, "budgets.max_files_per_subtask", 8)
    max_subtasks = get(cfg, "budgets.max_subtasks", 12)
    word_budget = get(cfg, "budgets.subtask_words", 80)
    require_cmd = get(cfg, "validation.require_command_done_when", True)

    subs = b.get("subtasks") or []
    if len(subs) > max_subtasks:
        rep.warn("SUB001", "subtasks", "%d subtasks (>%d) - merge to reviewable units or split "
                                       "the story" % (len(subs), max_subtasks))
    ids, titles = set(), set()
    ac_ids = {a.get("id") for a in (b.get("story") or {}).get("acceptance_criteria") or []}

    for s in subs:
        sid = s.get("id") or "?"
        where = "subtask %s" % sid
        if sid in ids:
            rep.error("SUB002", where, "duplicate subtask id")
        ids.add(sid)
        title = (s.get("title") or "").strip()
        if not title:
            rep.error("SUB003", where, "subtask has no title")
        if title.lower() in titles:
            rep.error("SUB004", where, "duplicate subtask title")
        titles.add(title.lower())
        if len(title) > 70:
            rep.warn("SUB005", where, "title is %d chars - trackers truncate at ~70" % len(title))
        if re.search(r"\band\b|\s&\s", title, re.I):
            rep.warn("SUB006", where, "title contains a conjunction - probably two subtasks")
        if not s.get("repo"):
            rep.error("SUB007", where, "subtask has no repo - one subtask = one repo = one PR")
        if words(s.get("human")) > word_budget:
            rep.warn("SUB008", where, "human text %d words (budget %d)"
                     % (words(s.get("human")), word_budget))
        if not s.get("human"):
            rep.error("SUB009", where, "no human-facing text")
        est = s.get("estimate_days")
        if est is None:
            rep.warn("SUB010", where, "no estimate_days - sizing cannot be checked")
        elif max_days and est > max_days:
            rep.error("SUB011", where, "estimate %.2fd exceeds %.2fd - not decomposed yet"
                      % (est, max_days))

        covers = s.get("covers") or []
        for cid in covers:
            if cid not in ac_ids:
                rep.error("SUB012", where, "covers unknown criterion %r" % cid)
        if not covers and s.get("kind") not in UNCOVERED_OK_KINDS:
            rep.error("SUB013", where,
                      "covers no acceptance criterion and kind %r is not enabling/spike/rollout"
                      % s.get("kind"))

        _check_brief(s, where, max_files, require_cmd, rep)

    for s in subs:
        for dep in s.get("depends_on") or []:
            if dep not in ids:
                rep.error("SUB014", "subtask %s" % s.get("id"),
                          "depends_on unknown subtask %r" % dep)
    return subs, ids


def _check_brief(s, where, max_files, require_cmd, rep):
    brief = s.get("agent_brief")
    if not brief:
        rep.error("BRF001", where, "no agent_brief")
        return
    for key in ("objective", "repo", "read_first", "change_surface", "done_when"):
        if not brief.get(key):
            rep.error("BRF002", where, "agent_brief missing %r" % key)
    if brief.get("repo") and s.get("repo") and brief["repo"] != s["repo"]:
        rep.error("BRF003", where, "agent_brief.repo %r != subtask.repo %r"
                  % (brief["repo"], s["repo"]))
    surface = brief.get("change_surface") or []
    if max_files and len(surface) > max_files:
        rep.error("BRF004", where, "%d files in change_surface (max %d) - split the subtask"
                  % (len(surface), max_files))
    for entry in surface:
        if entry.get("role") not in ("create", "modify", "delete"):
            rep.warn("BRF005", where, "change_surface role should be create/modify/delete, got %r"
                     % entry.get("role"))
    dw = brief.get("done_when") or []
    if require_cmd and not any(d.get("type") == "command" for d in dw):
        rep.error("BRF006", where, "no runnable command in done_when - there is no mechanical gate")
    for d in dw:
        if d.get("type") == "command" and not d.get("cmd"):
            rep.error("BRF007", where, "command done_when with no cmd")
        if d.get("type") == "assertion" and words(d.get("text")) < 5:
            rep.warn("BRF008", where, "assertion too vague to write a test from: %r" % d.get("text"))
    for conv in brief.get("conventions") or []:
        if ":" not in (conv.get("evidence") or ""):
            rep.error("BRF009", where,
                      "convention without path:line evidence - that is a training prior, "
                      "not a house rule: %r" % conv.get("rule"))
    if not brief.get("forbidden"):
        rep.warn("BRF010", where, "no 'forbidden' entries - nothing stops scope creep")
    if not brief.get("out_of_scope"):
        rep.warn("BRF011", where, "no 'out_of_scope' entries")
    # Anchors drift between refinement and implementation. An agent that cannot
    # tell its brief has gone stale will implement against the brief anyway.
    if any(e.get("line") for e in brief.get("entry_points") or []) \
            and not brief.get("preflight"):
        rep.warn("BRF013", where, "entry points carry line numbers and nothing verifies them - "
                 "add a preflight command so the agent finds out the anchor moved instead of "
                 "editing whatever is at that line now")
    if not brief.get("stop_and_ask"):
        rep.warn("BRF014", where, "no 'stop_and_ask' - 'forbidden' says what not to touch, "
                 "this says when not to decide; without it an agent that finds reality "
                 "different from the brief improvises")
    blob = json.dumps(brief)
    if "```" in blob or re.search(r"\bdef \w+\(|\bfunction \w+\(|=>\s*\{", blob):
        rep.warn("BRF012", where,
                 "agent_brief looks like it contains implementation - refinement stops at the seam")


def transitive_deps(subs):
    """id -> set of ids it depends on, directly or transitively. Cycle-safe."""
    graph = {s.get("id"): [d for d in (s.get("depends_on") or [])] for s in subs}
    memo = {}

    def walk(node, stack):
        if node in memo:
            return memo[node]
        if node in stack:
            return set()
        acc = set()
        for dep in graph.get(node, []):
            if dep in graph:
                acc.add(dep)
                acc |= walk(dep, stack | {node})
        memo[node] = acc
        return acc

    return {n: walk(n, frozenset()) for n in graph}, graph


def check_graph(subs, reach, graph, rep):
    state = {}

    def visit(node, stack):
        if state.get(node) == "done":
            return
        if state.get(node) == "open":
            rep.error("DAG001", "subtasks", "dependency cycle: %s" % " -> ".join(stack + [node]))
            return
        state[node] = "open"
        for dep in graph.get(node, []):
            if dep in graph:
                visit(dep, stack + [node])
        state[node] = "done"

    for node in graph:
        visit(node, [])

    producers = {}
    for s in subs:
        for c in s.get("produces_contracts") or []:
            producers.setdefault(c, []).append(s.get("id"))
    for s in subs:
        for c in s.get("consumes_contracts") or []:
            for prod in producers.get(c, []):
                if prod == s.get("id"):
                    continue
                if prod not in reach.get(s.get("id"), set()):
                    rep.error("DAG002", "subtask %s" % s.get("id"),
                              "consumes contract %r produced by %s but does not depend on it - "
                              "producers ship first" % (c, prod))


def check_file_collisions(subs, reach, rep):
    """Two subtasks writing the same file is a merge conflict, and with parallel
    agent implementors it is two agents fighting over one buffer."""
    owners = {}
    for s in subs:
        for entry in (s.get("agent_brief") or {}).get("change_surface") or []:
            if entry.get("role") not in ("create", "modify", "delete"):
                continue
            owners.setdefault((s.get("repo"), entry.get("path")), []).append(s.get("id"))
    for (repo, path), ids in sorted(owners.items()):
        if len(ids) < 2:
            continue
        ordered = all(a in reach.get(b, set()) or b in reach.get(a, set())
                      for i, a in enumerate(ids) for b in ids[i + 1:])
        where = "%s/%s" % (repo, path)
        if ordered:
            rep.warn("PAR002", where, "written by %s in sequence - the later subtask rebases"
                     % ", ".join(ids))
        else:
            rep.error("PAR001", where,
                      "written by concurrent subtasks %s - add a dependency between them or give "
                      "the file to one subtask" % ", ".join(ids))


def check_contract_ids(bundle, subs, rep):
    known = {c.get("id") for c in (bundle.get("evidence") or {}).get("contracts") or []}
    for s in subs:
        for field in ("produces_contracts", "consumes_contracts"):
            for cid in s.get(field) or []:
                if cid not in known:
                    rep.error("CON001", "subtask %s" % s.get("id"),
                              "%s references %r which is not in evidence.contracts" % (field, cid))


def check_brief_surface(bundle, subs, rep):
    """A brief that edits a file the evidence never found is a path the agent will trust
    and may not exist. Created files are exempt - they cannot be evidenced."""
    known = {(e.get("repo"), e.get("path"))
             for e in (bundle.get("evidence") or {}).get("change_surface") or []}
    for s in subs:
        for entry in (s.get("agent_brief") or {}).get("change_surface") or []:
            if entry.get("role") in ("modify", "delete") and \
                    (s.get("repo"), entry.get("path")) not in known:
                rep.warn("EVI007", "subtask %s" % s.get("id"),
                         "brief edits %r but evidence.change_surface never recorded it - verify "
                         "the path exists before an agent trusts it" % entry.get("path"))


def check_split_thresholds(bundle, cfg, rep):
    th = get(cfg, "evidence.split_thresholds", {}) or {}
    br = bundle.get("blast_radius") or {}
    total_files = (br.get("files_primary") or 0) + (br.get("files_secondary") or 0)
    for key, value, label in (("repos", br.get("repos"), "repos"),
                              ("files", total_files, "files in the blast radius"),
                              ("owner_teams", br.get("owner_teams"), "owning teams"),
                              ("breaking_contracts", br.get("breaking_contracts"),
                               "breaking contract changes")):
        limit = th.get(key)
        if limit and value and value > limit:
            rep.warn("SPL001", "blast_radius",
                     "%s %s exceeds the split threshold of %s - recommend splitting the story "
                     "(report it, do not restructure the backlog unasked)" % (value, label, limit))


def check_one_repo_rule(cfg, subs, rep):
    if not get(cfg, "decomposition.one_repo_per_subtask", True):
        return
    for s in subs:
        repos = {s.get("repo")} | {e.get("repo") for e in
                                   (s.get("agent_brief") or {}).get("change_surface") or []
                                   if e.get("repo")}
        repos.discard(None)
        if len(repos) > 1:
            rep.error("SUB015", "subtask %s" % s.get("id"),
                      "spans repos %s - one subtask is one repo, one PR, one reviewable unit"
                      % ", ".join(sorted(repos)))


def check_coverage(b, subs, cfg, rep):
    if not get(cfg, "validation.require_coverage_matrix", True):
        return
    acs = (b.get("story") or {}).get("acceptance_criteria") or []
    computed = {}
    for s in subs:
        for cid in s.get("covers") or []:
            computed.setdefault(cid, []).append(s.get("id"))
    for ac in acs:
        if ac.get("id") and ac["id"] not in computed:
            rep.error("COV001", "AC %s" % ac["id"], "no subtask covers this criterion")
    declared = b.get("coverage")
    if declared is not None:
        norm = lambda m: {k: sorted(v or []) for k, v in m.items()}  # noqa: E731
        if norm(declared) != norm(computed):
            rep.warn("COV002", "coverage",
                     "declared coverage map disagrees with the subtasks - it is derived, "
                     "regenerate it rather than maintaining it by hand")


def check_nonfunctional(b, cfg, rep):
    expected = get(cfg, "validation.non_functional_keys", DEFAULT_NFR_KEYS) or DEFAULT_NFR_KEYS
    nf = (b.get("story") or {}).get("non_functional") or {}
    missing = [k for k in expected if not nf.get(k)]
    if missing:
        rep.warn("NFR001", "story.non_functional",
                 "unaddressed: %s (write 'unchanged' if that is the answer)" % ", ".join(missing))
    # A quality attribute scenario ends in a response measure [P: Bass, Clements &
    # Kazman]. For the attributes that are measurable, prose is not an answer.
    measured = get(cfg, "validation.measured_non_functional_keys",
                   DEFAULT_MEASURED_NFR_KEYS) or DEFAULT_MEASURED_NFR_KEYS
    for key in measured:
        answer = nf.get(key)
        text = answer if isinstance(answer, str) else json.dumps(answer or "")
        if not answer:
            continue
        if not re.search(r"\d", text) and not UNCHANGED_RX.search(text):
            rep.warn("NFR002", "story.non_functional.%s" % key,
                     "answered without a measure - give the stimulus and the number it must "
                     "stay under, or say 'unchanged'")


def check_definition_of_done(cfg, subs, rep):
    """The house DoD, expressed as commands a subtask must be able to run."""
    for rule in get(cfg, "validation.definition_of_done", []) or []:
        raw_kinds = rule.get("applies_to_kinds")
        if isinstance(raw_kinds, str):
            rep.error("DOD003", "config", "definition_of_done %r has applies_to_kinds as a "
                      "string (%r) - it must be a list, or the rule silently matches nothing"
                      % (rule.get("id"), raw_kinds))
            continue
        kinds = set(raw_kinds or [])
        try:
            rx = re.compile(rule.get("expect_command_matching") or ".", re.I)
        except re.error as exc:
            rep.error("DOD002", "config", "definition_of_done %r has a bad regex: %s"
                      % (rule.get("id"), exc))
            continue
        severity = str(rule.get("severity") or "error").lower()
        for s in subs:
            if kinds and s.get("kind") not in kinds:
                continue
            cmds = [d.get("cmd") or "" for d in (s.get("agent_brief") or {}).get("done_when") or []
                    if d.get("type") == "command"]
            if not any(rx.search(c) for c in cmds):
                report = rep.error if severity == "error" else rep.warn
                report("DOD001", "subtask %s" % s.get("id"),
                       "no done_when command satisfies definition of done %r (expects a command "
                       "matching /%s/)" % (rule.get("id"), rx.pattern))


def _norm(text):
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def check_intake(b, cfg, rep):
    """Was there enough information, and did anyone check? The intake block is the
    recorded answer; these gates hold the rest of the bundle to it."""
    if not get(cfg, "validation.require_intake", True):
        return
    story = b.get("story") or {}
    intake = story.get("intake")
    if not intake:
        rep.error("INT001", "story.intake", "no intake assessment - run "
                  "`intake.py assess --bundle bundle.json --write` before anything else")
        return
    verdict = intake.get("verdict")
    if verdict not in ("sufficient", "scoutable", "insufficient"):
        rep.error("INT002", "story.intake", "verdict must be sufficient | scoutable | "
                  "insufficient, got %r" % verdict)
        return
    if verdict != "sufficient" and b.get("subtasks"):
        rep.error("INT003", "story.intake", "verdict is %r but the bundle has %d subtask(s) - "
                  "the item was decomposed although the intake said to stop and ask"
                  % (verdict, len(b["subtasks"])))
    questions = {q.get("id"): q for q in b.get("open_questions") or []}
    source = _norm(story.get("source_text"))
    kind = intake.get("kind") or "feature"
    required = set(get(cfg, "intake.%s_required" % kind,
                       {"feature": ["actor", "outcome", "trigger"],
                        "bug": ["repro", "expected", "actual", "environment"]}[kind]) or [])
    # The ticket's own labels can demand more: a production finding needs to say
    # since when and how often before anyone knows what to reproduce.
    _, policy, _ = triage_policy(story.get("tracker_meta") or {}, cfg)
    required |= set(policy.get("require_dimensions") or [])
    seen = set()
    for d in intake.get("dimensions") or []:
        did = d.get("id") or "?"
        seen.add(did)
        where = "intake.%s" % did
        status = d.get("status")
        is_required = d.get("required", did in required)
        if status == "present":
            ev = _norm(d.get("evidence"))
            if not ev:
                rep.error("INT007", where, "marked present with no evidence quote")
            elif ev not in source:
                rep.error("INT007", where, "evidence %r does not occur in story.source_text - "
                          "a dimension is present only if the source text says so"
                          % (d.get("evidence") or "")[:60])
            if d.get("heuristic"):
                rep.warn("INT009", where, "still flagged heuristic - nobody confirmed the "
                         "matched snippet actually answers the question")
        elif status == "missing":
            if is_required:
                q = questions.get(d.get("question_id"))
                if not q:
                    rep.error("INT004", where, "required dimension missing with no linked "
                              "question - set question_id to a blocking open question")
                elif not q.get("blocking"):
                    rep.error("INT004", where, "required dimension missing but %s is not "
                              "blocking" % d.get("question_id"))
                if verdict == "sufficient":
                    rep.error("INT008", where, "verdict is 'sufficient' while a required "
                              "dimension is missing")
        elif status == "assumed":
            if not d.get("assumption"):
                rep.error("INT005", where, "marked assumed with no assumption text - an "
                          "unstated assumption cannot be corrected")
            q = questions.get(d.get("question_id"))
            if not q:
                rep.warn("INT006", where, "assumed without a linked question - the assumption "
                         "can never be confirmed or refuted")
            elif q.get("blocking"):
                rep.warn("INT006", where, "assumed but its question %s is blocking - either it "
                         "is missing, or the question should not block" % d.get("question_id"))
        elif status == "answered":
            if not d.get("answer") or not d.get("answered_by"):
                rep.error("INT010", where, "marked answered without both 'answer' and "
                          "'answered_by' - an answer with no source is an assumption")
        else:
            rep.error("INT002", where, "status must be present | missing | assumed | answered, "
                      "got %r" % status)
    for did in sorted(required - seen):
        rep.error("INT004", "intake.%s" % did, "required dimension not assessed at all")
    if kind == "bug" and (b.get("profile") or "") not in ("bugfix", ""):
        rep.warn("INT011", "profile", "intake says this is a bug but profile is %r - "
                 "the bugfix profile puts the failing test first" % b.get("profile"))


TICKET_RX = re.compile(r"\b[A-Z][A-Z0-9]{1,9}-\d+\b")


def check_series(b, rep):
    """Stories arrive in streams, not one at a time. Two things leak between them:
    evidence carried forward and never re-read, and the follow-ups a refinement
    creates and nobody records."""
    story = b.get("story") or {}
    ev = b.get("evidence") or {}
    stale = [(field, e) for field in ("glossary", "conventions", "ruled_out")
             for e in ev.get(field) or [] if e.get("stale")]
    if stale:
        rep.warn("SER001", "evidence", "%d entr(ies) carried from an earlier bundle are marked "
                 "stale and were never re-verified: %s. An inherited absence is the first thing "
                 "to stop being true - re-read it or drop it"
                 % (len(stale), ", ".join(sorted({f for f, _ in stale}))))

    follow_ups = {f.get("ticket") for f in story.get("follow_ups") or []}
    own_key = story.get("key")
    promised = set()
    for text in (story.get("non_goals") or []):
        promised |= set(TICKET_RX.findall(text or ""))
    for d in b.get("decisions") or []:
        if d.get("status") == "deferred":
            promised |= set(TICKET_RX.findall(d.get("expires") or ""))
    promised.discard(own_key)
    missing = sorted(t for t in promised if t not in follow_ups)
    if missing:
        rep.warn("SER002", "story.follow_ups", "the text points at %s and story.follow_ups does "
                 "not list them - the next refinement in this area will not find them, and a "
                 "non-goal with a ticket nobody tracks is a promise, not a scope boundary"
                 % ", ".join(missing))
    for f in story.get("follow_ups") or []:
        if not f.get("trigger"):
            rep.warn("SER002", "story.follow_ups", "follow-up %s with no trigger - say what "
                     "makes it start, or it sits in the backlog unread" % f.get("ticket", "?"))


def check_tailoring(b, cfg, rep):
    """Users layer a team-tailoring skill over this one. These gates keep the seam
    honest: what the team changed is recorded, what it claims is mechanical really
    is, what it turned off is disclosed, and the invariants are not negotiable."""
    declared = get(cfg, "tailoring.source", "") or ""
    tailoring = b.get("tailoring") or {}
    applied_source = tailoring.get("source") or ""

    if declared and not applied_source:
        rep.warn("TLR001", "tailoring", "config declares the %r tailoring but the bundle "
                 "records none - either the team skill was never loaded in this session, or "
                 "its rules were applied without being recorded" % declared)
    elif declared and applied_source != declared:
        rep.warn("TLR001", "tailoring", "config declares %r, bundle records %r"
                 % (declared, applied_source))

    for i, entry in enumerate(tailoring.get("applied") or []):
        where = "tailoring.applied[%d]" % i
        if not entry.get("rule"):
            rep.error("TLR002", where, "applied rule with no text")
        mechanism = entry.get("mechanism")
        if mechanism not in ("config", "prompt", "gate", None):
            rep.error("TLR002", where, "mechanism must be config | prompt | gate, got %r"
                      % mechanism)
        if mechanism == "config":
            key = entry.get("key")
            if not key:
                rep.error("TLR002", where, "claims to be enforced by config but names no key")
            elif get(cfg, key, None) is None:
                rep.error("TLR002", where, "claims config key %r enforces it, and that key is "
                          "not set - the rule reads as enforced and is not" % key)

    for i, entry in enumerate(tailoring.get("overrides") or []):
        where = "tailoring.overrides[%d]" % i
        target = entry.get("of") or ""
        if target in INVARIANTS:
            rep.error("TLR003", where, "overrides the %r invariant, which no tailoring may "
                      "relax - refuse it, record the refusal, and tell whoever owns the "
                      "tailoring skill" % target)
        if not entry.get("reason"):
            rep.error("TLR004", where, "override with no reason")
        if not entry.get("authorised_by"):
            rep.error("TLR004", where, "override with nobody's name on it - 'the team skill "
                      "says so' is not a person")

    # disclosure: a gate switched off is a legitimate choice that has to be visible.
    disclosed = " ".join(json.dumps(x) for x in
                         (tailoring.get("overrides") or []) + (tailoring.get("applied") or []))
    off = []
    if str(get(cfg, "gates.adversarial_review", "on")).lower() == "off":
        off.append("gates.adversarial_review")
    if get(cfg, "validation.require_intake", True) is False:
        off.append("validation.require_intake")
    fail_on = {str(s).lower() for s in (get(cfg, "validation.fail_on", ["error"]) or [])}
    if "error" not in fail_on:
        off.append("validation.fail_on")
    for key in off:
        if key not in disclosed:
            rep.warn("TLR005", "tailoring", "%s is switched off and nothing in the bundle "
                     "says so - a team may skip a gate, but a reader who cannot tell it was "
                     "skipped is being misled" % key)


def check_triage(b, cfg, rep):
    """What the tracker already said about this item, and whether the refinement
    listened. A label is a decision somebody made before you opened the ticket."""
    story = b.get("story") or {}
    meta = story.get("tracker_meta")
    subs = b.get("subtasks") or []
    if not meta:
        if subs:
            rep.warn("TRI001", "story.tracker_meta", "the ticket's own labels, components, "
                     "priority and links were never read - run `triage.py apply`; "
                     "'production-issue' or 'security' changes what this refinement is")
        return
    if not get(cfg, "triage.labels", None):
        return

    matched, policy, unknown = triage_policy(meta, cfg)
    recorded = story.get("triage") or {}
    if recorded:
        was = {m.get("id") for m in recorded.get("matched") or []}
        now = {m["id"] for m in matched}
        if was != now:
            rep.warn("TRI009", "story.triage", "the labels no longer produce the triage on "
                     "record (was %s, now %s) - somebody re-labelled the ticket; re-run "
                     "`triage.py apply`" % (", ".join(sorted(was)) or "none",
                                            ", ".join(sorted(now)) or "none"))

    if policy.get("route") == "incident" and subs:
        rep.error("TRI002", "story.triage", "the labels put this in incident handling and "
                  "the bundle decomposes it anyway - stabilise first, then refine what is "
                  "left (matched: %s)" % ", ".join(m["id"] for m in matched))

    kinds = {s.get("kind") for s in subs}
    for kind in policy.get("mandatory_subtask_kinds") or []:
        if subs and kind not in kinds:
            rep.error("TRI003", "subtasks", "the labels require a %r subtask and there is "
                      "none - %s" % (kind, ", ".join(m["id"] for m in matched)))

    assessed = {d.get("id") for d in (story.get("intake") or {}).get("dimensions") or []}
    for dim in policy.get("require_dimensions") or []:
        if dim not in assessed:
            rep.error("TRI004", "story.intake", "the labels require the %r dimension and "
                      "intake never assessed it - a production finding without %s is a "
                      "guess about what to reproduce" % (dim, dim))

    wanted_profile = policy.get("profile")
    if wanted_profile and b.get("profile") and b["profile"] != wanted_profile:
        rep.warn("TRI005", "profile", "labels imply the %r profile, bundle uses %r - switch "
                 "it or say why the labels are wrong" % (wanted_profile, b["profile"]))
    wanted_kind = policy.get("kind")
    got_kind = (story.get("intake") or {}).get("kind")
    if wanted_kind and got_kind and got_kind != wanted_kind:
        rep.warn("TRI005", "story.intake.kind", "labels imply kind %r, intake recorded %r"
                 % (wanted_kind, got_kind))

    nf = story.get("non_functional") or {}
    for key in policy.get("must_answer_nfr") or []:
        answer = nf.get(key)
        if not answer or UNCHANGED_RX.search(str(answer)):
            rep.warn("TRI006", "story.non_functional.%s" % key, "the labels make this one "
                     "concrete: %r cannot be blank or 'unchanged' on an item labelled %s"
                     % (key, ", ".join(m["id"] for m in matched)))

    critics = {c.get("id") for c in (b.get("review") or {}).get("critics") or []}
    if b.get("review"):
        for critic in policy.get("add_critics") or []:
            if critic not in critics:
                rep.warn("TRI008", "review.critics", "the labels call for the %r critic and "
                         "the panel did not include one" % critic)

    if unknown:
        rep.warn("TRI007", "story.tracker_meta", "no policy and no ignore rule covers %s - "
                 "decide whether they change the refinement, then record the decision in "
                 "triage.labels or triage.ignore" % ", ".join(unknown))


def check_review(b, cfg, rep):
    """Did anyone hostile read this before an implementer did?

    `validate.py` proves the bundle is well-formed; it cannot tell whether the plan
    is wrong. That judgement comes from critics who never saw the reasoning, and
    these gates hold the bundle to what they found."""
    mode = str(get(cfg, "gates.adversarial_review", "on") or "on").lower()
    review = b.get("review") or {}
    if mode == "off" and not review:
        return
    if not review:
        if b.get("subtasks"):
            rep.error("REV001", "review", "no adversarial review - nothing has criticised "
                      "this story or its subtasks; run `review.py brief`, run the panel, "
                      "and record what it found")
        return

    method = str(review.get("method") or get(cfg, "review.method", "critics")).lower()
    if method not in ("critics", "rubber-duck", "both"):
        rep.error("REV001", "review.method",
                  "method must be critics | rubber-duck | both, got %r" % review.get("method"))
        return

    digest = review.get("bundle_digest")
    current = content_digest(b)
    if not digest:
        rep.error("REV007", "review.bundle_digest", "review is not stamped - run "
                  "`review.py digest --bundle <bundle> --stamp` so it is provable which "
                  "content was reviewed")
    elif digest != current:
        rep.error("REV007", "review.bundle_digest", "the bundle changed after this review "
                  "(stamped %s, now %s) - a review of an earlier draft is not a review of "
                  "this one; re-run the affected critics"
                  % (str(digest)[:14], current[:14]))

    critics = review.get("critics") or []
    findings = review.get("findings") or []
    critic_ids = {c.get("id") for c in critics}

    if method in ("critics", "both"):
        minimum = get(cfg, "review.min_critics", 3)
        if minimum and len(critics) < minimum:
            rep.error("REV006", "review.critics",
                      "%d critic(s), minimum %d - one reviewer finds one class of problem"
                      % (len(critics), minimum))
    if method == "rubber-duck":
        limit = get(cfg, "review.rubber_duck_max_subtasks", 3)
        if limit and len(b.get("subtasks") or []) > limit:
            rep.warn("REV008", "review.method",
                     "rubber-ducking alone on %d subtasks (limit %d) - one voice with full "
                     "context misses what a blind critic catches; run the panel"
                     % (len(b.get("subtasks") or []), limit))

    for c in critics:
        if not any(f.get("critic") == c.get("id") for f in findings) and not c.get("attempted"):
            rep.warn("REV004", "review.critics.%s" % (c.get("id") or "?"),
                     "found nothing and recorded no 'attempted' note - a critic who reports "
                     "silence either did not look or was not blind")
    if not findings and method == "rubber-duck" and not review.get("attempted"):
        rep.warn("REV004", "review", "rubber-duck pass with no findings and no 'attempted' "
                 "note - say what you tried to break and why it held")

    for i, f in enumerate(findings):
        where = "review.findings.%s" % (f.get("id") or i)
        severity, status = f.get("severity"), f.get("status")
        if severity not in SEVERITIES:
            rep.error("REV009", where, "severity must be %s, got %r"
                      % (" | ".join(SEVERITIES), severity))
        if status not in STATUSES:
            rep.error("REV009", where, "status must be %s, got %r"
                      % (" | ".join(STATUSES), status))
        if critic_ids and f.get("critic") not in critic_ids:
            rep.error("REV009", where, "attributed to %r, who is not one of the recorded "
                      "critics" % f.get("critic"))
        if not f.get("failure"):
            rep.warn("REV009", where, "no 'failure' - a finding that does not name what "
                     "goes wrong downstream cannot be prioritised")
        resolved, _ = resolve_locator(b, f.get("locator"))
        if not resolved:
            rep.error("REV005", where, "locator %r does not resolve in this bundle - it "
                      "points at nothing an author can fix" % f.get("locator"))
        if severity == "blocking" and status == "open":
            rep.error("REV002", where, "blocking finding still open: %s"
                      % (f.get("claim") or "?"))
        if status in ("accepted", "disputed") and not f.get("resolution"):
            rep.error("REV003", where, "%s with no resolution - a finding cannot be waved "
                      "away silently; record the risk accepted or the rebuttal" % status)
        if status == "fixed" and not f.get("resolution"):
            rep.warn("REV003", where, "fixed with no note saying what changed")


def check_config(cfg, rep):
    """A typo'd config key is silently ignored, which is how a setting you think is
    enforced turns out not to be. Name them."""
    def walk(node, path):
        if isinstance(node, dict):
            spec = CONFIG_SPEC.get(path)
            for key in node:
                where = "%s.%s" % (path, key) if path else key
                if spec is not None and key not in spec:
                    rep.warn("CFG001", "config", "unknown key %r - it is being ignored" % where)
                walk(node[key], where)
        elif isinstance(node, list):
            for item in node:
                if isinstance(item, dict):
                    walk(item, path + "[]")

    walk(cfg, "")


# ------------------------------------------------------------------------ main

def validate(bundle, cfg):
    rep = Report()
    check_config(cfg, rep)
    check_structure(bundle, rep)
    check_tailoring(bundle, cfg, rep)
    check_series(bundle, rep)
    check_triage(bundle, cfg, rep)
    check_intake(bundle, cfg, rep)
    check_questions_and_decisions(bundle, rep)
    check_acceptance_criteria(bundle, cfg, rep)
    check_example_coverage(bundle, rep)
    check_decision_table(bundle, rep)
    check_domain(bundle, rep)
    check_impact(bundle, rep)
    check_risks(bundle, rep)
    check_budgets(bundle, cfg, rep)
    check_evidence(bundle, rep)
    subs, _ = check_subtasks(bundle, cfg, rep)
    reach, graph = transitive_deps(subs)
    check_graph(subs, reach, graph, rep)
    check_file_collisions(subs, reach, rep)
    check_contract_ids(bundle, subs, rep)
    check_brief_surface(bundle, subs, rep)
    check_one_repo_rule(cfg, subs, rep)
    check_definition_of_done(cfg, subs, rep)
    check_coverage(bundle, subs, cfg, rep)
    check_split_thresholds(bundle, cfg, rep)
    check_nonfunctional(bundle, cfg, rep)
    check_review(bundle, cfg, rep)
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle")
    ap.add_argument("--config", default="refinery.yaml")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = ap.parse_args(argv)

    try:
        with open(args.bundle, "r", encoding="utf-8") as fh:
            bundle = json.load(fh)
    except (OSError, ValueError) as exc:
        print("cannot read bundle: %s" % exc, file=sys.stderr)
        return 2

    cfg = load_config(args.config) if os.path.exists(args.config) else {}
    rep = validate(bundle, cfg)
    errors, warns = rep.count("ERROR"), rep.count("WARN")
    fail_on = {str(s).lower() for s in (get(cfg, "validation.fail_on", ["error"]) or ["error"])}
    if args.strict:
        fail_on.add("warn")
    ready = not (("error" in fail_on and errors) or
                 ({"warn", "warning"} & fail_on and warns))

    if args.json:
        print(json.dumps({"ready": ready, "errors": errors, "warnings": warns,
                          "findings": rep.items}, indent=2))
    else:
        for severity in ("ERROR", "WARN"):
            for item in [i for i in rep.items if i["severity"] == severity]:
                print("%-5s %-9s %-28s %s" % (severity, item["code"], item["where"],
                                              item["message"]))
        print("\n%s  %d error(s), %d warning(s)"
              % ("READY" if ready else "NOT READY", errors, warns))
        if errors:
            print("Report the findings. Do not delete open questions to pass the gate.")
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
