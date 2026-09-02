#!/usr/bin/env python3
"""Self-test for story-refinery. Stdlib only, no network.

  python selftest.py

Fourteen suites:
  1. Validator gates  - mutate the golden bundle, assert each gate fires
  2. Config parsing   - the YAML subset, including the cases that bit us
  3. Markup           - wiki / ADF / HTML / plaintext conversion
  4. Pipeline         - evidence -> validate -> emit -> emit --previous, end to end
  5. Intake detection - sufficiency verdicts, English and Dutch
  6. Tailoring seam   - what a team skill may change, and what it may never relax
  7. Triage           - the label policy, its precedence, and what it reports
  8. Criterion codes  - assigning them, and them still meaning the same thing later
  9. De-cluttering    - the floor, and the pairs that are really one subtask
 10. Discussion summary - the one screen a refiner talks from
 11. Round trip       - a ticket read back into a bundle, and what shipped
 12. Batch            - what only shows up when several bundles are read together
 13. Adversarial review - digests, locators, and that a critic packet really is blind
 14. Docs consistency - SKILL.md against the scripts and validator codes it cites

A validator nobody has tried to break is a validator nobody should trust, and the
same goes for the config reader that decides which gates run at all.
Exit 0 if everything passes.
"""

import contextlib
import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import _yaml  # noqa: E402
from _yaml import load_config  # noqa: E402
from markup import to_adf, to_html, to_plaintext, to_wiki  # noqa: E402
from validate import validate  # noqa: E402

GOLDEN = os.path.join(ROOT, "assets", "examples", "example-bundle.json")
CONFIG = os.path.join(ROOT, "assets", "refinery.example.yaml")
FAILURES = []


def check(name, ok, detail=""):
    print("%-5s %s%s" % ("ok" if ok else "FAIL", name, "" if ok else "  <- %s" % (detail,)))
    if not ok:
        FAILURES.append(name)
    return ok


def mut(fn):
    def wrapper(b):
        fn(b)
        return b
    return wrapper


# ------------------------------------------------------- suite 1: validator gates

MUTATIONS = [
    ("READY001", mut(lambda b: b["open_questions"].append(
        {"id": "Q9", "text": "which tax provider", "owner": "x", "blocking": True}))),
    ("DEC003", mut(lambda b: b["decisions"][0].update({"rationale": ""}))),
    ("DEC005", mut(lambda b: b["decisions"][1].update({"spike": "S99"}))),
    ("DEC006", mut(lambda b: b["decisions"][1].update({"spike": "S1"}))),
    ("AC006", mut(lambda b: b["story"]["acceptance_criteria"][0].update({"examples": []}))),
    ("AC007", mut(lambda b: b["story"]["acceptance_criteria"][0].update(
        {"rule": "VAT is handled appropriately for EU business customers"}))),
    ("AC007-nl", mut(lambda b: b["story"]["acceptance_criteria"][0].update(
        {"rule": "BTW wordt netjes afgehandeld voor zakelijke klanten"}))),
    ("BUD003", mut(lambda b: b["story"].update({"technical_notes_human": ""}))),
    ("BUD005", mut(lambda b: b["story"].pop("source_text"))),
    ("EVI001", mut(lambda b: b["evidence"].update({"change_surface": []}))),
    ("EVI006", mut(lambda b: b["evidence"].update({"contracts": []}))),
    ("EVI007", mut(lambda b: b["evidence"]["change_surface"].pop(0))),
    ("SUB011", mut(lambda b: b["subtasks"][1].update({"estimate_days": 3.0}))),
    ("SUB012", mut(lambda b: b["subtasks"][1].update({"covers": ["AC9"]}))),
    ("SUB013", mut(lambda b: b["subtasks"][1].update({"covers": []}))),
    ("SUB014", mut(lambda b: b["subtasks"][1].update({"depends_on": ["S42"]}))),
    ("SUB015", mut(lambda b: b["subtasks"][1]["agent_brief"]["change_surface"].append(
        {"path": "src/x.ts", "role": "modify", "repo": "web"}))),
    ("BRF003", mut(lambda b: b["subtasks"][1]["agent_brief"].update({"repo": "web"}))),
    ("BRF004", mut(lambda b: b["subtasks"][1]["agent_brief"].update(
        {"change_surface": [{"path": "f%d.py" % i, "role": "modify"} for i in range(9)]}))),
    ("BRF006", mut(lambda b: b["subtasks"][1]["agent_brief"].update(
        {"done_when": [{"type": "assertion", "text": "it works when the flag is enabled"}]}))),
    ("BRF009", mut(lambda b: b["subtasks"][1]["agent_brief"]["conventions"].append(
        {"rule": "use dependency injection", "evidence": "everyone knows this"}))),
    ("DAG001", mut(lambda b: b["subtasks"][0].update({"depends_on": ["S1"]}))),
    ("DAG002", mut(lambda b: b["subtasks"][4].update({"depends_on": []}))),
    ("CON001", mut(lambda b: b["subtasks"][2].update({"produces_contracts": ["C9"]}))),
    ("COV001", mut(lambda b: b["subtasks"].__setitem__(
        4, dict(b["subtasks"][4], covers=[], kind="spike")))),
    ("COV002", mut(lambda b: b["coverage"].update({"AC1": ["S2"]}))),
    ("SPL001", mut(lambda b: b["blast_radius"].update({"repos": 9}))),
    ("STRUCT003", mut(lambda b: b.update({"subtasks": []}))),
    # Two concurrent subtasks writing one file: S3 and S5 both depend on S2 but not
    # on each other, so a runner would schedule them in the same wave.
    ("PAR001", mut(lambda b: b["subtasks"][5]["agent_brief"]["change_surface"].append(
        {"path": "tests/contract/test_orders_contract.py", "role": "modify"}))),
    # Same file, but strictly ordered: a rebase, not a collision.
    ("PAR002", mut(lambda b: b["subtasks"][2]["agent_brief"]["change_surface"].append(
        {"path": "src/billing/tax.py", "role": "modify"}))),
    # Intake gates.
    ("INT001", mut(lambda b: b["story"].pop("intake"))),
    ("INT003", mut(lambda b: b["story"]["intake"].update({"verdict": "scoutable"}))),
    ("INT004", mut(lambda b: b["story"]["intake"]["dimensions"][2].update(
        {"status": "missing", "question_id": "Q1"}))),          # Q1 is non-blocking
    ("INT005", mut(lambda b: b["story"]["intake"]["dimensions"][3].pop("assumption"))),
    ("INT006", mut(lambda b: b["story"]["intake"]["dimensions"][3].pop("question_id"))),
    ("INT007", mut(lambda b: b["story"]["intake"]["dimensions"][0].update(
        {"evidence": "As a finance controller in Germany"}))),   # not in source_text
    ("INT008", mut(lambda b: (b["story"]["intake"]["dimensions"][2].update(
        {"status": "missing", "question_id": "Q9"}),
        b["open_questions"].append({"id": "Q9", "text": "trigger?", "owner": "x",
                                    "blocking": True})))),
    ("INT009", mut(lambda b: b["story"]["intake"]["dimensions"][0].update({"heuristic": True}))),
    ("INT010", mut(lambda b: b["story"]["intake"]["dimensions"][2].pop("answered_by"))),
    ("INT011", mut(lambda b: b["story"]["intake"].update({"kind": "bug"}))),
    # Definition of Done: a feature subtask with no test command.
    ("DOD001", mut(lambda b: b["subtasks"][1]["agent_brief"].update(
        {"done_when": [{"type": "command", "cmd": "echo hello", "expect": "exit 0"},
                       {"type": "assertion", "text": "the flag gates the new branch"}]}))),
    # Relentless questioning: a question filed and never asked is a note to yourself.
    ("READY003", mut(lambda b: b["open_questions"][0].pop("asked"))),
    ("READY003-blocking", mut(lambda b: b["open_questions"].append(
        {"id": "Q9", "text": "which tax provider", "owner": "x", "blocking": True}))),
    # De-cluttering: the floor that the ceilings alone do not provide.
    ("SUB017", mut(lambda b: b["subtasks"].insert(2, dict(
        b["subtasks"][1], id="S1b", title="[api] Wire the flag in", estimate_days=0.2,
        depends_on=["S1"], agent_brief=dict(b["subtasks"][1]["agent_brief"],
                                            change_surface=[{"path": "src/billing/flags.py",
                                                             "role": "modify"}]))))),
    # The frontier, the context-window budget, and the profile for wide refactors.
    ("READY004", mut(lambda b: b["open_questions"][0].pop("guess"))),
    ("READY004-unknown", mut(lambda b: b["open_questions"][0].update(
        {"blocked_by": ["Q99"]}))),
    ("READY005", mut(lambda b: b["open_questions"][1].update({"blocked_by": ["Q1"]}))),
    ("BRF015", mut(lambda b: b["subtasks"][1]["agent_brief"]["read_first"].extend(
        [{"path": "f%d.py" % i, "why": "padding"} for i in range(8)]))),
    ("SUB016", mut(lambda b: b.update({"profile": "expand-contract"}))),
    # Successive stories: inherited evidence and the follow-ups a refinement creates.
    ("SER001", mut(lambda b: b["evidence"]["ruled_out"][0].update(
        {"inherited_from": "ABC-100", "stale": True}))),
    ("SER002", mut(lambda b: b["story"].update({"follow_ups": []}))),
    ("SER002-trigger", mut(lambda b: b["story"]["follow_ups"][0].pop("trigger"))),
    # Work that does not exist yet: the third citation state, and its link.
    ("PND001", mut(lambda b: b["evidence"].update(
        {"pending": [{"claim": "the tax object on the order response"}]}))),
    ("PND002", mut(lambda b: b["evidence"].update(
        {"pending": [{"claim": "the tax object", "provided_by": {"ticket": "ABC-999",
                                                                 "subtask": "S2"}}]}))),
    ("PND002-type", mut(lambda b: b["evidence"].update(
        {"pending": [{"claim": "the tax object", "provided_by": {"ticket": "ABC-140",
                                                                 "subtask": "S2"}}]}))),
    ("LNK001", mut(lambda b: b["story"]["links"].append(
        {"type": "is blocked by", "key": "ABC-9", "why": "wrong vocabulary"}))),
    ("LNK002", mut(lambda b: b["story"]["links"][0].pop("why"))),
    ("LNK003", mut(lambda b: b["story"].update({"links": []}))),
    # The dossier: what refinement learned that the ticket does not say.
    ("EVI008", mut(lambda b: b["evidence"].update({"ruled_out": []}))),
    ("EVI009", mut(lambda b: b["evidence"]["ruled_out"][0].pop("looked_in"))),
    ("EVI009-conclusion", mut(lambda b: b["evidence"]["ruled_out"][1].pop("conclusion"))),
    ("BRF013", mut(lambda b: b["subtasks"][1]["agent_brief"].pop("preflight"))),
    ("BRF014", mut(lambda b: b["subtasks"][1]["agent_brief"].pop("stop_and_ask"))),
    # Tailoring: the seam a team-tailoring skill layers onto.
    ("TLR001", mut(lambda b: b.pop("tailoring"))),
    ("TLR002", mut(lambda b: b["tailoring"]["applied"][0].update(
        {"key": "budgets.subtask_hours"}))),                # a key no config sets
    ("TLR002-prose", mut(lambda b: b["tailoring"]["applied"].append(
        {"rule": "Subtasks are at most half a day", "mechanism": "config"}))),
    ("TLR003", mut(lambda b: b["tailoring"]["overrides"].append(
        {"rule": "Citations are optional, our code moves too fast",
         "of": "evidence-or-assumption", "reason": "speed",
         "authorised_by": "the team skill"}))),
    ("TLR004", mut(lambda b: b["tailoring"]["overrides"].append(
        {"rule": "No panel on small stories", "of": "gates.adversarial_review"}))),
    # Triage: what the ticket already said about itself.
    ("TRI001", mut(lambda b: b["story"].pop("tracker_meta"))),
    ("TRI002", mut(lambda b: b["story"]["tracker_meta"]["labels"].append("sev1"))),
    ("TRI003", mut(lambda b: (b["story"]["tracker_meta"]["labels"].append("production-issue"),
                              b["subtasks"].pop(3)))),               # S3 is the test subtask
    ("TRI004", mut(lambda b: b["story"]["tracker_meta"]["labels"].append("production-issue"))),
    ("TRI005", mut(lambda b: b["story"]["tracker_meta"]["labels"].append("prod-bug"))),
    ("TRI006", mut(lambda b: (b["story"]["tracker_meta"]["labels"].append("security"),
                              b["story"]["non_functional"].update({"security": "unchanged"})))),
    ("TRI007", mut(lambda b: b["story"]["tracker_meta"]["labels"].append("ops-2"))),
    ("TRI008", mut(lambda b: b["story"]["tracker_meta"]["labels"].append("vulnerability"))),
    ("TRI009", mut(lambda b: b["story"]["triage"].update({"matched": []}))),
    # Example design: partitions, boundaries and the decision table.
    ("AC008", mut(lambda b: b["story"]["acceptance_criteria"][1].update(
        {"examples": [{"case": "DE business, VAT field empty", "expect": "19.00"}]}))),
    ("AC009", mut(lambda b: b["story"]["acceptance_criteria"][0].update(
        {"rule": "Orders above 100 EUR from a business customer are charged zero VAT.",
         "examples": [{"case": "DE business, 150 EUR", "expect": "0.00"}]}))),
    ("DT001", mut(lambda b: b["story"]["decision_table"].update(
        {"rules": b["story"]["decision_table"]["rules"][:-1]}))),          # consumers uncovered
    ("DT002", mut(lambda b: b["story"]["decision_table"]["rules"][0]["when"].update(
        {"vat_number": "perhaps"}))),
    ("DT003", mut(lambda b: b["story"]["decision_table"]["rules"].append(
        {"when": {"customer": "business", "vat_number": "valid", "destination": "eu_other"},
         "then": "destination standard rate"}))),
    ("DT004", mut(lambda b: b["story"]["decision_table"]["conditions"].append(
        {"id": "market", "values": ["m%d" % i for i in range(40)]}))),
    # Cynefin: enough information is not the same as enough knowledge.
    ("CYN001", mut(lambda b: (b["story"]["intake"].update({"domain": "complex"}),
                              b["subtasks"].pop(0)))),                     # S0 is the spike
    ("CYN002", mut(lambda b: b["story"]["intake"].update({"domain": "chaotic"}))),
    ("CYN003", mut(lambda b: b["story"]["intake"].update({"domain": "tricky"}))),
    # Impact map and premortem.
    ("IMP001", mut(lambda b: (b["story"].pop("impact"),
                              b["story"]["intake"]["flags"].append("mechanism-only")))),
    ("IMP002", mut(lambda b: b["story"]["impact"].update({"goal": "fewer manual refunds"}))),
    ("RSK001", mut(lambda b: b["story"]["risks"][0].pop("mitigation"))),
    ("RSK002", mut(lambda b: b["story"]["risks"][1].pop("detection"))),
    ("RSK003", mut(lambda b: b["story"].update({"risks": []}))),
    # Real Options: a deferred decision with no expiry is an unmade decision.
    ("DEC007", mut(lambda b: b["decisions"][1].pop("expires"))),
    ("DEC008", mut(lambda b: b["decisions"][1].pop("waiting_for"))),
    ("NFR002", mut(lambda b: b["story"]["non_functional"].update(
        {"performance": "should feel snappy"}))),
    # Adversarial review: the panel, and the ways a review can be theatre.
    ("REV001", mut(lambda b: b.pop("review"))),
    ("REV001-method", mut(lambda b: b["review"].update({"method": "vibes"}))),
    ("REV002", mut(lambda b: b["review"]["findings"][0].update({"status": "open"}))),
    ("REV003", mut(lambda b: b["review"]["findings"][1].pop("resolution"))),
    ("REV004", mut(lambda b: b["review"]["critics"][4].pop("attempted"))),
    ("REV005", mut(lambda b: b["review"]["findings"][0].update(
        {"locator": "subtasks[99].agent_brief.nowhere"}))),
    ("REV006", mut(lambda b: b["review"].update(
        {"critics": b["review"]["critics"][:2],
         "findings": [f for f in b["review"]["findings"]
                      if f["critic"] in ("implementer", "tester")]}))),
    ("REV007", mut(lambda b: b["review"].update({"bundle_digest": "sha256:deadbeef"}))),
    # A review whose findings were addressed by editing the bundle afterwards is a
    # review of a document that no longer exists.
    ("REV007-drift", mut(lambda b: b["subtasks"][1].update({"estimate_days": 0.75}))),
    ("REV008", mut(lambda b: b["review"].update({"method": "rubber-duck"}))),
    ("REV009", mut(lambda b: b["review"]["findings"][0].update({"severity": "catastrophic"}))),
]


def suite_gates(golden, cfg):
    print("\n-- 1. validator gates --")
    rep = validate(copy.deepcopy(golden), cfg)
    bad = [(i["code"], i["message"]) for i in rep.items]
    check("golden bundle is clean", not bad, bad)
    for code, mutation in MUTATIONS:
        expected = code.split("-")[0]
        rep = validate(mutation(copy.deepcopy(golden)), cfg)
        codes = {i["code"] for i in rep.items}
        check("gate %s" % code, expected in codes, "got %s" % sorted(codes))


# --------------------------------------------------------- suite 2: config parsing

def suite_config(cfg, golden):
    print("\n-- 2. config parsing --")
    cases = [
        ("flow list", "k: [a, b, c]", lambda c: c["k"] == ["a", "b", "c"]),
        ("empty flow list", "k: []", lambda c: c["k"] == []),
        ("quoted colon value", 'k: "refinery:"', lambda c: c["k"] == "refinery:"),
        ("inline comment", "k: 5   # note", lambda c: c["k"] == 5),
        ("hash inside quotes", 'k: "a # b"', lambda c: c["k"] == "a # b"),
        ("bools and null", "a: true\nb: false\nc: null",
         lambda c: c["a"] is True and c["b"] is False and c["c"] is None),
        ("nested map", "a:\n  b:\n    c: 1", lambda c: c["a"]["b"]["c"] == 1),
        ("list of maps with continuation", "a:\n  - x: 1\n    y: 2\n  - x: 3\n    y: 4",
         lambda c: c["a"] == [{"x": 1, "y": 2}, {"x": 3, "y": 4}]),
        ("list of scalars", "a:\n  - one\n  - two", lambda c: c["a"] == ["one", "two"]),
        ("floats", "a: 0.5", lambda c: c["a"] == 0.5),
    ]
    for name, text, ok in cases:
        try:
            parsed = _yaml.loads(text)
            check("yaml: %s" % name, ok(parsed), parsed)
        except Exception as exc:  # noqa: BLE001
            check("yaml: %s" % name, False, exc)

    dod = (cfg.get("validation") or {}).get("definition_of_done") or []
    check("shipped config: DoD kinds are lists",
          bool(dod) and all(isinstance(r.get("applies_to_kinds"), list) for r in dod), dod)
    check("shipped config: repos parsed",
          isinstance((cfg.get("evidence") or {}).get("repos"), list))
    check("shipped config: every spec key group present",
          all(k in cfg for k in ("budgets", "tracker", "evidence", "validation")))

    bad_cfg = copy.deepcopy(cfg)
    bad_cfg["budgets"]["max_subtaks"] = 12
    bad_cfg["tracker"]["agent_brief"]["sinkk"] = "x"
    rep = validate(copy.deepcopy(golden), bad_cfg)
    msgs = [i["message"] for i in rep.items if i["code"] == "CFG001"]
    check("config lint: typo'd keys reported", len(msgs) == 2, msgs)

    broken = copy.deepcopy(cfg)
    broken["validation"]["definition_of_done"][0]["applies_to_kinds"] = "feature, test"
    rep = validate(copy.deepcopy(golden), broken)
    check("config lint: DoD kinds as string is an error",
          "DOD003" in {i["code"] for i in rep.items})


# ---------------------------------------------------------------- suite 3: markup

def suite_markup():
    print("\n-- 3. markup --")
    md = ("## Head\n\nSome **bold** and `code`.\n\n- one\n- two\n\n| a | b |\n|---|---|\n"
          "| 1 | 2 |\n\n> note\n\n```json\n{\"x\": 1}\n```\n\n---\n")
    wiki = to_wiki(md)
    check("wiki: heading", "h2. Head" in wiki, wiki)
    check("wiki: bold and code", "*bold*" in wiki and "{{code}}" in wiki)
    check("wiki: bullets", "\n* one" in "\n" + wiki)
    check("wiki: code block", "{code:json}" in wiki)
    check("wiki: table header", "||a||b||" in wiki)
    check("wiki: no markdown left", "**" not in wiki and "## " not in wiki)
    check("wiki: rule directly after a paragraph is not swallowed",
          "----" in to_wiki("text\n---\nmore\n"), to_wiki("text\n---\nmore\n"))

    adf = to_adf(md)
    check("adf: doc envelope", adf.get("type") == "doc" and adf.get("version") == 1)
    types = [n["type"] for n in adf["content"]]
    check("adf: node types", types[:3] == ["heading", "paragraph", "bulletList"], types)
    check("adf: strong mark present",
          any(m.get("type") == "strong"
              for n in adf["content"] if n["type"] == "paragraph"
              for c in n["content"] for m in c.get("marks", [])))
    check("adf: serialises", isinstance(json.dumps(adf), str))
    check("adf: no empty text nodes",
          all(c.get("text") for n in adf["content"] if n.get("content")
              for c in n["content"] if c.get("type") == "text"))

    plain = to_plaintext(md)
    check("plaintext: markers stripped",
          "**" not in plain and "`" not in plain and "|" not in plain)
    html = to_html(md)
    check("html: escaped and tagged", "<h2>Head</h2>" in html and "<strong>bold</strong>" in html)


# -------------------------------------------------------------- suite 4: pipeline

FIXTURE = {
    "api/src/billing/tax.py": "from decimal import Decimal\n\n\nclass TaxCalculator:\n"
                              "    def rate_for(self, order):\n        return Decimal('0.21')\n",
    "api/tests/billing/test_tax.py": "def test_rate_for():\n    assert True\n",
    "api/openapi.yaml": "openapi: 3.0.0\n",
    "api/pyproject.toml": '[project]\nname = "api"\ndependencies = ["fastapi>=0.1"]\n',
    "api/CODEOWNERS": "src/billing/** @team-billing\n",
    "web/openapi.yaml": "openapi: 3.0.0\n",
    "web/package.json": '{"name":"web","scripts":{"test":"vitest","lint":"eslint ."}}\n',
    "web/src/OrderSummary.tsx": "export function OrderSummary() { return null; }\n",
}
FIXTURE_CFG = """version: 1
evidence:
  sources:
    - type: cached_manifest
      dir: .refinery/manifests
    - type: targeted_scan
      budget_files: 500
      budget_seconds: 30
  repos:
    - name: api
      path: ../api
    - name: web
      path: ../web
  contract_globs:
    - "**/openapi*.yaml"
"""


def run(argv, cwd):
    proc = subprocess.run([sys.executable] + argv, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def suite_pipeline():
    print("\n-- 4. pipeline --")
    tmp = tempfile.mkdtemp(prefix="refinery-selftest-")
    try:
        for rel, body in FIXTURE.items():
            path = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(body)
        ws = os.path.join(tmp, "ws")
        os.makedirs(ws)
        with open(os.path.join(ws, "refinery.yaml"), "w", encoding="utf-8") as fh:
            fh.write(FIXTURE_CFG)

        ev = os.path.join(HERE, "evidence.py")
        code, out = run([ev, "manifest", "--config", "refinery.yaml"], ws)
        check("evidence: manifest exits 0", code == 0, out)
        mdir = os.path.join(ws, ".refinery", "manifests")
        files = sorted(os.listdir(mdir)) if os.path.isdir(mdir) else []
        check("evidence: two manifests written", len(files) == 2, files)
        man = json.load(open(os.path.join(mdir, files[0]))) if files else {}
        check("evidence: test command detected", bool(man.get("commands", {}).get("test")),
              man.get("commands"))
        check("evidence: CODEOWNERS parsed", bool(man.get("owners")), man.get("owners"))

        code, out = run([ev, "scan", "--config", "refinery.yaml", "-q", "TaxCalculator"], ws)
        check("evidence: scan finds the symbol", code == 0 and "tax.py" in out, out)
        code, out = run([ev, "scan", "--config", "refinery.yaml", "-q", "NoSuchSymbolHere"], ws)
        check("evidence: empty scan is not an error", code == 0 and "0 hit" in out, out)
        code, out = run([ev, "contracts", "--config", "refinery.yaml"], ws)
        check("evidence: cross-repo edge found",
              "edge" in out and "direction guessed" in out, out)
        # ttl: an old manifest must be rebuilt even when the sha cannot change (nogit).
        stale = os.path.join(mdir, files[0])
        os.utime(stale, (0, 0))
        code, out = run([ev, "manifest", "--config", "refinery.yaml"], ws)
        check("evidence: expired manifest is rebuilt", "expired" in out and
              os.path.getmtime(stale) > 1, out)
        # inherit: the next story in the same area re-checks the dossier, it does
        # not re-derive it - and nothing carried is trusted while the repo has moved.
        nextb = os.path.join(ws, "next-story.json")
        with open(nextb, "w", encoding="utf-8") as fh:
            json.dump({"schema_version": "1.0", "story": {"key": "ABC-200"}, "subtasks": []}, fh)
        code, out = run([ev, "inherit", "--from", GOLDEN, "--bundle", nextb, "--write",
                         "--config", "refinery.yaml"], ws)
        carried = json.load(open(nextb, encoding="utf-8"))
        ev_block = carried.get("evidence") or {}
        check("inherit: the dossier comes across", code == 0
              and len(ev_block.get("ruled_out") or []) == 4
              and len(ev_block.get("glossary") or []) == 4, out)
        check("inherit: every carried entry says where it came from",
              all(e.get("inherited_from", "").startswith("ABC-123")
                  for f in ("ruled_out", "glossary", "conventions") for e in ev_block.get(f) or []))
        check("inherit: a moved repo marks everything stale rather than trusting it",
              all(e.get("stale") for e in ev_block["ruled_out"]), out)
        check("inherit: the predecessor is recorded",
              carried["story"]["series"]["predecessors"][0]["key"] == "ABC-123")
        run([ev, "inherit", "--from", GOLDEN, "--bundle", nextb, "--write",
             "--config", "refinery.yaml"], ws)
        again = json.load(open(nextb, encoding="utf-8"))
        check("inherit: running it twice does not duplicate the dossier",
              len(again["evidence"]["ruled_out"]) == 4
              and len(again["story"]["series"]["predecessors"]) == 1)
        codes = {i["code"] for i in validate(again, load_config(CONFIG)).items}
        check("inherit: carried-but-unverified evidence keeps saying so", "SER001" in codes)

        code, out = run([ev, "init", "--config", "init.yaml", "--root", ".."], ws)
        check("evidence: init scaffolds a config",
              code == 0 and os.path.exists(os.path.join(ws, "init.yaml")), out)

        val, emit = os.path.join(HERE, "validate.py"), os.path.join(HERE, "emit.py")
        code, out = run([val, GOLDEN, "--config", CONFIG], ws)
        check("validate: golden exits 0", code == 0, out)

        broken = json.load(open(GOLDEN, encoding="utf-8"))
        broken["subtasks"][1]["estimate_days"] = 5
        bpath = os.path.join(ws, "broken.json")
        with open(bpath, "w", encoding="utf-8") as fh:
            json.dump(broken, fh)
        code, out = run([val, bpath, "--config", CONFIG], ws)
        check("validate: broken exits 1", code == 1, out)
        code, out = run([val, bpath, "--config", CONFIG, "--json"], ws)
        check("validate: --json is parseable", json.loads(out)["ready"] is False)
        code, out = run([val, os.path.join(ws, "nope.json"), "--config", CONFIG], ws)
        check("validate: missing file exits 2", code == 2, out)

        for adapter in ("jira", "github", "gitlab", "linear", "azure-devops", "markdown"):
            code, out = run([emit, GOLDEN, "--config", CONFIG, "--adapter", adapter,
                             "--out", "out_" + adapter], ws)
            check("emit: %s exits 0" % adapter, code == 0, out)
        plan = json.load(open(os.path.join(ws, "out_jira", "push-plan.json")))
        check("emit: waves derived", len(plan["waves"]) == 5, plan["waves"])
        check("emit: wave 4 is parallel", len(plan["waves"][3]["subtasks"]) == 3)
        check("emit: no network claimed", plan["network"].startswith("none"))
        payload = json.load(open(os.path.join(ws, "out_jira", "payloads", "ABC-123-S1.json")))
        check("emit: adf body rendered", isinstance(payload["body_rendered"], dict)
              and payload["body_rendered"].get("type") == "doc")
        gh = json.load(open(os.path.join(ws, "out_github", "payloads", "ABC-123-S1.json")))
        check("emit: github body stays markdown", isinstance(gh["body_rendered"], str))
        with open(os.path.join(ws, "out_markdown", "preview.md"), encoding="utf-8") as fh:
            md_preview = fh.read()
        check("emit: the decision table reaches the ticket as a table",
              "**Decision table**" in md_preview and "| customer | vat_number |" in md_preview)
        check("emit: risks carry their detection signal", "_(detected by:" in md_preview)
        check("emit: a held option shows what it waits for and when it expires",
              "stays open until:" in md_preview and "Expires" in md_preview)
        check("emit: the impact goal heads the ticket", "**Goal**:" in md_preview)
        with open(os.path.join(ws, "out_markdown", "context", "ABC-123-context.md"),
                  encoding="utf-8") as fh:
            shared = fh.read()
        check("emit: the shared context carries what was ruled out",
              "Already ruled out" in shared and "VIES client" in shared)
        check("emit: the shared context carries the glossary and the conventions",
              "reverse charge" in shared and "money.round_half_up" in shared)
        check("emit: it says what is decided and what is deliberately still open",
              "do not re-open" in shared and "do not decide it in passing" in shared)
        check("emit: it dates itself, so a stale brief is detectable",
              "Freshness" in shared and "api@9f2c1ab" in shared)
        # The brief itself may be fenced into the description when the tracker has
        # nowhere else to put it. What must stay clean is the part a person reads.
        human_half = md_preview.split("## S1 —")[-1].split("<!-- AGENT-BRIEF")[0]
        check("emit: the human half of the ticket carries no preflight plumbing",
              "grep -n" not in human_half and "stop_and_ask" not in human_half,
              human_half[-200:])
        check("emit: the ticket points at the shared context instead of inlining it",
              "context/ABC-123-context.md" in human_half)
        for adapter in ("jira", "github", "linear"):
            other = open(os.path.join(ws, "out_" + adapter, "context",
                                      "ABC-123-context.md"), encoding="utf-8").read()
            check("emit: the shared context is byte-identical for %s - a stable prefix"
                  % adapter, other == shared)
        check("emit: triage says which labels changed the refinement",
              "## Triage" in md_preview and "**compliance**" in md_preview
              and "blocks ABC-131" in md_preview)
        parent = json.load(open(os.path.join(ws, "out_jira", "payloads",
                                             "ABC-123-story.json")))
        check("emit: a push does not delete the labels somebody set",
              all(x in parent["labels"] for x in ("compliance", "team-billing"))
              and "refinery:story" in parent["labels"], parent["labels"])
        check("emit: unfixed findings are what the approver sees",
              "These findings were not fixed" in md_preview)

        # A follow-up story cites work that has not been implemented yet. It must
        # reach both audiences: the ticket says what is missing, the shared context
        # tells the implementor not to go hunting for it.
        follow = json.load(open(GOLDEN, encoding="utf-8"))
        follow["evidence"]["pending"] = [{
            "claim": "tax.reason on the order response",
            "provided_by": {"ticket": "ABC-123", "subtask": "S2",
                            "bundle": ".refinery/bundles/ABC-123@2026-09-02.json"},
            "expected_path": "api/src/api/orders/serializers.py",
            "note": "Shape is fixed by AC3 there; do not re-specify it here."}]
        follow["story"]["links"] = [{"type": "blocked_by", "key": "ABC-123",
                                     "why": "the tax object it reads does not exist yet"}]
        fpath = os.path.join(ws, "follow-up.json")
        with open(fpath, "w", encoding="utf-8") as fh:
            json.dump(follow, fh)
        code, out = run([emit, fpath, "--config", CONFIG, "--adapter", "jira",
                         "--out", "out_follow"], ws)
        body = open(os.path.join(ws, "out_follow", "preview.md"), encoding="utf-8").read()
        shared = open(os.path.join(ws, "out_follow", "context", "ABC-123-context.md"),
                      encoding="utf-8").read()
        check("emit: the ticket says what does not exist yet and who makes it",
              "## Prerequisites" in body and "Does not exist yet" in body
              and "ABC-123 / S2" in body, out)
        check("emit: the implementor is told not to hunt for it",
              "Not there yet" in shared and "do not substitute something that" in shared)
        plan = json.load(open(os.path.join(ws, "out_follow", "push-plan.json")))
        blocked = [l for l in plan["links"] if l["type"] == "blocked_by"]
        check("emit: the prerequisite becomes a real link in the tracker's vocabulary",
              blocked and blocked[0]["adapter_type"] == "is blocked by", plan["links"])
        codes = {i["code"] for i in validate(follow, load_config(CONFIG)).items}
        check("validate: a linked, attributed prerequisite passes",
              not {"PND001", "PND002"} & codes, sorted(codes))

        tiny = os.path.join(ws, "tiny.yaml")
        with open(CONFIG, encoding="utf-8") as fh:
            text = fh.read().replace("max_description_chars: 32767",
                                     "max_description_chars: 900")
        with open(tiny, "w", encoding="utf-8") as fh:
            fh.write(text)
        code, out = run([emit, GOLDEN, "--config", tiny, "--adapter", "markdown",
                         "--out", "out_deg"], ws)
        briefs = os.listdir(os.path.join(ws, "out_deg", "briefs"))
        check("emit: oversize description really moves the brief",
              "moved to repo_file" in out and len(briefs) == 7, (out, briefs))

        nxt = json.load(open(GOLDEN, encoding="utf-8"))
        nxt["subtasks"] = [s for s in nxt["subtasks"] if s["id"] != "S5"]
        nxt["coverage"]["AC3"] = ["S2", "S3"]
        nxt["subtasks"][1]["estimate_days"] = 0.75
        npath = os.path.join(ws, "next.json")
        with open(npath, "w", encoding="utf-8") as fh:
            json.dump(nxt, fh)
        code, out = run([emit, npath, "--config", CONFIG, "--previous", GOLDEN,
                         "--out", "out_upd"], ws)
        plan = json.load(open(os.path.join(ws, "out_upd", "push-plan.json")))
        check("emit: update mode detected", plan["mode"] == "update", plan["mode"])
        check("emit: update mode never re-creates the parent",
              all(c["id"] != "ABC-123" for c in plan["creates"]), plan["creates"])
        check("emit: unchanged story is not listed for update",
              "ABC-123" not in plan["updates"], plan["updates"])
        nxt2 = json.load(open(GOLDEN, encoding="utf-8"))
        nxt2["story"]["summary_human"] += " Reworded."
        n2 = os.path.join(ws, "next2.json")
        with open(n2, "w", encoding="utf-8") as fh:
            json.dump(nxt2, fh)
        run([emit, n2, "--config", CONFIG, "--previous", GOLDEN, "--out", "out_upd2"], ws)
        plan2 = json.load(open(os.path.join(ws, "out_upd2", "push-plan.json")))
        check("emit: reworded story is listed for update",
              plan2["updates"] == ["ABC-123"] and plan2["creates"] == [], plan2["updates"])
        check("emit: orphan reported not deleted", plan["orphans"] == ["S5"], plan["orphans"])
        check("emit: changed subtask listed", plan["updates"] == ["S1"], plan["updates"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def suite_docs():
    """SKILL.md is the interface. A flag that no longer exists, or a reference file
    that was renamed, breaks the skill just as thoroughly as a bad regex."""
    print("\n-- 16. docs consistency --")
    import re
    with open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8") as fh:
        skill = fh.read()

    # Every path mentioned in SKILL.md must exist.
    referenced = set(re.findall(r"`((?:references|assets|scripts|evals)/[\w./-]+)`", skill))
    for rel in sorted(referenced):
        check("doc path exists: %s" % rel, os.path.exists(os.path.join(ROOT, rel)))
    check("SKILL.md mentions every reference file",
          all(("references/%s" % f) in skill
              for f in os.listdir(os.path.join(ROOT, "references"))),
          sorted(os.listdir(os.path.join(ROOT, "references"))))

    # Every documented command must use flags the script actually defines.
    cmds = re.findall(r"^python (scripts/\w+\.py) ([^\n]*)$", skill, re.M)
    check("SKILL.md documents commands", len(cmds) >= 5, len(cmds))
    for script, rest in cmds:
        path = os.path.join(ROOT, script)
        if not check("script exists: %s" % script, os.path.exists(path)):
            continue
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
        declared = {"--help", "-h"}
        for call in re.findall(r"add_argument\(([^)]*)\)", source, re.S):
            head = call.split(",")
            for token in head:
                m = re.match(r'\s*"(-{1,2}[\w-]+)"\s*$', token)
                if m:
                    declared.add(m.group(1))
                elif token.strip().startswith(('"', "'")) and "=" not in token:
                    continue
        used = [t for t in rest.split() if t.startswith("-")]
        unknown = [f for f in used if f not in declared]
        check("flags valid: %s %s" % (script, " ".join(used)), not unknown, unknown)
        subs = set(re.findall(r'add_parser\(\s*"(\w+)"', source))
        first = rest.split()[0] if rest.split() else ""
        if subs and first and not first.startswith("-"):
            check("subcommand valid: %s %s" % (script, first), first in subs, sorted(subs))

    # Every code mentioned in a reference must exist in a script that can emit it.
    vsrc = ""
    for name in ("validate.py", "batch.py", "criteria.py"):
        with open(os.path.join(HERE, name), encoding="utf-8") as fh:
            vsrc += fh.read()
    # {2,6}: AC and DT are two-letter prefixes; {3,6} silently skipped them for months.
    real = set(re.findall(r'"([A-Z]{2,6}\d{3})"', vsrc))
    docs = ""
    for name in os.listdir(os.path.join(ROOT, "references")):
        with open(os.path.join(ROOT, "references", name), encoding="utf-8") as fh:
            docs += fh.read()
    with open(CONFIG, encoding="utf-8") as fh:
        docs += fh.read()
    cited = set(re.findall(r"\b([A-Z]{2,6}\d{3})\b", docs + skill))
    check("no invented validator codes in docs", cited <= real, sorted(cited - real))

    # code -> docs: the registries against the call sites, both ways, and the generated
    # index against the generator. 'Emitted' is syntactic - a literal as the first
    # argument of an error/warn/report/add call, or criteria.py's ("WARN", "CODE", ...)
    # tuple - so a registry key (`"CODE": (`) can never count as its own emitter.
    import validate as V
    emit_rx = re.compile(r'(?:\b(?:error|warn|report|add)\(\s*|\(\s*"(?:ERROR|WARN)"\s*,\s*)'
                         r'"([A-Z]{2,6}\d{3})"')
    site_rx = re.compile(r'\b(rep\.error|rep\.warn|error|warn|report|add)\(\s*"([A-Z]{2,6}\d{3})"'
                         r'|\(\s*"(ERROR|WARN)"\s*,\s*"([A-Z]{2,6}\d{3})"')
    emitted, sites = set(), {}
    for name in ("validate.py", "batch.py", "criteria.py"):
        with open(os.path.join(HERE, name), encoding="utf-8") as fh:
            src = fh.read()
        emitted |= set(emit_rx.findall(src))
        for m in site_rx.finditer(src):
            callee, code = (m.group(1), m.group(2)) if m.group(2) else (m.group(3), m.group(4))
            sites.setdefault(code, set()).add(
                {"rep.error": "error", "error": "error", "ERROR": "error",
                 "rep.warn": "warn", "warn": "warn", "WARN": "warn"}.get(callee, "config"))
    registered = {r["code"]: r for r in V.all_codes()}
    check("codes: every emitted code is registered", emitted <= set(registered),
          sorted(emitted - set(registered)))
    check("codes: no registered code is dead", set(registered) <= emitted,
          sorted(set(registered) - emitted))
    wrong = []
    for code, r in registered.items():
        s = sites.get(code, set())
        want = "config" if "config" in s else "error | warn" if s >= {"error", "warn"} \
            else (next(iter(s)) if s else "?")
        if r["severity"] != want:
            wrong.append("%s registered %r, call sites say %r" % (code, r["severity"], want))
    check("codes: severity matches the call sites", not wrong, wrong)
    weak = [c for c, r in registered.items()
            if len(r["meaning"].split()) < 6 or r["meaning"].strip() == c
            or re.search(r"\bTODO\b|\bTBD\b|\|", r["meaning"])]
    check("codes: every meaning is a meaning", not weak, weak)
    index = os.path.join(ROOT, "references", "codes.md")
    try:
        with open(index, encoding="utf-8") as fh:
            committed = fh.read().replace("\r\n", "\n")
    except OSError:
        committed = None
    check("codes: references/codes.md is current",
          committed is not None
          and committed.rstrip("\n") == V.render_codes("markdown").rstrip("\n"),
          "regenerate with `python scripts/validate.py --codes --markdown > references/codes.md`")


INTAKE_TEXTS = {
    "thin": ("Make the dashboard faster.", "feature", "insufficient"),
    "mechanism": ("Add a Redis cache in front of the reporting API.", "feature", "insufficient"),
    "feature_no_trigger": (
        "As a finance user I want to export invoices as CSV from the Invoices screen so that "
        "I can reconcile them in Exact without retyping. Only paid invoices; drafts are out "
        "of scope. Export should finish under 5 seconds for 1000 rows.", "feature", "scoutable"),
    "feature_full": (
        "As a finance user I want to export invoices as CSV when I press Export on the "
        "Invoices screen, so that I can reconcile them in Exact.", "feature", "sufficient"),
    "bug_thin": ("Uploading a big file gives an error. Please fix.", "bug", "insufficient"),
    "bug_full": (
        "Bug in production since v2.4.1 (Chrome 128): uploading a file over 10MB on "
        "/documents/upload returns a 500 instead of a validation message.\nSteps:\n1. Log in "
        "as a tenant admin\n2. Go to Documents > Upload\n3. Pick an 11MB PDF\nExpected: "
        "\"File too large (max 10MB)\" message.\nActual: HTTP 500, UploadHandler stack trace "
        "in logs. Affects all tenants, every time.", "bug", "sufficient"),
    "dutch_feature": (
        "Als klantenservice-medewerker wil ik bij het openen van een order direct de "
        "retourstatus zien, zodat ik de klant niet hoef door te verbinden. Alleen orders van "
        "de laatste 90 dagen; oudere orders vallen buiten scope. Wanneer de retour is ontvangen "
        "moet dat binnen 1 minuut zichtbaar zijn in OrderDetail.", "feature", "sufficient"),
    "dutch_bug_thin": ("De export werkt niet meer, foutmelding. Graag fixen.", "bug", "insufficient"),
    "dutch_bug_full": (
        "Bug op productie sinds v3.1: als je in OrderDetail op Retourneren klikt krijg je een "
        "500.\nStappen:\n1. Open een order van gisteren\n2. Klik Retourneren\nVerwacht: "
        "retourformulier.\nWerkelijk: HTTP 500, ReturnHandler stacktrace. Gebeurt altijd, alle "
        "klanten.", "bug", "sufficient"),
}


def suite_intake():
    print("\n-- 5. intake detection --")
    from intake import assess
    reachable_cfg = {"evidence": {"repos": [{"name": "self", "path": ROOT}]}}
    unreachable_cfg = {"evidence": {"repos": [{"name": "ghost", "path": "/nonexistent/x"}]}}
    for name, (text, kind, expected) in INTAKE_TEXTS.items():
        rep = assess(text, reachable_cfg)
        check("intake kind: %s -> %s" % (name, kind), rep["kind"] == kind, rep["kind"])
        check("intake verdict: %s -> %s" % (name, expected), rep["verdict"] == expected,
              "%s (missing %s)" % (rep["verdict"], [d["id"] for d in rep["dimensions"]
                                                    if d["status"] == "missing"]))
    rep = assess(INTAKE_TEXTS["feature_no_trigger"][0], unreachable_cfg)
    check("intake: scoutable needs a reachable repo", rep["verdict"] == "insufficient", rep["verdict"])
    rep = assess(INTAKE_TEXTS["mechanism"][0], reachable_cfg)
    check("intake: mechanism-only flagged", any("mechanism" in f for f in rep["flags"]), rep["flags"])
    rep = assess(INTAKE_TEXTS["dutch_feature"][0], reachable_cfg)
    check("intake: Dutch detected", rep["lang"] == "nl", rep["lang"])
    check("intake: Dutch unit is a success signal",
          any(d["id"] == "success_signal" and d["status"] == "present" for d in rep["dimensions"]))
    check("intake: domain noun anchor", any(a["value"] == "OrderDetail" for a in rep["anchors"]),
          rep["anchors"])
    rep = assess(INTAKE_TEXTS["dutch_bug_full"][0], reachable_cfg)
    check("intake: Dutch bug gets Dutch questions", rep["lang"] == "nl", rep["lang"])
    rep = assess(INTAKE_TEXTS["thin"][0], reachable_cfg)
    check("intake: the subject noun is not a success signal",
          not any(d["id"] == "success_signal" and d["status"] == "present" for d in rep["dimensions"]))
    rep = assess(INTAKE_TEXTS["bug_full"][0], reachable_cfg)
    check("intake: every present dimension quotes the source",
          all(d["evidence"].lower() in " ".join(INTAKE_TEXTS["bug_full"][0].split()).lower()
              for d in rep["dimensions"] if d["status"] == "present"))

    # --write must produce a bundle whose intake block the validator understands.
    tmp = tempfile.mkdtemp(prefix="refinery-intake-")
    try:
        bpath = os.path.join(tmp, "b.json")
        with open(GOLDEN, encoding="utf-8") as fh:
            b = json.load(fh)
        b["story"].pop("intake")
        b["story"]["source_text"] = INTAKE_TEXTS["thin"][0]
        b["subtasks"] = []
        with open(bpath, "w", encoding="utf-8") as fh:
            json.dump(b, fh)
        code, out = run([os.path.join(HERE, "intake.py"), "assess", "--bundle", bpath,
                         "--write", "--config", CONFIG], tmp)
        check("intake --write: exit code carries the verdict", code == 4, (code, out[-200:]))
        with open(bpath, encoding="utf-8") as fh:
            b2 = json.load(fh)
        check("intake --write: intake block written", b2["story"].get("intake", {}).get("verdict")
              == "insufficient")
        added = [q for q in b2["open_questions"] if q.get("dimension")]
        check("intake --write: one blocking question per missing required dimension",
              sum(1 for q in added if q["blocking"]) == 3, added)
        rep = validate(b2, load_config(CONFIG))
        codes = {i["code"] for i in rep.items}
        check("intake --write: validator sees a not-ready bundle, not a broken one",
              "READY001" in codes and "INT003" not in codes and "INT004" not in codes,
              sorted(codes))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def suite_tailoring():
    """Users layer a team skill over this one. The seam has to hold: a gate a team
    switches off stays visible, and an invariant stays refused."""
    print("\n-- 6. tailoring seam --")
    from validate import INVARIANTS
    cfg = load_config(CONFIG)
    with open(GOLDEN, encoding="utf-8") as fh:
        golden = json.load(fh)

    check("tailoring: the shipped config declares a source",
          bool((cfg.get("tailoring") or {}).get("source")))
    check("tailoring: the example records the tailoring its config declares",
          golden["tailoring"]["source"] == cfg["tailoring"]["source"])
    check("tailoring: every 'config' rule in the example names a key that is really set",
          all(_yaml.get(cfg, e["key"], None) is not None
              for e in golden["tailoring"]["applied"] if e.get("mechanism") == "config"))

    # A team may switch the panel off. It may not do so invisibly.
    off_cfg = copy.deepcopy(cfg)
    off_cfg["gates"]["adversarial_review"] = "off"
    silent = copy.deepcopy(golden)
    silent.pop("review")
    codes = {i["code"] for i in validate(copy.deepcopy(silent), off_cfg).items}
    check("tailoring: skipping the panel silently is reported", "TLR005" in codes, sorted(codes))
    disclosed = copy.deepcopy(silent)
    disclosed["tailoring"]["overrides"].append(
        {"rule": "No blind panel on stories under three subtasks",
         "of": "gates.adversarial_review", "reason": "agreed with Product for maintenance work",
         "authorised_by": "Sanne (Product)"})
    codes = {i["code"] for i in validate(disclosed, off_cfg).items}
    check("tailoring: disclosing it clears the warning, and REV001 stays off",
          "TLR005" not in codes and "REV001" not in codes, sorted(codes))

    # The invariants are not negotiable, whatever the team skill says.
    for invariant in INVARIANTS:
        b = copy.deepcopy(golden)
        b["tailoring"]["overrides"] = [{"rule": "house rule", "of": invariant,
                                        "reason": "we are fast", "authorised_by": "A. Person"}]
        codes = {i["code"] for i in validate(b, cfg).items}
        check("tailoring: %s cannot be overridden" % invariant, "TLR003" in codes)

    check("tailoring: the copyable team skill exists and states the invariants",
          all(inv in open(os.path.join(ROOT, "assets", "templates",
                                       "team-tailoring-skill.md"), encoding="utf-8").read()
              for inv in INVARIANTS))
    with open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8") as fh:
        skill = fh.read()
    check("tailoring: SKILL.md carries the invariants, not only the reference",
          all(inv in skill for inv in INVARIANTS))


def suite_triage():
    """A label is a decision somebody already made. These check that the policy
    reads it the way the config says, and that a push cannot delete it."""
    print("\n-- 7. triage --")
    from triage import policy_for
    cfg = load_config(CONFIG)

    cases = [
        ("compliance label", {"labels": ["compliance"]},
         lambda m, p, u: p.get("add_critics") == ["stakeholder"] and not u),
        ("production finding routes to bugfix", {"labels": ["production-issue"]},
         lambda m, p, u: p.get("profile") == "bugfix" and p.get("kind") == "bug"
         and "first_seen" in p["require_dimensions"] and "operator" in p["add_critics"]),
        ("sev1 stops refinement", {"labels": ["sev-1"]},
         lambda m, p, u: p.get("route") == "incident"),
        ("incident wins over production-issue regardless of label order",
         {"labels": ["production-issue", "sev2"]},
         lambda m, p, u: p.get("route") == "incident" and p.get("profile") == "bugfix"),
        ("ignored labels are not reported", {"labels": ["team-billing", "sprint-42"]},
         lambda m, p, u: not m and not u),
        ("an unrecognised label is reported", {"labels": ["ops-2"]},
         lambda m, p, u: u == ["ops-2"]),
        ("components can match a rule but are not reported unknown",
         {"labels": [], "components": ["security"]},
         lambda m, p, u: "security" in p["must_answer_nfr"] and not u),
        ("no metadata, no consequences", {},
         lambda m, p, u: not m and not u and p.get("route") == "refine"),
        ("lists from several rules merge",
         {"labels": ["security", "compliance", "customer-escalation"]},
         lambda m, p, u: len(m) == 3 and set(p["add_critics"]) == {"security", "stakeholder"}),
    ]
    for name, meta, ok in cases:
        matched, policy, unknown = policy_for(meta, cfg)
        try:
            check("triage: %s" % name, ok(matched, policy, unknown),
                  (matched, {k: v for k, v in policy.items() if v}, unknown))
        except Exception as exc:  # noqa: BLE001
            check("triage: %s" % name, False, exc)

    check("triage: every critic a shipped rule adds actually exists",
          all(c in __import__("review").CRITICS
              for rule in (cfg.get("triage") or {}).get("labels") or []
              for c in rule.get("add_critics") or []),
          [c for rule in (cfg.get("triage") or {}).get("labels") or []
           for c in rule.get("add_critics") or []])

    with open(GOLDEN, encoding="utf-8") as fh:
        golden = json.load(fh)
    recorded = golden["story"]["triage"]
    _, policy, _ = policy_for(golden["story"]["tracker_meta"], cfg)
    check("triage: the shipped example's triage is what its labels produce",
          {m["id"] for m in recorded["matched"]} ==
          {m["id"] for m in policy_for(golden["story"]["tracker_meta"], cfg)[0]}
          and recorded.get("must_answer_nfr") == policy.get("must_answer_nfr"))


def suite_criteria():
    """A criterion code is a public reference the moment it leaves the session.
    These are about it still meaning the same thing next time."""
    print("\n-- 8. criterion codes --")
    import criteria as C

    with open(GOLDEN, encoding="utf-8") as fh:
        prior = json.load(fh)

    nxt = copy.deepcopy(prior)
    acs = nxt["story"]["acceptance_criteria"]
    acs[1]["rule"] = "A missing, malformed or unverifiable VAT number falls back to the " \
                     "destination standard rate."                       # reworded, same rule
    del acs[2]                                                          # AC3 retired
    acs.append({"rule": "A zero-VAT order is reported to Finance within one working day.",
                "examples": [{"case": "x", "expect": "y"}]})            # genuinely new
    pasted = dict(acs[0])
    pasted.pop("id")
    acs.append(pasted)                                                  # back, without its code
    del acs[0]
    actions, retired = C.assign(nxt, prior, "AC")
    by_kind = {code: what for what, code, _ in actions}
    check("criteria: a reworded criterion keeps its code", by_kind.get("AC2") == "kept")
    check("criteria: a criterion pasted back without its code is recovered, not renumbered",
          by_kind.get("AC1") == "recovered", actions)
    check("criteria: a new criterion takes the next free code, not the retired one",
          by_kind.get("AC5") == "assigned" and "AC3" not in by_kind, actions)
    check("criteria: the deleted code is retired rather than freed", retired == ["AC3"], retired)
    check("criteria: a stable re-refinement reports nothing that moved",
          not [f for f in C.check(nxt, prior) if f[0] == "ERROR"], C.check(nxt, prior))

    # The classic: insert at the top, shift everything down.
    shifted = copy.deepcopy(prior)
    acs = shifted["story"]["acceptance_criteria"]
    for i, ac in enumerate(acs):
        ac["id"] = "AC%d" % (i + 2)
    acs.insert(0, {"id": "AC1", "rule": "Only paid orders are considered for reverse charge.",
                   "examples": [{"case": "x", "expect": "y"}]})
    moved = [f for f in C.check(shifted, prior) if f[1] == "AC011"]
    check("criteria: renumbering is caught, and named as renumbering", len(moved) == 3, moved)

    reused = copy.deepcopy(prior)
    reused["story"]["retired_criterion_ids"] = ["AC2"]
    codes = {i["code"] for i in validate(reused, load_config(CONFIG)).items}
    check("criteria: a retired code back in use is an error", "AC011" in codes)
    mixed = copy.deepcopy(prior)
    mixed["story"]["acceptance_criteria"][1]["id"] = "C2"
    mixed["coverage"] = {}
    codes = {i["code"] for i in validate(mixed, load_config(CONFIG)).items}
    check("criteria: two schemes in one story is reported", "AC010" in codes, sorted(codes))
    check("criteria: the shipped example carries one scheme and no retired code",
          "AC010" not in {i["code"] for i in validate(copy.deepcopy(prior),
                                                      load_config(CONFIG)).items})


def suite_declutter():
    """Every other budget is a ceiling. Without a floor the plan drifts into slivers,
    and each extra subtask costs another load of the shared context for nothing."""
    print("\n-- 9. de-cluttering --")
    from validate import check_clutter, Report
    cfg = load_config(CONFIG)
    with open(GOLDEN, encoding="utf-8") as fh:
        golden = json.load(fh)

    def findings(bundle):
        rep = Report()
        check_clutter(bundle, cfg, bundle.get("subtasks") or [], rep)
        return {(i["code"], i["where"]) for i in rep.items}

    check("declutter: a plan of real subtasks is left alone", not findings(golden))

    sliver = copy.deepcopy(golden)
    s1 = sliver["subtasks"][1]
    sliver["subtasks"].insert(2, dict(
        s1, id="S1b", estimate_days=0.2, depends_on=["S1"],
        agent_brief=dict(s1["agent_brief"],
                         change_surface=[{"path": "src/billing/flags.py", "role": "modify"}])))
    check("declutter: a 0.2d one-file subtask is a commit, and is named as one",
          ("SUB017", "subtask S1b") in findings(sliver))

    chain = copy.deepcopy(golden)
    s2 = chain["subtasks"][2]
    half = dict(s2, id="S2b", estimate_days=0.25, depends_on=["S2"], covers=["AC3"],
                agent_brief=dict(s2["agent_brief"],
                                 change_surface=[{"path": "src/api/orders/serializers.py",
                                                  "role": "modify"}]))
    chain["subtasks"].insert(3, half)
    for s in chain["subtasks"]:
        if "S2" in (s.get("depends_on") or []) and s["id"] != "S2b":
            s["depends_on"] = ["S2b"]
    check("declutter: two halves of one PR in a straight chain are a merge candidate",
          ("SUB018", "subtask S2b") in findings(chain))

    fanned = copy.deepcopy(chain)
    fanned["subtasks"][4]["depends_on"] = ["S2"]        # the parent now feeds two
    check("declutter: a parent that feeds two children is a fan-out, not clutter",
          ("SUB018", "subtask S2b") not in findings(fanned))

    big = copy.deepcopy(chain)
    big["subtasks"][3]["estimate_days"] = 0.75          # merging would breach the cap
    check("declutter: it never proposes a merge that would breach a ceiling",
          ("SUB018", "subtask S2b") not in findings(big))

    # A spike holds a deferred decision; a rollout happens days later; and whatever
    # decomposition.mandatory asks for was asked for on purpose.
    for kind in ("spike", "rollout", "test", "docs"):
        exempt = copy.deepcopy(chain)
        exempt["subtasks"][3]["kind"] = kind
        check("declutter: %s stays separate, it is not accidental clutter" % kind,
              ("SUB018", "subtask S2b") not in findings(exempt))


def suite_research():
    """A research item is not a feature with unknowns. Asked the feature questions it
    answers them plausibly, and the output is a confident plan for work nobody has
    established is worth doing."""
    print("\n-- 10. research items --")
    import intake as I
    from validate import check_research, check_intake, Report, INTAKE_KINDS
    cfg = load_config(CONFIG)
    with open(GOLDEN, encoding="utf-8") as fh:
        golden = json.load(fh)

    def findings(bundle, fn=check_research):
        rep = Report()
        if fn is check_research:
            fn(bundle, cfg, bundle.get("subtasks") or [], rep)
        else:
            fn(bundle, cfg, rep)
        return {(i["code"], i["where"]) for i in rep.items}

    # The questionnaire. Every kind must have one, or the item silently gets the
    # feature questions - which is worse than crashing, because it looks like it worked.
    for kind in INTAKE_KINDS:
        check("research: kind %r has its own required dimensions" % kind,
              bool(I.DEFAULT_REQUIRED.get(kind)))
    check("research: a research item is not asked for an actor and an outcome",
          not ({"actor", "outcome", "trigger"} & set(I.DEFAULT_REQUIRED["spike"])))

    for text, want in (("We need to uitzoeken of een async lookup p95 haalt.", "spike"),
                       ("Spike: can we move the VAT lookup off the checkout path?", "spike"),
                       ("Investigate whether caching helps; it crashes with a 500 error "
                        "and fails on every retry.", "spike"),
                       ("The checkout returns a 500 error and the retry fails too.", "bug"),
                       ("As a customer I want to see my invoices so that I can file them.",
                        "feature")):
        check("research: %r detected as %s" % (text[:38], want), I.detect_kind(text) == want)

    # An unknown kind used to raise KeyError out of check_intake and take the whole
    # validator with it, so a research bundle could not even be reported on.
    unknown = copy.deepcopy(golden)
    unknown["story"]["intake"]["kind"] = "chore"
    check("research: an unknown kind is a finding, not a crash",
          ("INT012", "story.intake.kind") in findings(unknown, check_intake))

    spike_kind = copy.deepcopy(golden)
    spike_kind["story"]["intake"]["kind"] = "spike"
    check("research: kind=spike does not raise", isinstance(findings(spike_kind, check_intake), set))
    check("research: a delivery profile on a research item is reported",
          ("INT011", "profile") in findings(spike_kind, check_intake))
    check("research: a research item that plans the build is reported",
          ("SPK004", "subtasks") in findings(spike_kind))

    # A well-formed research item: one spike, inside the timebox, nothing else.
    ok = copy.deepcopy(golden)
    ok["profile"] = "research"
    ok["story"]["intake"]["kind"] = "spike"
    ok["subtasks"] = [dict(golden["subtasks"][0], covers=["AC1"], estimate_days=0.5)]
    check("research: one spike inside its timebox is left alone", not findings(ok))

    no_spike = copy.deepcopy(ok)
    no_spike["subtasks"][0]["kind"] = "docs"
    check("research: a research item with no spike is a story in disguise",
          ("SPK001", "subtasks") in findings(no_spike))

    over = copy.deepcopy(ok)
    over["subtasks"][0]["estimate_days"] = 2.0
    check("research: a spike over its timebox is reported",
          ("SPK002", "subtask S0") in findings(over))

    # SPK003 runs the other way: on a delivery story, a spike nothing waits for.
    orphan = copy.deepcopy(golden)
    for d in orphan["decisions"]:
        d.pop("spike", None)
    check("research: a spike no decision defers to is reading, not a ticket",
          ("SPK003", "subtask S0") in findings(orphan))
    check("research: a spike a decision does defer to is left alone",
          ("SPK003", "subtask S0") not in findings(golden))

    # Enablers: the customer is the team, and the story form hides it.
    from validate import check_enabler
    check("enabler: not asked for an actor or an outcome",
          not ({"actor", "outcome", "trigger"} & set(I.DEFAULT_REQUIRED["enabling"])))
    for text, want in (("Upgrade Django from 3.2 to 5.0 - 3.2 is end-of-life in April.", "enabling"),
                       ("As a developer I want a CI pipeline so we stop deploying by hand.", "enabling"),
                       ("Zet een build pipeline op; nu deployen we handmatig elke sprint.", "enabling"),
                       ("The sales pipeline report shows stale numbers for the platform team.", "feature"),
                       ("Upgrade the client library to fix the crash; it fails with a 500 error.", "bug")):
        check("enabler: %r detected as %s" % (text[:38], want), I.detect_kind(text) == want)

    def enb(bundle):
        rep = Report()
        check_enabler(bundle, rep)
        return {(i["code"], i["where"]) for i in rep.items}

    en = copy.deepcopy(golden)
    en["story"]["intake"]["kind"] = "enabling"
    en["story"]["intake"]["dimensions"] = [
        {"id": "unlocks", "required": True, "status": "answered",
         "answer": "ABC-210 needs async views", "answered_by": "m.dijkstra 2026-09-02"},
        {"id": "cost_of_delay", "required": True, "status": "answered",
         "answer": "3.2 is EOL in April", "answered_by": "m.dijkstra 2026-09-02"}]
    en["story"]["links"] = []
    check("enabler: unlocks a ticket nothing links - reported",
          ("ENB001", "story.intake.unlocks") in enb(en))
    en["story"]["links"] = [{"type": "relates", "key": "ABC-210"}]
    check("enabler: linked but not as 'blocks' - reported, the order is the point",
          ("ENB001", "story.intake.unlocks") in enb(en))
    en["story"]["links"] = [{"type": "blocks", "key": "ABC-210"}]
    check("enabler: a 'blocks' link satisfies it", not enb(en))
    check("enabler: a feature story is left alone by the enabler gate", not enb(golden))


def suite_story_shapes():
    """Story shapes whose defining question no other gate asks: one that moves a
    number, one that promises to preserve behaviour, and one that cannot be undone."""
    print("\n-- 11. story shapes --")
    from validate import (check_baseline, check_irreversible, check_subtasks,
                          Report, SUBTASK_KINDS)
    cfg = load_config(CONFIG)
    with open(GOLDEN, encoding="utf-8") as fh:
        golden = json.load(fh)

    def findings(bundle, fn):
        rep = Report()
        if fn is check_baseline:
            fn(bundle, cfg, rep)
        elif fn is check_subtasks:
            fn(bundle, cfg, rep)
        else:
            fn(bundle, cfg, bundle.get("subtasks") or [], rep)
        return {(i["code"], i["where"]) for i in rep.items}

    # A kind is a switch. An unrecognised one used to match no DoD rule, no mandatory
    # rule and no exemption - so a typo turned every gate off for that subtask.
    check("shapes: the golden bundle uses only known kinds",
          all(s["kind"] in SUBTASK_KINDS for s in golden["subtasks"]))
    typo = copy.deepcopy(golden)
    typo["subtasks"][1]["kind"] = "faeture"
    check("shapes: a typo'd subtask kind is reported, not silently exempted",
          ("SUB019", "subtask S1") in findings(typo, check_subtasks))
    housed = copy.deepcopy(cfg)
    housed.setdefault("decomposition", {})["extra_subtask_kinds"] = ["faeture"]
    rep = Report()
    check_subtasks(typo, housed, rep)
    check("shapes: a house kind declared in config is accepted",
          ("SUB019", "subtask S1") not in {(i["code"], i["where"]) for i in rep.items})

    # Moving a number needs a number to move from.
    check("shapes: the golden bundle needs no baseline", not findings(golden, check_baseline))
    target = copy.deepcopy(golden)
    target["story"]["non_functional"]["performance"] = "p95 under 200ms"
    check("shapes: a target relative to today with no baseline is reported",
          ("BAS001", "story.non_functional.performance") in findings(target, check_baseline))
    design = copy.deepcopy(golden)
    design["story"]["non_functional"]["performance"] = "adds one indexed lookup, 4ms"
    check("shapes: a bare number is a design statement, not a target",
          ("BAS001", "story.non_functional.performance") not in findings(design, check_baseline))
    fixed = copy.deepcopy(target)
    fixed["story"]["baseline"] = [{"metric": "performance", "current": "p95 340ms",
                                   "source": "grafana checkout-p95, 7d to 2026-08-30"}]
    check("shapes: a baseline satisfies it", not findings(fixed, check_baseline))
    hollow = copy.deepcopy(target)
    hollow["story"]["baseline"] = [{"metric": "performance", "current": "", "source": "grafana"}]
    check("shapes: an empty baseline value is worse than none, and is reported",
          ("BAS003", "story.baseline[0]") in findings(hollow, check_baseline))

    # "Unchanged" is only demonstrable against a capture made before the change.
    keep = copy.deepcopy(golden)
    keep["story"]["acceptance_criteria"][0]["rule"] = \
        "Every existing tax calculation returns exactly what it returned before."
    check("shapes: a preservation claim with no capture cannot be met or failed",
          ("BAS002", "AC AC1") in findings(keep, check_baseline))
    keep2 = copy.deepcopy(keep)
    keep2["story"]["baseline"] = [{"metric": "tax totals", "current": "2025 invoice corpus, 41k orders",
                                   "source": "tests/fixtures/corpus-2025.jsonl @9f2c1ab"}]
    check("shapes: a recorded corpus satisfies it", not findings(keep2, check_baseline))

    # A migration is not a revert away.
    check("shapes: no migration subtask means no irreversibility findings",
          not findings(golden, check_irreversible))
    mig = copy.deepcopy(golden)
    s = mig["subtasks"][1]
    s["kind"] = "migration"
    s["agent_brief"] = dict(s["agent_brief"], rollback={"flag": "billing.reverse_charge", "note": ""})
    f = findings(mig, check_irreversible)
    check("shapes: a migration with no rollback note is reported", ("IRR001", "subtask S1") in f)
    check("shapes: a migration that verifies nothing is reported", ("IRR002", "subtask S1") in f)
    check("shapes: a migration with no dry run is reported", ("IRR003", "subtask S1") in f)

    safe = copy.deepcopy(mig)
    b2 = safe["subtasks"][1]["agent_brief"]
    b2["rollback"] = {"flag": "", "irreversible": True,
                      "note": "overwrites tax_reason in place; restorable only from the nightly "
                              "snapshot, which is 24h behind"}
    b2["done_when"] = list(b2["done_when"]) + [
        {"type": "command", "cmd": "psql -c 'select count(*) from orders where tax_reason is null'",
         "expect": "0"}]
    b2["preflight"] = list(b2["preflight"]) + [
        {"type": "command", "cmd": "python manage.py backfill_tax_reason --dry-run", "expect": "exit 0"}]
    check("shapes: an irreversible migration that says so, verifies and rehearses passes",
          not findings(safe, check_irreversible))
    silent = copy.deepcopy(safe)
    silent["subtasks"][1]["agent_brief"]["rollback"] = {"flag": "", "irreversible": True, "note": ""}
    check("shapes: 'irreversible' with no explanation is still reported",
          ("IRR001", "subtask S1") in findings(silent, check_irreversible))

    # Re-assessing a refined bundle used to reset it: answered dimensions back to
    # missing, the domain dropped, the verdict flipped, and the same three questions
    # appended again for people who had already answered them.
    import intake as I
    import tempfile
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(golden, tmp); tmp.close()
    rep = I.assess(golden["story"]["source_text"], cfg)
    I.write_into_bundle(tmp.name, rep)
    with open(tmp.name, encoding="utf-8") as fh:
        again = json.load(fh)
    os.unlink(tmp.name)
    before = {d["id"]: d for d in golden["story"]["intake"]["dimensions"]}
    after = {d["id"]: d for d in again["story"]["intake"]["dimensions"]}
    check("re-assess: an answered dimension stays answered, with its provenance",
          after["trigger"]["status"] == "answered"
          and after["trigger"].get("answered_by") == before["trigger"].get("answered_by"))
    check("re-assess: an assumed dimension stays assumed",
          all(after[k]["status"] == "assumed" for k in ("success_signal", "scope")))
    check("re-assess: the domain classification survives",
          again["story"]["intake"].get("domain") == golden["story"]["intake"].get("domain"))
    check("re-assess: the verdict does not flip to insufficient on settled dimensions",
          again["story"]["intake"]["verdict"] == "sufficient")
    check("re-assess: no duplicate questions for dimensions already asked about",
          len(again["open_questions"]) == len(golden["open_questions"]))


def suite_summary():
    """The artefact people actually talk from. It has to work before the bundle is
    finished, and it has to say the unwelcome part."""
    print("\n-- 12. discussion summary --")
    import re
    import summary as S
    cfg = load_config(CONFIG)
    with open(GOLDEN, encoding="utf-8") as fh:
        golden = json.load(fh)

    text = "\n".join(S.one_story(copy.deepcopy(golden), cfg))
    for heading in ("**Why.**", "**Size.**", "**In order.**", "**It hinges on.**",
                    "**Ask this round.**", "**Ready.**"):
        check("summary: says %s" % heading.strip("*."), heading in text)
    check("summary: fits a screen", len(text.splitlines()) < 45, len(text.splitlines()))
    check("summary: separates the work from the elapsed time",
          "2.8 day(s) of work" in text and "2.2 day(s) end to end" in text, text[:400])
    check("summary: names the critical path, not just a number", "S0 → S1 → S2" in text)
    block = text.split("- **Marieke (Finance)**")[1].split("\n- **")[0]
    check("summary: groups the questions by the person who owes the answer",
          text.count("- **Marieke (Finance)**") == 1
          and len(re.findall(r"\n  \d+\. ", block)) == 3, block)
    check("summary: the round is numbered and each question carries its recommendation",
          "  1. " in text and text.count("_recommend:_") == 5, text)

    # The frontier: what cannot be answered yet is listed, not asked.
    laterb = copy.deepcopy(golden)
    laterb["open_questions"][1]["blocked_by"] = ["Q1"]
    laterb["open_questions"][1].pop("asked", None)
    text2 = "\n".join(S.one_story(laterb, cfg))
    check("summary: a question waiting on an earlier answer is not in the round",
          "Waits on an earlier answer" in text2
          and laterb["open_questions"][1]["text"] not in text2.split("Waits on an earlier")[0],
          text2)
    answered = copy.deepcopy(golden)
    for q in answered["open_questions"]:
        q["answer"] = "yes"
    check("summary: an empty frontier is said out loud",
          "frontier is empty" in "\n".join(S.one_story(answered, cfg)))

    unfinished = copy.deepcopy(golden)
    unfinished["story"]["acceptance_criteria"] = []
    unfinished["open_questions"].append({"id": "Q9", "text": "which provider?", "owner": "",
                                         "blocking": True})
    text = "\n".join(S.one_story(unfinished, cfg))
    check("summary: still works on an unfinished bundle", "**Size.**" in text)
    check("summary: leads with what blocks it, not the first error found",
          "**Not ready**" in text and "READY001" in text, text[-300:])
    check("summary: says which questions have not been put to anyone yet",
          "not asked yet" in text)

    days, path = S.critical_path(golden["subtasks"])
    check("summary: the critical path is the longest chain, not the sum",
          abs(days - 2.25) < 0.01 and path[0] == "S0", (days, path))
    check("summary: an empty bundle has no critical path", S.critical_path([]) == (0.0, []))


def suite_roundtrip():
    """A ticket has to be readable back into a bundle, because in a real team the
    stored bundle is on somebody else's laptop. And progress has to be recordable,
    because a plan that never learns what shipped keeps deleting work that exists."""
    print("\n-- 13. round trip and progress --")
    import ingest as I
    import progress as P

    with open(GOLDEN, encoding="utf-8") as fh:
        golden = json.load(fh)
    tmp = tempfile.mkdtemp(prefix="refinery-rt-")
    try:
        emit = os.path.join(HERE, "emit.py")
        code, out = run([emit, GOLDEN, "--config", CONFIG, "--adapter", "markdown",
                         "--out", "out"], tmp)
        text = open(os.path.join(tmp, "out", "preview.md"), encoding="utf-8").read()
        back, edited = I.ingest(text)

        check("ingest: the criterion codes come back attached to their rules",
              [(c["id"], c["rule"]) for c in back["story"]["acceptance_criteria"]]
              == [(c["id"], c["rule"]) for c in golden["story"]["acceptance_criteria"]])
        check("ingest: the subtask table round-trips, dependencies and estimates included",
              [(s["id"], s["repo"], tuple(s["depends_on"]), s["estimate_days"])
               for s in back["subtasks"]]
              == [(s["id"], s["repo"], tuple(s.get("depends_on") or []), s["estimate_days"])
                  for s in golden["subtasks"]])
        check("ingest: every agent brief is recovered from its markers",
              sum(1 for s in back["subtasks"] if s.get("agent_brief")) == 7)
        check("ingest: the decision table survives the trip",
              len(back["story"]["decision_table"]["rules"]) == 6)
        check("ingest: questions keep their owner and whether they block",
              len(back["open_questions"]) == 5
              and back["open_questions"][0]["owner"] == "Marieke (Finance)")
        check("ingest: nothing was edited, so nothing is reported", not edited)
        check("ingest: it does not invent the evidence it cannot see",
              not back.get("evidence") and "intake" not in back["story"])
        codes = {i["code"] for i in validate(back, load_config(CONFIG)).items}
        check("ingest: an imported bundle is honestly not ready until re-derived",
              "INT001" in codes and "EVI001" in codes, sorted(codes)[:6])

        tampered = text.replace('"Do not change anything in the api repo."',
                                '"Feel free to touch the api repo too."', 1)
        _, edited = I.ingest(tampered)
        check("ingest: a brief edited in the tracker is caught by its own hash",
              len(edited) == 1 and edited[0][0] == "web", edited)

        moved = copy.deepcopy(golden)
        P.apply_states(moved, {"S0": "done", "S1": "done", "S2": "started"}, "standup")
        _, counted, done_days, total = P.summarise(moved)
        check("progress: what shipped is recorded with its source",
              counted["done"] == ["S0", "S1"] and counted["started"] == ["S2"]
              and (moved["story"]["progress"]["source"] == "standup"))
        check("progress: days done are counted against the total",
              abs(done_days - 1.0) < 0.01 and abs(total - 2.75) < 0.01, (done_days, total))
        check("progress: an unknown subtask id is refused, not recorded",
              P.apply_states(moved, {"S99": "done"}, "x") == ["S99"]
              and "S99" not in moved["story"]["progress"]["subtasks"])

        # Dropping a subtask that already shipped must not read like a plan change.
        prior = os.path.join(tmp, "prior.json")
        nxt = os.path.join(tmp, "next.json")
        with open(prior, "w", encoding="utf-8") as fh:
            json.dump(moved, fh)
        shrunk = copy.deepcopy(moved)
        shrunk["subtasks"] = [s for s in shrunk["subtasks"] if s["id"] not in ("S1", "S5")]
        shrunk["coverage"] = {"AC1": ["S2"], "AC2": ["S2"], "AC3": ["S2", "S3"], "AC4": ["S4"]}
        with open(nxt, "w", encoding="utf-8") as fh:
            json.dump(shrunk, fh)
        code, out = run([emit, nxt, "--config", CONFIG, "--previous", prior,
                         "--out", "out_upd3", "--allow-not-ready"], tmp)
        plan = json.load(open(os.path.join(tmp, "out_upd3", "push-plan.json")))
        check("progress: an orphan that already shipped is separated from one that did not",
              plan["orphans_already_underway"] == ["S1"] and set(plan["orphans"]) == {"S1", "S5"},
              plan["orphans_already_underway"])
        check("progress: and it is said out loud", "deleting work that exists" in out, out[-300:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def suite_batch():
    """Several related stories in one run. These are the findings that do not exist
    for one bundle: they only appear when the bundles are read side by side."""
    print("\n-- 14. batch --")
    import batch as B

    with open(GOLDEN, encoding="utf-8") as fh:
        first = json.load(fh)
    second = copy.deepcopy(first)
    second["story"]["key"] = "ABC-131"
    second["evidence"]["pending"] = [{"claim": "tax.reason on the order response",
                                      "provided_by": {"ticket": "ABC-123", "subtask": "S2"}}]
    second["story"]["links"] = []
    second["evidence"]["glossary"][0]["means"] = "A discount for business customers"
    first["evidence"]["ruled_out"].append({
        "claim": "There is no rate table for non-EU destinations",
        "looked_in": ["api/src/billing/rates/**"],
        "conclusion": "Adding one is new work, not a lookup."})
    pair = [("a.json", first), ("b.json", second)]

    tmp = tempfile.mkdtemp(prefix="refinery-batch-")
    try:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = B.cmd_check(pair)
        text = out.getvalue()
        check("batch: a contradiction between bundles is an error", "BAT002" in text and code == 1)
        check("batch: a dependency inside the batch with no link is an error", "BAT004" in text)
        check("batch: two stories writing one file is reported once, not once per file",
              text.count("BAT001") == 1 and "18 file(s)" in text, text)
        check("batch: one person asked the same thing twice is a batching problem",
              "BAT003" in text)
        check("batch: near-identical change surfaces are questioned", "BAT006" in text)

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            order = B.cmd_order(pair)
        text = out.getvalue()
        check("batch: the story others depend on is refined first",
              text.index("ABC-123") < text.index("ABC-131") and order == 0, text)
        check("batch: a fork open in several bundles is named once",
              text.count("fork(s) are open") == 1, text)

        # share must not spread a definition the batch already disagrees about.
        paths = []
        for name, bundle in pair:
            path = os.path.join(tmp, name)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(bundle, fh)
            paths.append(path)
        loaded = B.load(paths)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = B.cmd_share(loaded, write=True)
        check("batch: a conflicting definition is reported, not shared",
              "CONFLICT" in out.getvalue() and code == 1)
        merged = json.load(open(paths[1], encoding="utf-8"))
        means = [g["means"] for g in merged["evidence"]["glossary"]
                 if g["term"] == "reverse charge"]
        check("batch: the conflicting term keeps one meaning per bundle", len(means) == 1, means)
        carried = [e for e in merged["evidence"]["ruled_out"] if e.get("inherited_from")]
        check("batch: what is shared says which story it came from",
              carried and "same refinement run" in carried[0]["inherited_from"])

        clean = copy.deepcopy(second)
        clean["evidence"]["glossary"][0]["means"] = first["evidence"]["glossary"][0]["means"]
        clean["story"]["links"] = [{"type": "blocked_by", "key": "ABC-123", "why": "the tax "
                                    "object it reads does not exist yet"}]
        clean["subtasks"] = []
        clean["open_questions"] = []
        clean["evidence"]["change_surface"] = []
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = B.cmd_check([("a.json", first), ("b.json", clean)])
        check("batch: a linked, non-overlapping, agreeing pair is clean",
              code == 0 and "CLEAN" in out.getvalue(), out.getvalue())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def suite_review():
    """The critic packets are the only mechanical guarantee of blindness in the
    skill. If the reasoning leaks into one, the panel is grading the reasoning."""
    print("\n-- 15. adversarial review --")
    from review import (CRITICS, DEFAULT_PANEL, cmd_check, content_digest,
                        render_brief, resolve_locator)
    with open(GOLDEN, encoding="utf-8") as fh:
        golden = json.load(fh)

    digest = content_digest(golden)
    reordered = json.loads(json.dumps(golden, sort_keys=True))
    check("digest: stable under key order and whitespace",
          content_digest(reordered) == digest)
    check("digest: review block does not hash itself",
          content_digest(dict(golden, review={"method": "rubber-duck"})) == digest)
    check("digest: a re-render does not invalidate a review",
          content_digest(dict(golden, generated_at="2999-01-01T00:00:00Z")) == digest)
    changed = copy.deepcopy(golden)
    changed["subtasks"][1]["estimate_days"] = 0.75
    check("digest: content change moves it", content_digest(changed) != digest)
    check("digest: the shipped example is stamped with its own content",
          golden["review"]["bundle_digest"] == digest, golden["review"]["bundle_digest"])

    for locator, expect in (("story.acceptance_criteria[1].id", "AC2"),
                            ("subtasks[6].depends_on[0]", "S4"),
                            ("$.story.key", "ABC-123")):
        ok, value = resolve_locator(golden, locator)
        check("locator resolves: %s" % locator, ok and value == expect, value)
    for locator in ("subtasks[99]", "story.nope", "subtasks.0.id", "", "story..key"):
        ok, _ = resolve_locator(golden, locator)
        check("locator rejected: %r" % locator, not ok)

    # Blindness: the packet must carry the artefact and nothing that explains it.
    rationale = golden["decisions"][0]["rationale"]
    for cid in DEFAULT_PANEL:
        packet = render_brief(golden, cid)
        check("packet %s: withholds decision rationale" % cid, rationale not in packet)
        check("packet %s: withholds the self-score" % cid,
              "rubric" not in packet.lower() and '"decisions"' not in packet)
        check("packet %s: carries the finding contract" % cid,
              "locator" in packet and "failure" in packet)
        check("packet %s: states what was withheld" % cid, "Withheld deliberately" in packet)
    # Only the artefact section; the instructions above it legitimately name fields.
    artefact = lambda cid: render_brief(golden, cid).split("## The artefact", 1)[1]  # noqa: E731
    impl = artefact("implementer")
    check("packet implementer: carries the briefs it must execute",
          "read_first" in impl and "done_when" in impl)
    check("packet implementer: judges the brief alone, not the criteria behind it",
          "acceptance_criteria" not in impl)
    seq = artefact("sequencer")
    check("packet sequencer: carries the graph, not the prose",
          "depends_on" in seq and "summary_human" not in seq)
    arch = artefact("archaeologist")
    check("packet archaeologist: carries every citation", "change_surface" in arch
          and "conventions" in arch)
    stake = artefact("stakeholder")
    check("packet stakeholder: carries the original ask",
          golden["story"]["source_text"][:40] in stake)
    check("packet stakeholder: not shown the technical plan",
          "technical_notes_human" not in stake)
    check("every configured panel member is a known critic",
          all(c in CRITICS for c in
              (load_config(CONFIG).get("review") or {}).get("panel") or []),
          (load_config(CONFIG).get("review") or {}).get("panel"))

    check("check: clean bundle exits 0", cmd_check(copy.deepcopy(golden)) == 0)
    blocked = copy.deepcopy(golden)
    blocked["review"]["findings"][0]["status"] = "open"
    check("check: an open blocking finding exits 1", cmd_check(blocked) == 1)
    unreviewed = copy.deepcopy(golden)
    unreviewed.pop("review")
    check("check: no review at all exits 1", cmd_check(unreviewed) == 1)

    # The gate can be switched off, but only deliberately.
    cfg_off = copy.deepcopy(load_config(CONFIG))
    cfg_off.setdefault("gates", {})["adversarial_review"] = "off"
    rep = validate(unreviewed, cfg_off)
    check("gate off: an unreviewed bundle is not blocked",
          "REV001" not in {i["code"] for i in rep.items})


def main():
    with open(GOLDEN, encoding="utf-8") as fh:
        golden = json.load(fh)
    cfg = load_config(CONFIG)
    suite_gates(golden, cfg)
    suite_config(cfg, golden)
    suite_markup()
    suite_pipeline()
    suite_intake()
    suite_tailoring()
    suite_triage()
    suite_criteria()
    suite_declutter()
    suite_research()
    suite_story_shapes()
    suite_summary()
    suite_roundtrip()
    suite_batch()
    suite_review()
    suite_docs()
    print("\n%s  %d failure(s)" % ("PASS" if not FAILURES else "FAIL", len(FAILURES)))
    if FAILURES:
        print("failed: %s" % ", ".join(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
