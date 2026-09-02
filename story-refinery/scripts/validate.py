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
# A subtask's kind is a switch, not a caption: it decides which Definition of Done
# applies (DOD001), whether the subtask must cover a criterion (SUB013), whether the
# de-clutter gates leave it alone, and whether it is the build a research item may
# not plan (SPK004). A kind nobody recognises matches none of those and quietly
# exempts the subtask from all of them - so the vocabulary is closed, and a house
# that needs another one adds it to decomposition.extra_subtask_kinds on purpose.
SUBTASK_KINDS = {"feature", "test", "docs", "migration", "rollout", "spike", "enabling"}
# What the item is, which decides which questions must be answered before it can be
# planned at all. A research item is not a feature with unknowns: asking it for an
# actor and an outcome gets you a plausible answer to the wrong question.
DEFAULT_REQUIRED_DIMENSIONS = {
    "feature": ["actor", "outcome", "trigger"],
    "bug": ["repro", "expected", "actual", "environment"],
    "spike": ["question", "decision", "timebox"],
    "enabling": ["unlocks", "cost_of_delay"],
}
INTAKE_KINDS = tuple(DEFAULT_REQUIRED_DIMENSIONS)
# intake.kind -> the profile that kind implies (INT011). Refining a bug without
# putting the failing test first, or a research item with a delivery profile, is
# refining the wrong shape of work.
PROFILE_FOR_KIND = {"bug": "bugfix", "spike": "research"}
# A leading dot is part of the path: `.github/workflows/x.yml` cited in the notes must
# compare equal to the same path in the change surface, not to `github/...`.
PATH_RX = re.compile(r"(?<![\w/])\.?[\w.-]+(?:/[\w.-]+)+\.[A-Za-z0-9]{1,6}\b")
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
# An instruction that is really config: a quantity with a unit, a bound, a command in
# backticks, or a label pattern. Owners, tone and escalation never match this.
MECHANICAL_RULE_RX = re.compile(
    r"\d+(\.\d+)?\s*(day|days|hour|hours|file|files|subtask|subtasks|word|words|criteria|"
    r"dag|dagen|uur|bestand|bestanden|subtaken|woorden|%)\b|"
    r"\b(at most|at least|no more than|maximum|minimum|max\.?|min\.?|hoogstens|minimaal|"
    r"maximaal|ten hoogste)\s+(a |an |een |half |halve )?\d*\s*\w+|"
    r"`[^`\s]+\s[^`]+`|"                                   # a command with an argument
    r"\blabel(s|led)?\b.*\b(means?|=>|->|→|betekent)\b", re.I)
# What a team-tailoring skill may never relax. Each exists to stop the output being
# confidently wrong; see references/tailoring.md. Every gate in this skill can be
# switched off in config - `disclosure` is what keeps that legitimate.
INVARIANTS = ("evidence-or-assumption", "no-invented-metadata", "not-ready-is-reported",
              "no-decomposition-without-intake", "stop-at-the-seam", "disclosure")
# Beyond this, the table is telling you the story is too big to refine as one.
MAX_TABLE_COMBINATIONS = 512
# Which phase a finding belongs to, so a half-written bundle reports "these four are
# yours right now" instead of thirty-three findings in one flat list.
PHASE_OF = {
    "CFG": "0 configure", "TLR": "0 configure",
    "TRI": "1 triage", "INT": "1 intake", "CYN": "1 intake", "IMP": "1 intake",
    "EVI": "2 evidence", "PND": "2 evidence", "SER": "2 evidence",
    "AC": "3 criteria", "DT": "3 criteria", "NFR": "3 criteria", "BUD": "3 criteria",
    "DEC": "4 decisions", "RSK": "4 decisions", "READY": "4 decisions",
    "SUB": "5 decompose", "DAG": "5 decompose", "PAR": "5 decompose", "SPK": "5 decompose",
    "IRR": "5 decompose", "BAS": "3 criteria", "ENB": "1 intake",
    "COV": "5 decompose", "CON": "5 decompose", "SPL": "5 decompose",
    "BRF": "6 briefs", "DOD": "6 briefs",
    "REV": "8 review", "LNK": "9 emit", "STRUCT": "0 configure", "LANG": "6 write",
    "BAT": "9 batch", "GRN": "2 evidence", "CPX": "5 decompose",
}


def phase_of(code):
    for prefix in sorted(PHASE_OF, key=len, reverse=True):
        if code.startswith(prefix):
            return PHASE_OF[prefix]
    return "9 other"

# Every key the scripts actually read. Anything else in refinery.yaml is a typo or a
# leftover, and is reported rather than silently ignored.
CONFIG_SPEC = {
    "": {"version", "profile", "tailoring", "decomposition", "budgets", "tracker",
         "evidence", "intake", "triage", "gates", "review", "validation", "complexity"},
    "complexity": {"thresholds"},
    "complexity.thresholds": {"repos", "code_paths", "files_written", "read_set", "contracts",
                              "breaking_contracts", "owner_teams", "rule_space", "forks",
                              "deferred", "unknowns", "irreversible", "critical_path"},
    "decomposition": {"one_repo_per_subtask", "one_pr_per_subtask", "title_pattern",
                      "mandatory", "spike_when_unresolved", "spike_timebox_days",
                      "extra_subtask_kinds"},
    "decomposition.mandatory[]": {"kind", "when"},
    "budgets": {"story_summary_words", "technical_notes_words", "subtask_words",
                "max_subtasks", "max_files_per_subtask", "max_subtask_days",
                "min_acceptance_criteria", "max_acceptance_criteria",
                "max_context_entries", "min_subtask_days"},
    "tracker": {"language", "headings", "adapter", "project", "markup", "story_issue_type", "subtask_issue_type",
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
               "spike_required", "spike_recommended", "enabling_required",
               "enabling_recommended", "min_anchors"},
    "validation": {"fail_on", "require_command_done_when", "require_coverage_matrix",
                   "vagueness_lexicon", "non_functional_keys", "definition_of_done",
                   "require_intake", "measured_non_functional_keys"},
    "validation.definition_of_done[]": {"id", "applies_to_kinds",
                                        "expect_command_matching", "severity"},
}


# Every code this module can emit, with the severity its call sites use and a one-line
# meaning: the condition that trips the gate, not the advice. `--codes` prints the
# union of these registries; selftest holds each to its call sites both ways, so a
# code cannot be emitted unregistered and an entry cannot outlive its emitter.
# "error | warn" is a code with call sites at both severities; "config" is one whose
# severity a rule in refinery.yaml decides.
CODES = {
    # 0 configure
    "CFG001": ("warn", "refinery.yaml carries a key that no script reads"),
    "STRUCT001": ("error", "a required top-level key of the bundle is missing"),
    "STRUCT002": ("error", "story is missing its key, title, summary or criteria"),
    "STRUCT003": ("error", "the bundle has no subtasks, so nothing was decomposed"),
    "TLR001": ("warn", "config names a tailoring source the bundle does not record"),
    "TLR002": ("error", "an applied tailoring rule carries no text a reader can check"),
    "TLR006": ("warn", "a mechanical tailoring instruction is recorded as prompt, invisible to every gate"),
    "TLR007": ("warn", "a tailoring source is recorded and no wishes file is stamped"),
    "TLR008": ("warn", "the stamped wishes file is missing or changed since this refinement"),
    "TLR003": ("error", "a tailoring override relaxes an invariant no tailoring may relax"),
    "TLR004": ("error", "a tailoring override records no reason and no person"),
    "TLR005": ("warn", "a gate is switched off and the bundle never says so"),
    # 1 intake
    "CYN001": ("error", "the domain is complex and the plan contains no probe"),
    "CYN002": ("warn", "the domain is chaotic, so refinement is the wrong instrument now"),
    "CYN003": ("error | warn", "nobody classified whether this problem is knowable up front"),
    "ENB001": ("warn", "an enabler names what it unlocks and no blocks link records it"),
    "IMP001": ("warn", "intake flagged a mechanism with no outcome and no impact map answers it"),
    "IMP002": ("error | warn", "the impact map has no goal, or its goal carries no number"),
    "INT001": ("error", "the bundle carries no intake assessment at all"),
    "INT002": ("error", "an intake verdict or dimension status is outside the vocabulary"),
    "INT003": ("error", "the item was decomposed although its verdict was not sufficient"),
    "INT004": ("error", "a required intake dimension is missing with no blocking question"),
    "INT005": ("error", "a dimension is marked assumed with no assumption written down"),
    "INT006": ("warn", "an assumption has no question that could ever confirm it"),
    "INT007": ("error", "a dimension marked present quotes nothing found in the source text"),
    "INT008": ("error", "the verdict says sufficient while a required dimension is missing"),
    "INT009": ("warn", "a present dimension is still flagged heuristic, unconfirmed by anyone"),
    "INT010": ("error", "a dimension marked answered lacks the answer or who gave it"),
    "INT011": ("warn", "the intake kind and the decomposition profile disagree"),
    "INT012": ("error", "the intake kind is outside the vocabulary and has no questionnaire"),
    # 1 triage
    "TRI001": ("warn", "the ticket's own metadata was never captured into tracker_meta"),
    "TRI002": ("error", "labels route this to incident handling yet it was decomposed"),
    "TRI003": ("error", "labels require a subtask kind the decomposition does not contain"),
    "TRI004": ("error", "labels require an intake dimension nobody assessed"),
    "TRI005": ("warn", "labels imply a profile or kind the bundle does not use"),
    "TRI006": ("warn", "labels make a quality attribute mandatory and it reads unchanged"),
    "TRI007": ("warn", "a label matches no policy rule and no ignore pattern"),
    "TRI008": ("warn", "labels call for a critic the review panel lacks"),
    "TRI009": ("warn", "the triage block no longer matches the ticket's current labels"),
    # 2 evidence
    "GRN001": ("error", "greenfield is declared without a target or a reason"),
    "GRN002": ("error", "a greenfield story rules nothing out about reuse"),
    "GRN003": ("warn", "a line number is cited on a file that does not exist yet"),
    "GRN004": ("error | warn", "a greenfield story has no walking skeleton, or subtasks start beside it"),
    "EVI001": ("error", "the change surface is empty, so Phase 2 was skipped"),
    "EVI002": ("error", "a change-surface entry lacks its repo or its path"),
    "EVI003": ("warn", "a change-surface entry carries a role outside create, modify, delete, read"),
    "EVI004": ("warn", "evidence records no repos, so provenance cannot be verified"),
    "EVI005": ("warn", "the notes cite a path the change surface never recorded"),
    "EVI006": ("error", "several repos change and no contract between them is recorded"),
    "EVI007": ("warn", "a brief edits a file the evidence never recorded touching"),
    "EVI008": ("warn", "a change across repos rules nothing out, so near-misses go unnamed"),
    "EVI009": ("error", "a negative result records nowhere it looked or no conclusion"),
    "PND001": ("error | warn", "a pending claim names nothing that will create the code it cites"),
    "PND002": ("error | warn", "the story depends on another item and no link records it"),
    "SER001": ("warn", "entries inherited from an earlier bundle are stale and unverified"),
    "SER002": ("warn", "the text promises a follow-up ticket that follow_ups does not list"),
    # 3 criteria
    "AC001": ("error", "fewer acceptance criteria than the configured minimum"),
    "AC002": ("warn", "more acceptance criteria than the configured maximum, so split the story"),
    "AC003": ("error", "an acceptance criterion carries no code at all"),
    "AC004": ("error", "two acceptance criteria share the same code"),
    "AC005": ("error", "an acceptance criterion has no rule text at all"),
    "AC006": ("error", "a rule has no concrete example, so it is not understood yet"),
    "AC007": ("error", "an acceptance criterion contains a term from the vagueness lexicon"),
    "AC008": ("warn", "the rule names more alternatives than it carries examples"),
    "AC009": ("warn", "the rule draws a threshold and no example stands exactly on it"),
    "AC010": ("warn", "the criteria mix two code schemes in one story"),
    "AC011": ("error", "a retired criterion code is in use again"),
    "BAS001": ("warn", "a target is stated relative to today and no baseline records today"),
    "BAS002": ("error", "a criterion claims behaviour is preserved and nothing captured the behaviour"),
    "BAS003": ("error | warn", "a baseline entry lacks its metric, its value or its source"),
    "BUD001": ("warn", "a human-facing text exceeds its word budget"),
    "BUD002": ("warn", "a human-facing text contains a term from the vagueness lexicon"),
    "BUD003": ("error", "the technical notes are empty, so this is a reworded ticket"),
    "BUD004": ("warn", "no non-goals are recorded, the cheapest scope control there is"),
    "BUD005": ("warn", "the original ask was not recorded, so scope creep cannot be checked"),
    "DT001": ("error", "a decision-table combination has neither a rule nor an impossibility"),
    "DT002": ("error", "the decision table is malformed: unknown condition, value or criterion"),
    "DT003": ("error", "one combination matches several rules with different outcomes"),
    "DT004": ("warn", "the decision table is wider than one story can be"),
    "NFR001": ("warn", "a required quality attribute was never addressed, not even as unchanged"),
    "NFR002": ("warn", "a measured quality attribute is answered in prose with no number"),
    # 4 decisions
    "DEC001": ("error", "a decision status is neither locked nor deferred"),
    "DEC002": ("error", "a locked decision names no chosen option"),
    "DEC003": ("error", "a locked decision carries no rationale anyone could challenge"),
    "DEC004": ("error", "a deferred decision has no spike subtask to resolve it"),
    "DEC005": ("error", "a deferred decision points at a spike that is not in the bundle"),
    "DEC006": ("error", "a deferred decision points at a subtask that is not a spike"),
    "DEC007": ("error", "a deferred decision has no expiry, so it is an unmade decision"),
    "DEC008": ("error", "a deferred decision never says what information would decide it"),
    "READY001": ("error", "a blocking question is still unresolved in the bundle"),
    "READY002": ("warn", "a question has no owner, so nobody will answer it"),
    "READY003": ("error | warn", "a question was recorded but never put to anyone"),
    "READY004": ("error | warn", "a question waits on something that is not a question, or carries no guess"),
    "READY005": ("warn", "a question was asked while it still waits on an earlier answer"),
    "RSK001": ("error", "a risk records no mitigation, so it is a worry, not a plan"),
    "RSK002": ("warn", "a high risk records no detection signal that would reveal it"),
    "RSK003": ("warn", "a change across repos records no risks at all"),
    # 5 decompose
    "CPX001": ("warn", "no complexity card is recorded for a decomposed story"),
    "CPX002": ("warn", "the recorded complexity card no longer matches the bundle"),
    "CON001": ("error", "a subtask references a contract id the evidence never recorded"),
    "COV001": ("error", "an acceptance criterion is covered by no subtask"),
    "COV002": ("warn", "the declared coverage map disagrees with the subtasks' covers lists"),
    "DAG001": ("error", "the subtask dependency graph contains a cycle"),
    "DAG002": ("error", "a subtask consumes a contract without depending on its producer"),
    "IRR001": ("error", "a migration subtask records neither a rollback nor an irreversibility note"),
    "IRR002": ("warn", "a migration subtask's done_when counts or verifies nothing it touched"),
    "IRR003": ("warn", "a migration subtask has no dry run in its preflight"),
    "PAR001": ("error", "one file is written by subtasks that could run concurrently"),
    "PAR002": ("warn", "one file is written by two subtasks in sequence, so the later one rebases"),
    "SPK001": ("error", "a research item plans no spike subtask"),
    "SPK002": ("error", "a spike exceeds the configured timebox in days"),
    "SPK003": ("warn", "a spike on a delivery story that no decision defers to"),
    "SPK004": ("error", "a research item already plans the build it exists to inform"),
    "SPL001": ("warn", "the blast radius exceeds a split threshold, so the story should split"),
    "SUB001": ("warn", "more subtasks than the configured maximum allows"),
    "SUB002": ("error", "two subtasks in the bundle share one id"),
    "SUB003": ("error", "a subtask has no title at all"),
    "SUB004": ("error", "two subtasks in the bundle share one title"),
    "SUB005": ("warn", "a subtask title is longer than trackers display"),
    "SUB006": ("warn", "a subtask title contains a conjunction, so it is probably two subtasks"),
    "SUB007": ("error", "a subtask names no repo it belongs to"),
    "SUB008": ("warn", "a subtask's human text exceeds its word budget"),
    "SUB009": ("error", "a subtask has no human-facing text at all"),
    "SUB010": ("warn", "a subtask has no estimate, so sizing cannot be checked"),
    "SUB011": ("error", "a subtask estimate exceeds the configured maximum days"),
    "SUB012": ("error", "a subtask covers a criterion code that does not exist"),
    "SUB013": ("error", "a subtask covers no criterion and its kind is not exempt"),
    "SUB014": ("error", "a subtask depends on a subtask id that does not exist"),
    "SUB015": ("error", "a subtask spans more than one repo at once"),
    "SUB016": ("error | warn", "the profile is expand-contract and nothing contracts"),
    "SUB017": ("warn", "a subtask is below the floor and touches one file, a commit not a ticket"),
    "SUB018": ("warn", "two chained subtasks in one repo on one criterion fit inside every cap together"),
    "SUB019": ("error", "a subtask kind is outside the closed vocabulary and skips every kind-keyed gate"),
    # 6 briefs
    "LANG001": ("warn", "no language is recorded for a story that carries human-facing text"),
    "LANG002": ("warn", "a human-facing field reads as a different language than the story's"),
    "LANG003": ("warn", "the story's language has no heading table, so the ticket renders English headings"),
    "BRF001": ("error", "a subtask has no agent brief at all"),
    "BRF002": ("error", "an agent brief lacks a required field"),
    "BRF003": ("error", "an agent brief names a different repo than its subtask"),
    "BRF004": ("error", "a brief's change surface exceeds the file budget"),
    "BRF005": ("warn", "a change-surface role is outside create, modify, delete"),
    "BRF006": ("error", "done_when contains no runnable command, so there is no mechanical gate"),
    "BRF007": ("error", "a command entry in done_when has no command"),
    "BRF008": ("warn", "a done_when assertion is too vague to write a test from"),
    "BRF009": ("error", "a convention cites no path:line evidence, so it is a training prior"),
    "BRF010": ("warn", "a brief has no forbidden entries, so nothing stops scope creep"),
    "BRF011": ("warn", "a brief has no out_of_scope entries at all"),
    "BRF012": ("warn", "a brief contains what looks like implementation code"),
    "BRF013": ("warn", "entry points carry line numbers and no preflight verifies them"),
    "BRF014": ("warn", "a brief has no stop_and_ask, so an unknown gets improvised past"),
    "BRF015": ("warn", "a brief's read and touch set exceeds one context window's budget"),
    "DOD001": ("config", "no done_when command satisfies a Definition of Done rule for this kind"),
    "DOD002": ("error", "a Definition of Done rule carries an invalid regular expression"),
    "DOD003": ("error", "a Definition of Done rule lists its kinds as a string, matching nothing"),
    # 8 review
    "REV001": ("error", "no adversarial review has read the bundle"),
    "REV002": ("error", "a blocking review finding is still open"),
    "REV003": ("error | warn", "a review finding carries no resolution, or an invalid status"),
    "REV004": ("warn", "a critic found nothing and recorded nothing it attempted"),
    "REV005": ("error", "a finding's locator resolves to nothing in the bundle"),
    "REV006": ("error", "fewer critics than the configured minimum"),
    "REV007": ("error", "the review stamp is missing or the bundle changed since it"),
    "REV008": ("warn", "rubber-ducking alone on more subtasks than the configured limit"),
    "REV009": ("error | warn", "a finding's severity or a critic's id is outside the vocabulary"),
    # 9 emit
    "LNK001": ("error", "a link names no target ticket at all"),
    "LNK002": ("warn", "a link records no reason for existing"),
    "LNK003": ("warn", "a follow-up this refinement created is linked to nothing"),
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


def frontier(questions):
    """The questions you can ask *now* without guessing at answers you have not heard
    yet - every question whose prerequisites are already settled `[P: Pocock, grilling]`.

    Asking past the frontier is how a round produces answers that the next round
    invalidates: you ask which cache TTL before anyone has said whether we cache."""
    answered = {q.get("id") for q in questions if q.get("answer")}
    now, later = [], []
    for q in questions:
        if q.get("answer"):
            continue
        blockers = [b for b in q.get("blocked_by") or [] if b not in answered]
        (later if blockers else now).append(q)
    return now, later


def check_questions_and_decisions(b, rep):
    questions = b.get("open_questions") or []
    ids = {q.get("id") for q in questions}
    askable, _ = frontier(questions)
    askable_ids = {q.get("id") for q in askable}
    for q in questions:
        where = "open_questions.%s" % q.get("id", "?")
        for blocker in q.get("blocked_by") or []:
            if blocker not in ids:
                rep.error("READY004", where, "waits on %r, which is not a question in this "
                          "bundle" % blocker)
        # A bare question gets an essay back; a question with a guess attached gets a
        # correction, which is cheaper for everyone and arrives sooner.
        if not q.get("guess") and not q.get("answer"):
            rep.warn("READY004", where, "no recommended answer attached - a bare question "
                     "costs the owner an essay, a guess costs them a correction")
        if q.get("asked") and q.get("id") not in askable_ids and not q.get("answer"):
            rep.warn("READY005", where, "asked while it still waits on %s - the answer will "
                     "be a guess at a guess" % ", ".join(q.get("blocked_by") or []))
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
    # A code is a public reference the moment it leaves this session: subtasks cover
    # it, the table cites it, people type it into comment threads. Mixed schemes make
    # every one of those ambiguous.
    coded = [ac.get("id") for ac in acs if ac.get("id")]
    prefixes = {re.sub(r"\d+$", "", i) for i in coded}
    if len(prefixes) > 1:
        rep.warn("AC010", "story.acceptance_criteria", "mixed code schemes (%s) - use the "
                 "source's scheme or this skill's, not both; `criteria.py assign` keeps one"
                 % ", ".join(sorted(coded)))
    retired = set((b.get("story") or {}).get("retired_criterion_ids") or [])
    for i in sorted(retired & set(coded)):
        rep.error("AC011", "AC %s" % i, "this code was retired and is in use again - every "
                  "reference to it still resolves, and now resolves to something else")


def check_example_coverage(b, rep):
    """Examples are not illustrations, they are the test cases. A rule that names
    three inputs and shows one has two branches nobody has thought about, and a rule
    that draws a line with no example standing on it will be implemented off by one.
    `[P: Myers, equivalence partitioning and boundary value analysis, 1979]`"""
    import lang as L
    connector = L.CONNECTOR.get(L.code_of(b), r"\bor\b")
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
    if not ev.get("repos") and not ev.get("greenfield"):
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
    known_kinds = SUBTASK_KINDS | set(get(cfg, "decomposition.extra_subtask_kinds", []) or [])

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

        if s.get("kind") not in known_kinds:
            rep.error("SUB019", where, "unknown kind %r - a kind nothing recognises matches no "
                      "Definition of Done, no mandatory-subtask rule and no exemption, so the "
                      "subtask silently skips every one of them. Use %s, or add it to "
                      "decomposition.extra_subtask_kinds"
                      % (s.get("kind"), " | ".join(sorted(known_kinds))))

        covers = s.get("covers") or []
        for cid in covers:
            if cid not in ac_ids:
                rep.error("SUB012", where, "covers unknown criterion %r" % cid)
        if not covers and s.get("kind") not in UNCOVERED_OK_KINDS:
            rep.error("SUB013", where,
                      "covers no acceptance criterion and kind %r is not enabling/spike/rollout"
                      % s.get("kind"))

        _check_brief(s, where, max_files, require_cmd, rep,
                     get(cfg, "budgets.max_context_entries", 12),
                     greenfield=bool((b.get("evidence") or {}).get("greenfield")))

    for s in subs:
        for dep in s.get("depends_on") or []:
            if dep not in ids:
                rep.error("SUB014", "subtask %s" % s.get("id"),
                          "depends_on unknown subtask %r" % dep)
    return subs, ids


def _check_brief(s, where, max_files, require_cmd, rep, max_reading=12, greenfield=False):
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
        evidence = conv.get("evidence") or ""
        if greenfield and re.match(r"^(standard|adr|template|decision|reference):", evidence):
            continue        # nothing exists to cite yet; a declared source is the citation
        if ":" not in evidence:
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
    # Days and files bound what a person can hold; an agent is bound by what fits in
    # one fresh context window, which is the reading, not the writing [P: Pocock,
    # to-tickets: "sized to fit in a single fresh context window"].
    reading = len(brief.get("read_first") or []) + len(surface) + \
        len(brief.get("entry_points") or [])
    if max_reading and reading > max_reading:
        rep.warn("BRF015", where, "%d file(s) to read and touch (budget %d) - a subtask sized "
                 "for a day can still be too big for one fresh context window, and an agent "
                 "that runs out re-reads from a fuzzy average of the codebase"
                 % (reading, max_reading))
    if not brief.get("stop_and_ask"):
        rep.warn("BRF014", where, "no 'stop_and_ask' - 'forbidden' says what not to touch, "
                 "this says when not to decide; without it an agent that finds reality "
                 "different from the brief improvises")
    # Commands are allowed to name code - `grep -n '^def check('` is a preflight, not an
    # implementation - so only the prose fields are read for the smell.
    prose = {k: v for k, v in brief.items() if k not in ("preflight", "done_when")}
    blob = json.dumps(prose)
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


def check_clutter(b, cfg, subs, rep):
    """Every budget in this skill is an upper bound, so the whole thing leans towards
    smaller. Nothing leaned back, and the result is a plan of slivers.

    A subtask exists to be *separately reviewable*. Two pieces of work that will be
    read together, reviewed together and merged together are one subtask, and each
    extra one is not free: a ticket, a brief, a review, a CI run, a handoff - and,
    for an agent implementor, another full load of the shared context. Three slivers
    pay for the dossier three times to deliver one PR."""
    floor = get(cfg, "budgets.min_subtask_days", 0.25)
    max_days = get(cfg, "budgets.max_subtask_days", 1.0)
    max_files = get(cfg, "budgets.max_files_per_subtask", 8)
    # Kinds the house asks for separately are chosen ceremony, not accidental clutter.
    mandated = {r.get("kind") for r in get(cfg, "decomposition.mandatory", []) or []}
    by_id = {s.get("id"): s for s in subs}
    dependents = {}
    for s in subs:
        for dep in s.get("depends_on") or []:
            dependents.setdefault(dep, []).append(s.get("id"))

    def writes(s):
        return [e for e in (s.get("agent_brief") or {}).get("change_surface") or []
                if e.get("role") in ("create", "modify", "delete")]

    for s in subs:
        est = s.get("estimate_days")
        if est is not None and floor and est < floor and len(writes(s)) <= 1 \
                and s.get("kind") not in mandated and s.get("kind") != "spike":
            rep.warn("SUB017", "subtask %s" % s.get("id"), "%.2gd and one file - below the "
                     "floor of %.2gd. A subtask earns its overhead by being separately "
                     "reviewable; this one is a commit inside another subtask"
                     % (est, floor))

    for s in subs:
        deps = [d for d in s.get("depends_on") or [] if d in by_id]
        if len(deps) != 1:
            continue
        parent = by_id[deps[0]]
        # Only a straight chain of two: the parent feeds nothing else, and this one
        # waits on nothing else. Anything wider is a real fan-out.
        if len(dependents.get(parent.get("id"), [])) != 1:
            continue
        if parent.get("repo") != s.get("repo"):
            continue
        # A spike holds a deferred decision (DEC004) and a rollout happens days later.
        # Both are separate for a structural reason, not by accident.
        if {s.get("kind"), parent.get("kind")} & (mandated | {"spike", "rollout"}):
            continue
        covers, pcovers = set(s.get("covers") or []), set(parent.get("covers") or [])
        if covers and pcovers and not covers & pcovers:
            continue
        days = (s.get("estimate_days") or 0) + (parent.get("estimate_days") or 0)
        files = len({e.get("path") for e in writes(s) + writes(parent)})
        if (max_days and days > max_days) or (max_files and files > max_files):
            continue
        rep.warn("SUB018", "subtask %s" % s.get("id"), "%s and %s are one repo, one criterion "
                 "and a chain of two, and together they are still %.2gd over %d file(s) - "
                 "inside every cap. Merging them removes a handoff, a review and one more "
                 "load of the shared context; keep them apart only if they are genuinely "
                 "reviewed by different people" % (parent.get("id"), s.get("id"), days, files))


# A claim measured against today, as opposed to one that merely contains a number.
IMPROVEMENT_RX = re.compile(
    r"\bunder\b|\bbelow\b|\bless than\b|\bno more than\b|\bat most\b|\bwithin\b|\bfaster\b|"
    r"\breduc\w+\b|\bdown to\b|\bfrom \d[\w.]*\s*(to|->|→)\s*\d|\bimprov\w+\b|\bspeed\w* up\b|"
    r"\bonder\b|\bminder dan\b|\bhoogstens\b|\bbinnen\b|\bsneller\b|\bterugbrengen\b|"
    r"\bverbeter\w+\b|\bmaximaal\b", re.I)
PRESERVATION_RX = re.compile(
    r"\bunchanged\b|\bidentical\b|\bexactly (what|as)\b|\bsame as (before|today|now)\b|"
    r"\bno (observable|behavioural|functional) change\b|\bbyte-identical\b|"
    r"\bongewijzigd\b|\bidentiek\b|\bhetzelfde als (nu|voorheen)\b|\bprecies wat\b", re.I)


def check_baseline(b, cfg, rep):
    """Two whole classes of story claim something about a 'before' that nobody wrote down.

    A performance story says 'p95 under 200ms' - from what? If it is already 180ms the
    story is finished before it starts, and if it is four seconds this is a different
    project. A refactor says 'behaviour is unchanged' - unchanged from what? Neither
    claim can be demonstrated, or falsified, without a recorded starting point. It is
    the cheapest thing in the whole refinement to capture and the easiest to skip,
    because at refinement time everyone in the room believes they know the number."""
    story = b.get("story") or {}
    baselines = story.get("baseline") or []
    have = {}
    for i, entry in enumerate(baselines):
        metric = (entry.get("metric") or "").strip().lower()
        if not metric or not str(entry.get("current") or "").strip():
            rep.error("BAS003", "story.baseline[%d]" % i, "a baseline entry needs both the "
                      "metric and its current value - an empty one is worse than none, it "
                      "looks like somebody measured")
            continue
        if not entry.get("source"):
            rep.warn("BAS003", "story.baseline[%d]" % i, "%r = %r with no source - a number "
                     "nobody can re-derive is a memory, and memories of latency are wrong"
                     % (entry.get("metric"), entry.get("current")))
        have[metric] = entry

    measured = get(cfg, "validation.measured_non_functional_keys", DEFAULT_MEASURED_NFR_KEYS) or []
    nfr = story.get("non_functional") or {}
    for key in measured:
        text = str(nfr.get(key) or "")
        # A number alone is a design statement ("VIES timeout 3s"), and nothing is being
        # moved. Only a claim relative to today needs a today to be relative to.
        if not text or UNCHANGED_RX.search(text) or not IMPROVEMENT_RX.search(text):
            continue
        if key not in have:
            rep.warn("BAS001", "story.non_functional.%s" % key, "states a target (%r) and no "
                     "baseline records what it is today - a target without a starting point "
                     "cannot be verified, and nobody can tell whether this story is worth "
                     "pulling" % text[:60])

    for ac in story.get("acceptance_criteria") or []:
        rule = ac.get("rule") or ""
        if not PRESERVATION_RX.search(rule):
            continue
        if not baselines:
            rep.error("BAS002", "AC %s" % ac.get("id"), "claims behaviour is preserved, and "
                      "nothing recorded what it was. 'Unchanged' is only demonstrable against "
                      "a capture made before the change - name it in story.baseline (a "
                      "characterisation test, a recorded corpus, a saved query result), or "
                      "this criterion cannot be met or failed")


def check_irreversible(b, cfg, subs, rep):
    """A migration is the one subtask kind where being wrong is not a revert away.

    Everything else in this skill assumes a bad change can be backed out: flags,
    rollback notes, wave ordering. Data does not work that way - the old value is
    gone - so the questions that make a migration safe have to be asked at refinement
    time, when there is still someone to ask."""
    for s in subs:
        if s.get("kind") != "migration":
            continue
        where = "subtask %s" % s.get("id")
        brief = s.get("agent_brief") or {}
        rollback = brief.get("rollback") or {}
        note = (rollback.get("note") or "").strip()
        if not note and not rollback.get("irreversible"):
            rep.error("IRR001", where, "a migration with no rollback note. Either say how the "
                      "data change is reversed, or set rollback.irreversible with the reason - "
                      "'we cannot undo this' is a fact the story owner has to know before it "
                      "is pulled, not one the implementer discovers")
        elif rollback.get("irreversible") and not note:
            rep.error("IRR001", where, "marked irreversible with no note - say what is lost "
                      "and what would have to be restored from, so somebody can decide whether "
                      "to accept it")

        cmds = " ".join((d.get("cmd") or "") + " " + (d.get("text") or "")
                        for d in brief.get("done_when") or [])
        if not re.search(r"\bcount\b|\bselect\b|\brows?\b|\bverif|\breconcil|\baantal\b", cmds, re.I):
            rep.warn("IRR002", where, "nothing in done_when counts or verifies what the "
                     "migration touched. A migration that ran without error and changed the "
                     "wrong rows reports success")

        pre = " ".join((d.get("cmd") or "") + " " + (d.get("text") or "")
                       for d in brief.get("preflight") or [])
        if not re.search(r"dry.?run|--dry|rehearse|proefdraai|staging|shadow", pre, re.I):
            rep.warn("IRR003", where, "no dry run in preflight - the first full-size execution "
                     "will be the production one, on data that has no second copy")


def check_enabler(b, rep):
    """An enabler's whole justification is the work it unlocks. If that work has a
    ticket, the tracker should say so - the link is what stops the enabler being
    deprioritised past the story that needed it, by someone who never read either."""
    story = b.get("story") or {}
    intake = story.get("intake") or {}
    if intake.get("kind") != "enabling":
        return
    links = _known_links(story)
    for d in intake.get("dimensions") or []:
        if d.get("id") != "unlocks":
            continue
        text = " ".join(str(d.get(k) or "") for k in ("evidence", "answer", "assumption"))
        for key in sorted(set(TICKET_RX.findall(text))):
            if key == story.get("key"):
                continue
            if key not in links:
                rep.warn("ENB001", "story.intake.unlocks", "says this unlocks %s and no link "
                         "records it - add a 'blocks' link, or the enabler gets scheduled after "
                         "the story it exists for, by someone who read neither" % key)
            elif "blocks" not in links[key]:
                rep.warn("ENB001", "story.intake.unlocks", "linked to %s as %s, not 'blocks' - "
                         "the order is the point of the link"
                         % (key, "/".join(sorted(links[key])) or "?"))


def check_greenfield(b, subs, rep):
    """A story for a project that does not exist yet. There is nothing to cite, so the
    evidence rule turns around: what gets ruled out is reuse, what gets cited is a
    declared source, and the first thing built is a walking skeleton - the thinnest
    end-to-end path, deployed - so every later subtask lands on something that runs
    [P: Cockburn, walking skeleton]."""
    ev = b.get("evidence") or {}
    g = ev.get("greenfield")
    if not g:
        return
    if not isinstance(g, dict) or not g.get("target") or not g.get("reason"):
        rep.error("GRN001", "evidence.greenfield", "greenfield needs a target (the repo or "
                  "project that will exist) and a reason it is new rather than an extension "
                  "of something that exists")
    reuse = [r for r in ev.get("ruled_out") or []
             if re.search(r"\b(reuse|extend|existing|already|bestaand|hergebruik)\b",
                          (r.get("claim") or "") + " " + (r.get("conclusion") or ""), re.I)]
    if not reuse:
        rep.error("GRN002", "evidence.ruled_out", "greenfield and nothing rules out reuse - "
                  "'there is no existing project to extend' is the one search a new project "
                  "must record, with where it looked")
    for i, entry in enumerate(ev.get("change_surface") or []):
        if entry.get("line") and entry.get("role") == "create":
            rep.warn("GRN003", "evidence.change_surface[%d]" % i, "a line number on a file "
                     "that will be created - a citation into code that does not exist")
    if subs:
        roots = [s for s in subs if not (s.get("depends_on") or [])]
        skeleton = [s for s in roots if s.get("kind") == "enabling"]
        if not skeleton:
            rep.error("GRN004", "subtasks", "greenfield with no walking skeleton - the first "
                      "subtask is kind 'enabling', depends on nothing, and puts the thinnest "
                      "end-to-end path through a deployable project; everything else lands "
                      "on it")
        elif len(roots) > len(skeleton):
            others = [s.get("id") for s in roots if s.get("kind") != "enabling"]
            rep.warn("GRN004", "subtasks", "%s start alongside the skeleton instead of on it "
                     "- on a project that does not exist yet, what do they build into?"
                     % ", ".join(str(o) for o in others))


def check_complexity(b, cfg, subs, rep):
    """The card is derived, so a recorded one either matches the bundle or is stale."""
    if not subs:
        return
    import complexity as CX
    rec = (b.get("story") or {}).get("complexity")
    if not rec:
        rep.warn("CPX001", "story.complexity", "no complexity card - run `complexity.py assess "
                 "--bundle <bundle> --write`; a story handed over without one is sized by "
                 "feel")
    elif not CX.is_current(b, cfg):
        rep.warn("CPX002", "story.complexity", "the recorded card no longer matches the bundle "
                 "- it is derived, regenerate it rather than maintaining it by hand")


def check_language(b, cfg, rep):
    """The refinement goes back in the language the item came in. The story records
    which; the human-facing fields are held to it where detection can tell; and a
    language with no heading table is said out loud before the ticket renders."""
    import lang as L
    story = b.get("story") or {}
    human = [story.get("summary_human") or "", story.get("technical_notes_human") or ""]
    human += [a.get("rule") or "" for a in story.get("acceptance_criteria") or []]
    if not any(t.strip() for t in human):
        return
    lang = story.get("language")
    code = (lang or {}).get("code") if isinstance(lang, dict) else lang
    if not code:
        rep.warn("LANG001", "story.language", "not recorded - `intake.py assess --write` "
                 "detects it; a ticket in one language refined in another reads as a "
                 "translation error")
        return
    if code == "unknown":
        rep.warn("LANG001", "story.language", "recorded as unknown - name the language by "
                 "reading and set {code, source: given}")
        return
    joined = " ".join(t for t in human if t)
    found, _ = L.detect(joined)
    if found and found != code and len(joined.split()) >= 40:
        rep.warn("LANG002", "story.summary_human", "the human-facing text reads as %r while "
                 "the story's language is %r - the refinement is written in the wrong "
                 "language, or story.language is" % (found, code))
    cfg_lang = str(get(cfg, "tracker.language", "auto") or "auto")
    target = code if cfg_lang == "auto" else cfg_lang
    if not L.has_headings(target, get(cfg, "tracker.headings", None)):
        rep.warn("LANG003", "story.language", "no heading table for %r - the ticket renders "
                 "English headings around %s text. Add tracker.headings in refinery.yaml "
                 "(every key of the English table) or accept the mix at handover" % (target, code))


def check_research(b, cfg, subs, rep):
    """A research item delivers information, and nothing else.

    Its failure mode is not being too vague, it is being too confident: it arrives as
    a delivery plan for the thing nobody has established yet. So the gates run the
    other way round from a feature's - they check that the item stops at the answer,
    that the answer is bounded, and that somebody is waiting for it."""
    story = b.get("story") or {}
    kind = ((story.get("intake") or {}).get("kind")) or "feature"
    spikes = [s for s in subs if s.get("kind") == "spike"]

    if kind == "spike" and subs and not spikes:
        rep.error("SPK001", "subtasks", "intake says this item is research and not one subtask "
                  "is a spike - either the plan is not the research, or the item is a story "
                  "wearing a spike label")

    timebox = get(cfg, "decomposition.spike_timebox_days", 0.5)
    for s in spikes:
        est = s.get("estimate_days")
        if timebox and est is not None and est > timebox:
            rep.error("SPK002", "subtask %s" % s.get("id"), "spike is %.2gd against a timebox "
                      "of %.2gd. The timebox is the price of the option, not an estimate of "
                      "the work - a spike that overruns it has stopped buying information "
                      "and started doing the job" % (est, timebox))

    # risk-and-options.md: a spike that would not change any decision is research, and
    # research is not a subtask on this story. On a research item the decision it
    # unblocks is a required intake dimension, so it is already recorded at story level.
    if kind != "spike":
        resolved = {d.get("spike") for d in b.get("decisions") or [] if d.get("spike")}
        for s in spikes:
            if s.get("id") not in resolved:
                rep.warn("SPK003", "subtask %s" % s.get("id"), "no decision defers to this "
                         "spike - name the decision it resolves, or drop it. A spike whose "
                         "answer changes nothing is reading, and reading is not a ticket")

    # triage.md: check it is not a story in disguise. Test and docs subtasks are left
    # alone - decomposition.mandatory can manufacture those - but planning the build is
    # proof the answer was assumed.
    if kind == "spike":
        building = [s.get("id") for s in subs if s.get("kind") in ("feature", "migration")]
        if building:
            rep.error("SPK004", "subtasks", "a research item plans the build: %s. Whatever the "
                      "answer turns out to be, these were written before it - move them to the "
                      "story this research informs, and link the two"
                      % ", ".join(str(i) for i in building))


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
    owners, creators = {}, {}
    for s in subs:
        for entry in (s.get("agent_brief") or {}).get("change_surface") or []:
            if entry.get("role") not in ("create", "modify", "delete"):
                continue
            key = (s.get("repo"), entry.get("path"))
            owners.setdefault(key, []).append(s.get("id"))
            if entry.get("role") == "create" and s.get("kind") == "enabling":
                creators[key] = s.get("id")
    for (repo, path), ids in sorted(owners.items()):
        if len(ids) < 2:
            continue
        ordered = all(a in reach.get(b, set()) or b in reach.get(a, set())
                      for i, a in enumerate(ids) for b in ids[i + 1:])
        where = "%s/%s" % (repo, path)
        # A walking skeleton creates the files every later slice fills in. That is the
        # shape, not a rebase to warn about - provided the slices depend on it.
        if ordered and creators.get((repo, path)) in ids and all(
                creators[(repo, path)] in reach.get(other, set())
                for other in ids if other != creators[(repo, path)]):
            continue
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


def check_expand_contract(b, subs, rep):
    """Expand, migrate, contract. The third is the one that gets skipped, and skipping
    it ships two ways of doing the same thing plus a comment promising to clean up."""
    if (b.get("profile") or "") != "expand-contract" or not subs:
        return
    kinds = {s.get("kind") for s in subs}
    text = " ".join((s.get("title") or "") + " " + (s.get("human") or "") for s in subs).lower()
    if "migration" not in kinds:
        rep.warn("SUB016", "subtasks", "profile is expand-contract and no subtask is kind "
                 "'migration' - the wide mechanical step is the middle one, and it is only "
                 "allowed to be wide because it is mechanical")
    if not any(w in text for w in ("remove", "delete", "drop", "contract", "clean up")):
        rep.error("SUB016", "subtasks", "profile is expand-contract and nothing contracts - "
                  "no subtask removes the old path. Expanding and migrating without "
                  "contracting ships two ways of doing the same thing and a promise")


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
    if kind not in INTAKE_KINDS:
        rep.error("INT012", "story.intake.kind", "kind must be %s, got %r - an unknown kind "
                  "silently gets the feature questionnaire, which asks a research item for "
                  "an actor and an outcome it does not have"
                  % (" | ".join(INTAKE_KINDS), kind))
        kind = "feature"
    required = set(get(cfg, "intake.%s_required" % kind,
                       DEFAULT_REQUIRED_DIMENSIONS[kind]) or [])
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
    wanted = PROFILE_FOR_KIND.get(kind)
    why = {"bugfix": "the bugfix profile puts the failing test first",
           "research": "the research profile stops at the answer; a delivery profile plans "
                       "the build this item exists to inform"}
    if wanted and (b.get("profile") or "") not in (wanted, ""):
        rep.warn("INT011", "profile", "intake says this is a %s but profile is %r - %s"
                 % (kind, b.get("profile"), why[wanted]))


TICKET_RX = re.compile(r"\b[A-Z][A-Z0-9]{1,9}-\d+\b")
# Canonical link vocabulary. Adapters map these onto their own names (emit.py);
# the bundle never carries a tracker's spelling.
LINK_TYPES = ("blocks", "blocked_by", "relates", "duplicates")


def _known_links(story):
    """Links the tracker already has, plus the ones this refinement says to create."""
    out = {}
    for source in ((story.get("tracker_meta") or {}).get("links") or [],
                   story.get("links") or []):
        for link in source:
            if link.get("key"):
                out.setdefault(link["key"], set()).add(str(link.get("type", "")).lower()
                                                       .replace(" ", "_").replace("is_", ""))
    return out


def check_pending(b, rep):
    """Refining a follow-up means reasoning about code that does not exist yet.

    That is neither evidence nor an assumption: it is specified work someone has
    not done. It gets its own citation - to the item that creates it - and the
    dependency has to exist in the tracker, or the only thing holding the order
    together is that you happened to know."""
    pending = (b.get("evidence") or {}).get("pending") or []
    links = _known_links(b.get("story") or {})
    for i, p in enumerate(pending):
        where = "evidence.pending[%d]" % i
        provider = p.get("provided_by") or {}
        ticket = provider.get("ticket")
        if not p.get("claim"):
            rep.error("PND001", where, "pending entry with no claim - say what will exist")
        if not ticket:
            rep.error("PND001", where, "nothing is recorded as creating this - a claim about "
                      "code that does not exist yet, with no item that produces it, is a guess "
                      "wearing a citation")
            continue
        if not provider.get("subtask") and not provider.get("bundle"):
            rep.warn("PND001", where, "provided by %s, but not by which subtask or in which "
                     "bundle it was specified - an implementor cannot check what shape it will "
                     "arrive in" % ticket)
        if ticket not in links:
            rep.error("PND002", where, "this story depends on %s and no link records it - the "
                      "tracker does not know the order, so the only thing holding it together "
                      "is that you happened to know" % ticket)
        elif "blocked_by" not in links[ticket]:
            rep.warn("PND002", where, "%s is linked but not as a blocker (%s) - a 'relates to' "
                     "does not stop anyone starting this first"
                     % (ticket, ", ".join(sorted(links[ticket])) or "no type"))


def check_links(b, rep):
    story = b.get("story") or {}
    for i, link in enumerate(story.get("links") or []):
        where = "story.links[%d]" % i
        if not link.get("key"):
            rep.error("LNK001", where, "link with no target")
        if link.get("type") not in LINK_TYPES:
            rep.error("LNK001", where, "type must be %s, got %r - adapters map these onto "
                      "their own names; the bundle never carries a tracker's spelling"
                      % (" | ".join(LINK_TYPES), link.get("type")))
        if not link.get("why"):
            rep.warn("LNK002", where, "link with no reason - an unexplained link is the first "
                     "thing deleted in the next backlog cleanup")
    known = set(_known_links(story))
    for f in story.get("follow_ups") or []:
        if f.get("ticket") and f["ticket"] not in known:
            rep.warn("LNK003", "story.follow_ups", "%s is created by this refinement and linked "
                     "to nothing - nobody walking the ticket graph will find it, which is how a "
                     "follow-up becomes a rediscovery" % f["ticket"])


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

    # A calling skill steers this run with a wishes file. Which file, and whether it is
    # still the same file, is what a later reader needs to reproduce the refinement.
    wishes = tailoring.get("wishes")
    if applied_source and not wishes:
        rep.warn("TLR007", "tailoring.wishes", "%r steered this run and no wishes file is "
                 "stamped - run `wishes.py stamp --file <refinement.md> --source %s --write` "
                 "so a later reader can re-read what steered it" % (applied_source, applied_source))
    elif wishes:
        import wishes as W
        why = W.drift(wishes)
        if why:
            rep.warn("TLR008", "tailoring.wishes", why + " - re-read it and re-stamp, or say "
                     "at handover that the refinement predates the change")

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
        # Tailoring arrives mostly as instructions. An instruction that is really a
        # number, a command or a pattern is invisible to every gate while it stays
        # prose - so the rule is: write it into refinery.yaml (generated from the
        # instruction is fine) and record it as config. This is the mechanical half of
        # "prose that thinks it is a gate".
        if mechanism == "prompt" and MECHANICAL_RULE_RX.search(entry.get("rule") or ""):
            rep.warn("TLR006", where, "this instruction is mechanical (%r) and is recorded as "
                     "prompt, so no gate will ever see it - write it into refinery.yaml, "
                     "generated from the instruction if the tailoring skill ships no config, "
                     "and record it with mechanism: config and the key"
                     % (entry.get("rule") or "")[:60])
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
    check_pending(bundle, rep)
    check_links(bundle, rep)
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
    check_clutter(bundle, cfg, subs, rep)
    check_research(bundle, cfg, subs, rep)
    check_language(bundle, cfg, rep)
    check_greenfield(bundle, subs, rep)
    check_complexity(bundle, cfg, subs, rep)
    check_enabler(bundle, rep)
    check_irreversible(bundle, cfg, subs, rep)
    check_baseline(bundle, cfg, rep)
    check_file_collisions(subs, reach, rep)
    check_contract_ids(bundle, subs, rep)
    check_brief_surface(bundle, subs, rep)
    check_one_repo_rule(cfg, subs, rep)
    check_expand_contract(bundle, subs, rep)
    check_definition_of_done(cfg, subs, rep)
    check_coverage(bundle, subs, cfg, rep)
    check_split_thresholds(bundle, cfg, rep)
    check_nonfunctional(bundle, cfg, rep)
    check_review(bundle, cfg, rep)
    return rep


def all_codes():
    """The union of every emitting module's registry, sorted by (phase label, code) -
    the same ordering main() groups findings in. batch.py and criteria.py import
    nothing from here, so the lazy imports cannot cycle."""
    import batch  # noqa: E402
    import criteria  # noqa: E402
    merged = {}
    for module in (sys.modules[__name__], batch, criteria):
        for code, (severity, meaning) in module.CODES.items():
            merged[code] = (severity, meaning)
    rows = [{"code": c, "phase": phase_of(c), "severity": s, "meaning": m}
            for c, (s, m) in merged.items()]
    return sorted(rows, key=lambda r: (r["phase"], r["code"]))


def render_codes(fmt):
    rows = all_codes()
    if fmt == "json":
        return json.dumps(rows, indent=2)
    if fmt == "markdown":
        out = ["# Validator codes", "",
               "Generated by `python scripts/validate.py --codes --markdown`; selftest fails when "
               "this file is stale. A code is the stable identifier of a finding. Severity is what "
               "the call sites use: `error | warn` has call sites at both, `config` is decided by "
               "a rule in `refinery.yaml`.", ""]
        phase = None
        for r in rows:
            if r["phase"] != phase:
                phase = r["phase"]
                out += ["## %s" % phase, "", "| Code | Severity | Meaning |", "|---|---|---|"]
            out.append("| `%s` | %s | %s |" % (r["code"], r["severity"], r["meaning"]))
        return "\n".join(out)
    return "\n".join("%s\t%s\t%s\t%s" % (r["code"], r["phase"], r["severity"], r["meaning"])
                     for r in rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle", nargs="?")
    ap.add_argument("--config", default="refinery.yaml")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--codes", action="store_true",
                    help="list every code the validator, batch.py and criteria.py can emit, "
                         "and exit; needs no bundle")
    ap.add_argument("--markdown", action="store_true",
                    help="with --codes: render the list as references/codes.md")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--flat", action="store_true",
                    help="one finding per line, ungrouped - the pre-phase output")
    args = ap.parse_args(argv)
    if args.markdown and not args.codes:
        ap.error("--markdown only applies with --codes")
    if args.codes:
        # Dispatched before any bundle is opened: a listing must not depend on one.
        print(render_codes("json" if args.json else "markdown" if args.markdown else "tsv"))
        return 0
    if not args.bundle:
        ap.error("the following arguments are required: bundle")

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
        if args.flat:
            for severity in ("ERROR", "WARN"):
                for item in [i for i in rep.items if i["severity"] == severity]:
                    print("%-5s %-9s %-28s %s" % (severity, item["code"], item["where"],
                                                  item["message"]))
        else:
            grouped = {}
            for item in rep.items:
                grouped.setdefault(phase_of(item["code"]), []).append(item)
            for phase in sorted(grouped):
                print("\n-- phase %s --" % phase)
                for severity in ("ERROR", "WARN"):
                    for item in [i for i in grouped[phase] if i["severity"] == severity]:
                        print("  %-5s %-9s %-26s %s" % (severity, item["code"], item["where"],
                                                        item["message"]))
            print("")
        print("\n%s  %d error(s), %d warning(s)"
              % ("READY" if ready else "NOT READY", errors, warns))
        if errors:
            print("Report the findings. Do not delete open questions to pass the gate.")
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
