"""Tests for software-studio-builder's scripts.

    python3 -m unittest discover -s software-studio-builder/tests

The template-check tests are MUTATION tests: each breaks one property the check guards in a
freshly generated template and asserts the check now FAILs. A gate nobody has watched fail
is not a gate.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
SCRIPTS = os.path.join(SKILL, "scripts")
FIXTURE = os.path.join(HERE, "fixtures", "hr-payroll", ".ssb")
PY = sys.executable


def rd(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def wr(p, text, mode="w"):
    with open(p, mode, encoding="utf-8") as fh:
        fh.write(text)


def jl(p):
    return json.loads(rd(p))


def jd(obj, p):
    wr(p, json.dumps(obj, indent=2))


def run(*args, cwd=None):
    return subprocess.run([PY, *args], capture_output=True, text=True, cwd=cwd)


def script(name, *args):
    return run(os.path.join(SCRIPTS, name), *args)


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d)
        self.L = os.path.join(self.d, "research")
        self.assertEqual(script("ledger.py", "init", self.L, "--query", "q").returncode, 0)

    def add_source(self, sid="iso-29148", tier="standard-body", url="https://www.iso.org/standard/72089.html"):
        return script("ledger.py", "add-source", self.L, "--id", sid, "--title", "t", "--publisher", "p",
                      "--tier", tier, "--type", "standard", "--url", url)

    def test_empty_ledger_is_not_assessed(self):
        r = script("ledger.py", "check", self.L)
        self.assertIn("VERDICT: NOT ASSESSED", r.stdout)
        self.assertEqual(r.returncode, 3)

    def test_supported_claim_passes(self):
        self.add_source()
        e = script("ledger.py", "add-evidence", self.L, "--source", "iso-29148", "--quote", "words",
                   "--locator", "5.2", "--supports", "x").stdout.strip()
        self.assertEqual(e, "E001")
        c = script("ledger.py", "add-claim", self.L, "--claim", "c", "--kind", "fact", "--evidence", e)
        self.assertEqual(c.stdout.strip(), "C001")
        self.assertIn("VERDICT: PASS", script("ledger.py", "check", self.L).stdout)

    def test_supported_on_unverified_source_fails(self):
        self.add_source("blog", tier="unverified", url="")
        e = script("ledger.py", "add-evidence", self.L, "--source", "blog", "--quote", "w", "--locator", "l",
                   "--supports", "x").stdout.strip()
        script("ledger.py", "add-claim", self.L, "--claim", "c", "--kind", "fact", "--evidence", e)
        r = script("ledger.py", "check", self.L)
        self.assertIn("VERDICT: FAIL", r.stdout)
        self.assertIn("no evidence above tier", r.stdout)

    def test_synthesis_needs_two_sources(self):
        self.add_source()
        e = script("ledger.py", "add-evidence", self.L, "--source", "iso-29148", "--quote", "w", "--locator", "l",
                   "--supports", "x").stdout.strip()
        script("ledger.py", "add-claim", self.L, "--claim", "c", "--kind", "synthesis", "--evidence", e)
        self.assertIn("needs evidence from >=2 sources", script("ledger.py", "check", self.L).stdout)

    def test_supersedes_keeps_old_row_and_forbids_citing_it(self):
        self.add_source()
        e1 = script("ledger.py", "add-evidence", self.L, "--source", "iso-29148", "--quote", "w", "--locator",
                    "wrong 9.9", "--supports", "x").stdout.strip()
        e2 = script("ledger.py", "add-evidence", self.L, "--source", "iso-29148", "--quote", "w", "--locator",
                    "5.2", "--supports", "x", "--supersedes", e1).stdout.strip()
        self.assertEqual((e1, e2), ("E001", "E002"))
        r = script("ledger.py", "add-claim", self.L, "--claim", "c", "--kind", "fact", "--evidence", e1)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("superseded", r.stderr + r.stdout)
        script("ledger.py", "add-claim", self.L, "--claim", "c", "--kind", "fact", "--evidence", e2)
        self.assertIn("VERDICT: PASS", script("ledger.py", "check", self.L).stdout)

    def test_claim_supersedes_retires_the_old_claim(self):
        self.add_source()
        e = script("ledger.py", "add-evidence", self.L, "--source", "iso-29148", "--quote", "w", "--locator",
                   "5.2", "--supports", "x").stdout.strip()
        bad = script("ledger.py", "add-claim", self.L, "--claim", "c", "--kind", "synthesis", "--evidence", e).stdout.strip()
        self.assertIn("VERDICT: FAIL", script("ledger.py", "check", self.L).stdout)  # synthesis from one source
        good = script("ledger.py", "add-claim", self.L, "--claim", "c", "--kind", "fact", "--evidence", e,
                      "--supersedes", bad).stdout.strip()
        out = script("ledger.py", "check", self.L).stdout
        self.assertIn("VERDICT: PASS", out, out)
        self.assertIn(f"superseded (kept, not citable): {bad}", out)
        r = script("ledger.py", "add-claim", self.L, "--claim", "x", "--kind", "fact", "--evidence", bad,
                   "--status", "supported-inference")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotEqual(script("ledger.py", "add-claim", self.L, "--claim", "y", "--kind", "fact", "--evidence",
                                   e, "--supersedes", bad).returncode, 0)  # already superseded
        self.assertEqual(good, "C002")

    def test_entry_point_rejects_bad_rows(self):
        self.assertNotEqual(self.add_source(tier="blog").returncode, 0)
        self.assertNotEqual(self.add_source(url="").returncode, 0)
        r = script("ledger.py", "add-evidence", self.L, "--source", "nope", "--quote", "w", "--locator", "l",
                   "--supports", "x")
        self.assertNotEqual(r.returncode, 0)
        r = script("ledger.py", "add-claim", self.L, "--claim", "c", "--kind", "fact", "--evidence", "E999")
        self.assertNotEqual(r.returncode, 0)
        r = script("ledger.py", "not-sourceable", self.L, "--claim", "c", "--reason", "")
        self.assertNotEqual(r.returncode, 0)

    def test_not_sourceable_is_a_concern_free_record(self):
        script("ledger.py", "not-sourceable", self.L, "--claim", "c", "--reason", "searched x and y")
        self.assertIn("not-sourceable=1", script("ledger.py", "check", self.L).stdout)


class ProposalTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d)
        self.run_dir = os.path.join(self.d, ".ssb")
        shutil.copytree(FIXTURE, self.run_dir)

    def bp(self):
        return jl(os.path.join(self.run_dir, "proposal.json"))

    def save(self, bp):
        jd(bp, os.path.join(self.run_dir, "proposal.json"))

    def check(self):
        return script("proposal.py", "check", self.run_dir)

    def test_fixture_has_no_failures(self):
        r = self.check()
        self.assertIn("VERDICT: CONCERNS", r.stdout, r.stdout)  # fixture sources are unverified on purpose
        self.assertNotIn("FAIL:", r.stdout)

    def test_missing_ledger_is_not_assessed(self):
        shutil.rmtree(os.path.join(self.run_dir, "research"))
        self.assertIn("VERDICT: NOT ASSESSED", self.check().stdout)

    def mutate(self, fn, expect):
        bp = self.bp()
        fn(bp)
        self.save(bp)
        r = self.check()
        self.assertIn("VERDICT: FAIL", r.stdout, r.stdout)
        self.assertRegex(r.stdout, expect)

    def role(self, bp, rid):
        return next(r for r in bp["roles"] if r["id"] == rid)

    def test_specialist_reporting_to_specialist_fails(self):
        self.mutate(lambda bp: self.role(bp, "qa-tester").update(reports_to="backend-engineer"), r"is not above")

    def test_director_must_report_to_user(self):
        self.mutate(lambda bp: self.role(bp, "product-director").update(reports_to="technical-director"),
                    r"a director reports to `user`")

    def test_unknown_escalation_target_fails(self):
        self.mutate(lambda bp: self.role(bp, "qa-tester")["escalation"].append({"to": "ghost", "when": "x"}),
                    r"escalation target .* is not a role")

    def test_escalation_without_reason_fails(self):
        self.mutate(lambda bp: self.role(bp, "qa-tester")["escalation"].append({"to": "qa-lead"}), r"gives no reason")

    def test_stored_delegates_disagreeing_fails(self):
        self.mutate(lambda bp: self.role(bp, "qa-lead").update(delegates_to=["backend-engineer"]),
                    r"disagrees with the derived")

    def test_empty_claims_fail(self):
        self.mutate(lambda bp: self.role(bp, "qa-tester").update(claims=[]), r"`claims` is empty")

    def test_superseded_claim_in_proposal_fails(self):
        res = os.path.join(self.run_dir, "research")
        script("ledger.py", "add-claim", res, "--claim", "replacement", "--kind", "fact", "--evidence", "E001",
               "--status", "unverified", "--supersedes", "C001")
        r = self.check()
        self.assertIn("VERDICT: FAIL", r.stdout)
        self.assertIn("claim C001 is superseded by C007", r.stdout)

    def test_unknown_claim_id_fails(self):
        self.mutate(lambda bp: self.role(bp, "qa-tester").update(claims=["C999"]), r"not in the ledger")

    def test_gate_owner_must_exist(self):
        self.mutate(lambda bp: bp["gates"][0].update(owner="ghost"), r"owner 'ghost' is not a role")

    def test_catalog_command_must_be_a_skill(self):
        self.mutate(lambda bp: bp["phases"][1]["steps"][0].update(command="/nope"), r"is not a skill")

    def test_cycle_is_found(self):
        def f(bp):
            self.role(bp, "business-analysis-lead").update(tier="specialist", reports_to="business-analyst")
        self.mutate(f, r"reporting cycle|is not above")

    def test_director_without_user_escalation_fails(self):
        self.mutate(lambda bp: self.role(bp, "product-director").update(escalation=[]),
                    r"directors escalate to the user")

    def test_only_directors_escalate_to_user(self):
        self.mutate(lambda bp: self.role(bp, "qa-tester")["escalation"].append({"to": "user", "when": "x"}),
                    r"only a director escalates to `user`")

    def test_cold_context_phrase_in_agent_text_fails(self):
        self.mutate(lambda bp: self.role(bp, "qa-tester")["responsibilities"].append("Run the checks as discussed"),
                    r"says 'as discussed'")

    def test_placeholder_in_agent_text_fails(self):
        self.mutate(lambda bp: bp["gates"][0].update(prompt="{{PROMPT}}"), r"contains placeholder")

    def test_render_writes_reporting_lines(self):
        r = script("proposal.py", "render", self.run_dir)
        self.assertEqual(r.returncode, 0, r.stdout)
        md = rd(os.path.join(self.run_dir, "proposal.md"))
        self.assertIn("- **Reports to:** `business-analysis-lead`", md)
        self.assertIn("- **Delegates to:** `business-analyst`, `payroll-rules-specialist`", md)
        self.assertIn("- **Gates owned:** `QL-UAT-SIGNOFF`", md)
        # the user approves the real cut: mvp:false items appear as deferred, not "none"
        self.assertIn("role:data-migration-specialist", md.split("## 12. Scope")[1].split("##")[0])


class GenerateTests(unittest.TestCase):
    """Generate the fixture into a temp dir once per test, then mutate and check."""

    def setUp(self):
        self.t = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.t)
        self.run_dir = os.path.join(self.t, ".ssb")
        shutil.copytree(FIXTURE, self.run_dir)

    def approve(self):
        script("state.py", "init", self.run_dir, "--domain", "HR", "--target", self.t)
        r = script("state.py", "approve", self.run_dir, "--by", "user")
        self.assertEqual(r.returncode, 0, r.stdout)

    def generate(self, *extra):
        return script("generate.py", self.t, *extra)

    def check(self):
        return run(os.path.join(self.t, ".claude/scripts/check_template.py"), self.t, "--proposal",
                   os.path.join(self.run_dir, "proposal.json"))

    def test_refuses_without_approval(self):
        r = self.generate("--dry-run")
        self.assertEqual(r.returncode, 2)
        self.assertIn("REFUSED", r.stdout)

    def test_refuses_after_proposal_edit(self):
        self.approve()
        bp = jl(os.path.join(self.run_dir, "proposal.json"))
        bp["open_questions"].append("edited after approval")
        jd(bp, os.path.join(self.run_dir, "proposal.json"))
        r = self.generate("--dry-run")
        self.assertIn("changed after approval", r.stdout)

    def test_only_user_approves(self):
        script("state.py", "init", self.run_dir, "--domain", "HR", "--target", self.t)
        self.assertNotEqual(script("state.py", "approve", self.run_dir, "--by", "claude").returncode, 0)

    def test_mvp_cut_conflict_refused(self):
        bp = jl(os.path.join(self.run_dir, "proposal.json"))
        bp["scope"]["later"].append("role:lead-engineer")  # its reports would be orphaned
        jd(bp, os.path.join(self.run_dir, "proposal.json"))
        self.approve()
        r = self.generate("--dry-run")
        self.assertIn("MVP cut breaks", r.stdout)

    def test_dry_run_writes_nothing(self):
        self.approve()
        r = self.generate("--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("WOULD-WRITE .claude/agents/qa-lead.md", r.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.t, ".claude")))

    def test_generated_template_passes_and_never_overwrites(self):
        self.approve()
        r = self.generate("--layer", "all")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.t, ".claude/agents/data-migration-specialist.md")))
        c = self.check()
        self.assertIn("VERDICT: PASS", c.stdout, c.stdout)
        st = run("-m", "unittest", "discover", "-s", "studio-tests", "-p", "test_*.py", cwd=self.t)
        self.assertEqual(st.returncode, 0, st.stderr)
        p = os.path.join(self.t, ".claude/agents/qa-lead.md")
        wr(p, "\nlocal edit\n", "a")
        r2 = self.generate("--layer", "agents")
        self.assertIn("KEEP .claude/agents/qa-lead.md", r2.stdout)
        self.assertIn("local edit", rd(p))

    def test_regenerate_after_adding_a_role_updates_untouched_files_only(self):
        self.approve()
        self.assertEqual(self.generate("--layer", "all").returncode, 0)
        hand = os.path.join(self.t, ".claude/agents/qa-tester.md")
        wr(hand, "\nhand edit\n", "a")
        bpp = os.path.join(self.run_dir, "proposal.json")
        bp = jl(bpp)
        new = json.loads(json.dumps(next(r for r in bp["roles"] if r["id"] == "business-analyst")))
        new.update(id="data-protection-officer", title="Data Protection Officer", reports_to="compliance-lead",
                   description="Owns the records of processing and the data-subject request procedure.",
                   siblings=[], coordinates_with=[], skills=[], owns_paths=["docs/compliance/privacy/"],
                   escalation=[{"to": "compliance-lead", "when": "an obligation is unclear"}])
        bp["roles"].append(new)
        jd(bp, bpp)
        self.assertIn("REFUSED", self.generate("--dry-run").stdout)  # the edit voids the approval
        self.assertEqual(script("state.py", "approve", self.run_dir, "--by", "user").returncode, 0)
        dry = self.generate("--dry-run").stdout
        self.assertIn("WOULD-UPDATE .claude/docs/agent-roster.md", dry)
        r = self.generate("--layer", "all").stdout
        self.assertIn("WRITE .claude/agents/data-protection-officer.md", r)
        self.assertIn("UPDATE .claude/docs/agent-roster.md", r)
        self.assertIn("UPDATE .claude/agents/compliance-lead.md", r)
        self.assertIn("UPDATE .claude/agent-models.yaml", r)
        self.assertIn("KEEP .claude/agents/qa-tester.md", r)
        self.assertIn("hand edit", rd(hand))
        self.assertIn("`data-protection-officer`", rd(os.path.join(self.t, ".claude/agents/compliance-lead.md")))
        c = run(os.path.join(self.t, ".claude/scripts/check_template.py"), self.t, "--only",
                "C01,C02,C03,C04,C05,C06,C07,C08,C09,C10,C11,C13")
        self.assertNotIn("FAIL", c.stdout, c.stdout)

    # ---- mutation tests on the generated template: each must turn the verdict to FAIL
    def generated(self):
        self.approve()
        self.assertEqual(self.generate("--layer", "all").returncode, 0)

    def edit(self, rel, fn):
        p = os.path.join(self.t, rel)
        t = rd(p)
        t2 = fn(t)
        self.assertNotEqual(t, t2, f"mutation did not change {rel}")
        wr(p, t2)

    def assert_fails(self, cid, pattern):
        c = self.check()
        self.assertIn("VERDICT: FAIL", c.stdout, c.stdout)
        self.assertRegex(c.stdout, rf"CHECK {cid} FAIL")
        self.assertRegex(c.stdout, pattern)

    def test_m_reports_to_wrong_role(self):
        self.generated()
        self.edit(".claude/agents/qa-tester.md", lambda t: t.replace("**Reports to**: `qa-lead`",
                                                                      "**Reports to**: `lead-engineer`"))
        self.assert_fails("C05", r"Reports to `lead-engineer` but roster says `qa-lead`")

    def test_m_missing_delegate(self):
        self.generated()
        self.edit(".claude/agents/qa-lead.md", lambda t: re.sub(r"- `qa-tester` for .*\n", "", t))
        self.assert_fails("C05", r"`qa-tester` reports here but is not under \*\*Delegates to\*\*")

    def test_m_missing_section(self):
        self.generated()
        self.edit(".claude/agents/qa-tester.md", lambda t: t.replace("### What This Agent Must NOT Do", "### Notes"))
        self.assert_fails("C04", r"missing section '### What This Agent Must NOT Do'")

    def test_m_director_escalation_removed(self):
        self.generated()
        self.edit(".claude/agents/product-director.md", lambda t: re.sub(r"- the user when .*\n", "", t))
        self.assert_fails("C04", r"product-director.md: a director must escalate to the user")

    def test_generated_director_escalates_to_the_user(self):
        self.generated()
        t = rd(os.path.join(self.t, ".claude/agents/delivery-director.md"))
        self.assertIn("- the user when a release date, budget or quality bar cannot be met", t)

    def test_m_missing_map_label(self):
        self.generated()
        self.edit(".claude/agents/qa-tester.md", lambda t: t.replace("**Sibling coordination**", "**Siblings**"))
        self.assert_fails("C04", r"Delegation Map lacks \*\*Sibling coordination\*\*")

    def test_m_unknown_escalation(self):
        self.generated()
        self.edit(".claude/agents/qa-tester.md", lambda t: t.replace("- `qa-lead` when", "- `ghost-role` when"))
        self.assert_fails("C05", r"\*\*Escalation targets\*\* names unknown role `ghost-role`")

    def test_m_orphan_agent(self):
        self.generated()
        shutil.copy(os.path.join(self.t, ".claude/agents/qa-tester.md"),
                    os.path.join(self.t, ".claude/agents/qa-tester-2.md"))
        self.edit(".claude/agents/qa-tester-2.md", lambda t: t.replace("name: qa-tester", "name: qa-tester-2"))
        self.assert_fails("C05", r"agent-roster.md has no row for `qa-tester-2`")

    def test_m_model_drift(self):
        self.generated()
        self.edit(".claude/agents/qa-tester.md", lambda t: t.replace("model: sonnet", "model: opus"))
        self.assert_fails("C06", r"`qa-tester`: agent file says opus/medium, table says sonnet/medium")

    def test_m_gate_owner_unlisted(self):
        self.generated()
        self.edit(".claude/agents/qa-lead.md", lambda t: t.replace("Gates owned: `QL-UAT-SIGNOFF`.", "Gates owned: none."))
        self.assert_fails("C09", r"owns gate `QL-UAT-SIGNOFF` but its Gate Verdict Format does not list it")

    def test_m_skill_without_not_assessed(self):
        self.generated()
        self.edit(".claude/skills/uat-report/SKILL.md", lambda t: t.replace("NOT ASSESSED", "UNKNOWN"))
        self.assert_fails("C07", r"verdicts lack a NOT ASSESSED value")

    def test_m_catalog_dangling_command(self):
        self.generated()
        shutil.rmtree(os.path.join(self.t, ".claude/skills/uat-report"))
        self.assert_fails("C10", r"command /uat-report has no skill")

    def test_m_hook_missing(self):
        self.generated()
        os.remove(os.path.join(self.t, ".claude/hooks/validate-read.sh"))
        self.assert_fails("C02", r"validate-read.sh does not exist")

    def test_m_hook_syntax(self):
        self.generated()
        self.edit(".claude/hooks/log-agent.sh", lambda t: t + "\nif then fi\n")
        self.assert_fails("C03", r"log-agent.sh")

    def test_m_deny_list(self):
        self.generated()
        self.edit(".claude/settings.json", lambda t: t.replace('"Bash(git reset --hard*)",', ""))
        self.assert_fails("C02", r"no rule for 'reset --hard'")

    def test_m_invalid_config_value(self):
        self.generated()
        self.edit("project.yaml", lambda t: t.replace("rigor: minimal", "rigor: extreme"))
        self.assert_fails("C11", r"modes.rigor='extreme' is not one of")

    def test_m_proposal_item_missing(self):
        self.generated()
        os.remove(os.path.join(self.t, ".claude/rules/personal-data.md"))
        self.assert_fails("C12", r"rule personal-data: .* neither generated nor listed as deferred")

    def test_m_required_file_missing(self):
        self.generated()
        os.remove(os.path.join(self.t, ".claude/docs/coordination-rules.md"))
        self.assert_fails("C01", r"missing: .claude/docs/coordination-rules.md")

    def test_m_rule_without_paths(self):
        self.generated()
        self.edit(".claude/rules/tests.md", lambda t: re.sub(r"paths:\n(  - .*\n)+", "", t))
        self.assert_fails("C08", r"tests.md: no `paths:` globs")

    # ---- C13: agent-facing Markdown is written for agents
    def test_m_agent_without_spawn_section(self):
        self.generated()
        self.edit(".claude/agents/qa-tester.md", lambda t: t.replace("### When You Are Spawned", "### Intro"))
        self.assert_fails("C13", r"qa-tester.md: no `### When You Are Spawned` section")

    def test_m_skill_without_return_section(self):
        self.generated()
        self.edit(".claude/skills/uat-report/SKILL.md", lambda t: t.replace("## Return", "## The end"))
        self.assert_fails("C13", r"uat-report/SKILL.md: no `## Return` section")

    def test_m_skill_description_without_trigger(self):
        self.generated()
        self.edit(".claude/skills/uat-report/SKILL.md", lambda t: t.replace("Use when", "Handy if", 1))
        self.assert_fails("C13", r"does not say `Use when …`")

    def test_m_overlong_description(self):
        self.generated()
        self.edit(".claude/agents/qa-tester.md",
                  lambda t: t.replace('description: "', 'description: "' + "word " * 90, 1))
        self.assert_fails("C13", r"qa-tester.md: description is \d+ words")

    def test_m_cold_context_phrase(self):
        self.generated()
        self.edit(".claude/rules/tests.md", lambda t: t + "- Use the fixtures as discussed\n")
        self.assert_fails("C13", r"tests.md: 'as discussed' assumes context")

    def test_m_leftover_placeholder(self):
        self.generated()
        self.edit("CLAUDE.md", lambda t: t + "\n{{UNFILLED}}\n")
        self.assert_fails("C13", r"CLAUDE.md: placeholder '\{\{UNFILLED\}\}'")

    def test_m_claude_md_over_budget(self):
        self.generated()
        self.edit("CLAUDE.md", lambda t: t + "- filler line\n" * 160)
        self.assert_fails("C13", r"CLAUDE.md: \d+ lines, over the 150-line budget")

    def test_m_empty_section(self):
        self.generated()
        self.edit(".claude/rules/tests.md", lambda t: t.replace("Owner:", "## Empty\n\n## Next\n\nOwner:", 1))
        self.assert_fails("C13", r"section '## Empty' is empty")

    def test_counts_and_docs_exclude_deferred_items(self):
        self.generated()
        n_agents = len([f for f in os.listdir(os.path.join(self.t, ".claude/agents"))])
        self.assertIn(f"{n_agents} coordinated Claude Code subagents", rd(os.path.join(self.t, "CLAUDE.md")))
        ds = rd(os.path.join(self.t, ".claude/docs/directory-structure.md"))
        self.assertNotIn("`data-migration-specialist` |", ds)
        self.assertIn("Deferred (in the proposal, not generated", ds)

    def test_crashed_or_skipped_check_is_not_a_pass(self):
        self.generated()
        r = run(os.path.join(self.t, ".claude/scripts/check_template.py"), self.t, "--only", "C01")
        self.assertIn("VERDICT: NOT ASSESSED", r.stdout)
        self.assertEqual(r.returncode, 3)


class ValidateTests(unittest.TestCase):
    """The validation stage: each check must be seen to fail when its property is broken."""

    def setUp(self):
        self.t = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.t)
        self.rd = os.path.join(self.t, ".ssb")
        shutil.copytree(FIXTURE, self.rd)
        script("state.py", "init", self.rd, "--domain", "HR", "--target", self.t)
        script("state.py", "intake", self.rd, "--json", '{"domain": "HR"}')
        script("proposal.py", "render", self.rd)
        wr(os.path.join(self.rd, "research", "report.md"), "# Report\nRoles rest on C001 and C002.\n")
        wr(os.path.join(self.rd, "critic.md"), "independent: yes\n1. compliance-lead has no reports\n")

    def validate(self):
        return script("validate.py", self.t)

    ACC = rd(os.path.join(SKILL, "references", "acceptance.md"))
    ACC_IDS = re.findall(r"^\|\s*([PG]\d+)\s*\|", ACC, re.M)

    def message(self, text="Stopped for your approval.\nVALIDATE <stop>: <pending>\n"):
        wr(os.path.join(self.rd, "final-message.md"), text)

    def review(self, verdict="PASS", independent="yes", skip_ids=(), m_rows=True, message=True):
        """Write the validator's table: a request row, every acceptance id (minus skip_ids), one message row."""
        if message and not os.path.exists(os.path.join(self.rd, "final-message.md")):
            self.message()
        rows = ["| 1 | stop for approval | .ssb | Met |"]
        rows += [f"| {i} | criterion | evidence | Met |" for i in self.ACC_IDS if i not in skip_ids]
        if m_rows:
            rows.append("| M1 | message claim | evidence | Met |")
        wr(os.path.join(self.rd, "validation.md"),
           f"independent: {independent}\n" + "\n".join(rows) + f"\nVALIDATION: {verdict}\n")

    def trial(self, result="Pass", independent="yes", skip=()):
        out = script("trial.py", "pick", self.t).stdout.split("\n")
        picks = [l.split()[2] for l in out if l.startswith("T")]
        rows = [f"| T{i} | `{p}` | brief | shape | observed | {result} |"
                for i, p in enumerate((x for x in picks if x not in skip), 1)]
        wr(os.path.join(self.rd, "trial.md"), f"independent: {independent}\n" + "\n".join(rows) + "\n")

    def refute(self, verdict="SURVIVED", result="Not refuted", independent="yes", skip=()):
        """Write a refutation that names every changed path (minus `skip`) in its attempt table."""
        out = script("validate.py", self.t, "--changes").stdout.splitlines()[1:]
        paths = [l.split(None, 1)[1] for l in out if l.strip()]
        rows = [f"| {i} | `{p}` | claim | tried to break it | {result} | evidence |"
                for i, p in enumerate(x for x in paths if x not in skip)]
        wr(os.path.join(self.rd, "refutation.md"),
           f"independent: {independent}\n" + "\n".join(rows) + f"\nREFUTATION: {verdict}\n")

    def row(self, out, vid):
        m = re.search(rf"^{vid} (PASS|CONCERNS|FAIL|NOT ASSESSED) ", out, re.M)
        return m.group(1) if m else None

    # ---- proposal stop
    def test_proposal_stop_without_review_is_not_assessed(self):
        r = self.validate()
        self.assertIn("VALIDATE proposal:", r.stdout)
        self.assertEqual(self.row(r.stdout, "V90"), "NOT ASSESSED")
        self.assertEqual(r.returncode, 3)
        self.assertTrue(os.path.exists(os.path.join(self.rd, "validation.json")))

    def test_proposal_stop_with_review_reaches_its_best_verdict(self):
        self.refute()
        self.review()
        r = self.validate()
        # fixture sources are unverified, so the ledger and proposal carry CONCERNS
        self.assertIn("VALIDATE proposal: CONCERNS", r.stdout, r.stdout)
        for vid in ("V11", "V13", "V14", "V15", "V90", "V91", "V92"):
            self.assertEqual(self.row(r.stdout, vid), "PASS", (vid, r.stdout))

    def test_stale_review_is_not_counted(self):
        self.review()
        import time
        time.sleep(0.05)
        bp = jl(os.path.join(self.rd, "proposal.json"))
        bp["open_questions"].append("changed after review")
        jd(bp, os.path.join(self.rd, "proposal.json"))
        script("proposal.py", "render", self.rd)
        r = self.validate()
        self.assertEqual(self.row(r.stdout, "V90"), "NOT ASSESSED")
        self.assertIn("older than the files it reviews", r.stdout)

    def test_unrendered_proposal_md_fails(self):
        self.review()
        wr(os.path.join(self.rd, "proposal.md"), "hand-edited\n", "a")
        r = self.validate()
        self.assertEqual(self.row(r.stdout, "V13"), "FAIL", r.stdout)

    def test_generation_before_approval_fails(self):
        os.makedirs(os.path.join(self.t, ".claude"))
        self.review()
        self.assertEqual(self.row(self.validate().stdout, "V14"), "FAIL")

    def test_report_citing_unknown_claim_fails(self):
        wr(os.path.join(self.rd, "research", "report.md"), "Rests on C999.\n")
        self.review()
        self.assertEqual(self.row(self.validate().stdout, "V11"), "FAIL")

    def test_missing_critic_is_not_assessed_and_self_review_is_capped(self):
        os.remove(os.path.join(self.rd, "critic.md"))
        self.review(independent="no")
        out = self.validate().stdout
        self.assertEqual(self.row(out, "V15"), "NOT ASSESSED")
        self.assertEqual(self.row(out, "V90"), "CONCERNS")
        self.assertIn("capped at CONCERNS", out)

    def test_review_fail_fails_the_stage(self):
        self.review("FAIL")
        r = self.validate()
        self.assertIn("VALIDATE proposal: FAIL", r.stdout)
        self.assertEqual(r.returncode, 1)

    def test_empty_intake_is_a_concern(self):
        s = jl(os.path.join(self.rd, "state.json"))
        s["intake"] = {}
        jd(s, os.path.join(self.rd, "state.json"))
        self.assertEqual(self.row(self.validate().stdout, "V01"), "CONCERNS")

    # ---- refutation critic (V91)
    def test_missing_refutation_is_not_assessed(self):
        self.review()
        out = self.validate().stdout
        self.assertEqual(self.row(out, "V91"), "NOT ASSESSED")
        self.assertIn("no .ssb/refutation.md", out)

    def test_a_refuted_change_fails_the_stage(self):
        self.refute(verdict="SURVIVED", result="Refuted")  # verdict line cannot hide a refuted row
        self.review()
        r = self.validate()
        self.assertEqual(self.row(r.stdout, "V91"), "FAIL", r.stdout)
        self.assertEqual(r.returncode, 1)

    def test_a_change_nobody_attacked_is_not_assessed(self):
        self.refute(skip={".ssb/proposal.json"})
        self.review()
        out = self.validate().stdout
        self.assertEqual(self.row(out, "V91"), "NOT ASSESSED")
        self.assertIn(".ssb/proposal.json", out)

    def test_naming_only_a_top_level_folder_covers_nothing(self):
        wr(os.path.join(self.rd, "refutation.md"), "independent: yes\n| 1 | `.ssb` | all | looked | Not refuted | x |\n"
           "REFUTATION: SURVIVED\n")
        self.review()
        self.assertEqual(self.row(self.validate().stdout, "V91"), "NOT ASSESSED")

    def test_untested_or_self_critique_is_capped_at_concerns(self):
        self.refute(result="Could not test")
        self.review()
        self.assertEqual(self.row(self.validate().stdout, "V91"), "CONCERNS")
        self.refute(independent="no")
        self.assertEqual(self.row(self.validate().stdout, "V91"), "CONCERNS")

    def test_stale_refutation_is_not_counted(self):
        self.refute()
        self.review()
        import time
        time.sleep(0.05)
        wr(os.path.join(self.rd, "research", "report.md"), "Roles rest on C001.\n")
        out = self.validate().stdout
        self.assertEqual(self.row(out, "V91"), "NOT ASSESSED")
        self.assertIn("older than a change", out)

    def test_baseline_scopes_the_critic_to_new_changes(self):
        self.assertIn("REFUSED", script("validate.py", self.t, "--mark-reported").stdout)  # validate first
        self.refute()
        self.review()
        self.validate()
        self.assertIn("baseline recorded", script("validate.py", self.t, "--mark-reported").stdout)
        self.assertIn("CHANGES since the last reported stop: 0", script("validate.py", self.t, "--changes").stdout)
        self.assertEqual(self.row(self.validate().stdout, "V91"), "PASS")
        bp = jl(os.path.join(self.rd, "proposal.json"))
        bp["open_questions"].append("a later change")
        jd(bp, os.path.join(self.rd, "proposal.json"))
        ch = script("validate.py", self.t, "--changes").stdout
        self.assertIn("modified  .ssb/proposal.json", ch)
        self.assertNotIn("critic.md", ch)

    # ---- acceptance criteria (V90) and the final message (V92)
    def test_review_missing_an_acceptance_criterion_is_not_assessed(self):
        self.refute()
        self.review(skip_ids={"P5"})
        out = self.validate().stdout
        self.assertEqual(self.row(out, "V90"), "NOT ASSESSED")
        self.assertIn("no row for: P5", out)

    def test_acceptance_ids_are_derived_from_the_reference(self):
        self.assertIn("P1", self.ACC_IDS)
        self.assertIn("G9", self.ACC_IDS)
        self.assertEqual(len(self.ACC_IDS), len(set(self.ACC_IDS)), "acceptance ids must be unique")

    def test_missing_final_message_is_not_assessed(self):
        self.review(message=False)
        out = self.validate().stdout
        self.assertEqual(self.row(out, "V92"), "NOT ASSESSED")
        self.assertIn("no .ssb/final-message.md", out)

    def test_message_without_validator_rows_is_not_assessed(self):
        self.review(m_rows=False)
        self.assertEqual(self.row(self.validate().stdout, "V92"), "NOT ASSESSED")

    def test_message_with_a_wrong_count_fails(self):
        self.message("The proposal has 99 roles.\n")
        self.review()
        r = self.validate()
        self.assertEqual(self.row(r.stdout, "V92"), "FAIL", r.stdout)
        self.assertIn("says '99 roles'", r.stdout)

    def test_message_claiming_nothing_generated_is_checked(self):
        os.makedirs(os.path.join(self.t, ".claude"))
        self.message("Nothing was generated.\n")
        self.review()
        self.assertEqual(self.row(self.validate().stdout, "V92"), "FAIL")

    def test_qualified_counts_are_not_read_as_totals(self):
        self.message("6 skills plus 4 baseline skills; 13 roles in scope.\n")
        self.review()
        out = self.validate().stdout
        self.assertNotIn("says '4", out)

    # ---- generated stop
    def generate(self):
        self.assertEqual(script("state.py", "approve", self.rd, "--by", "user").returncode, 0)
        self.assertEqual(script("generate.py", self.t, "--layer", "all").returncode, 0)

    def test_generated_stop_passes_its_mechanical_checks(self):
        self.generate()
        self.trial()
        self.refute()
        self.message("Generated 12 agents and 10 skills.\nVALIDATE <stop>: <pending>\n")
        self.review()
        r = self.validate()
        self.assertIn("VALIDATE generated:", r.stdout)
        for vid in ("V20", "V21", "V22", "V23", "V24", "V25", "V26", "V90", "V91", "V92"):
            self.assertEqual(self.row(r.stdout, vid), "PASS", (vid, r.stdout))

    def test_generated_stop_catches_drift_and_edited_proposal(self):
        self.generate()
        wr(os.path.join(self.t, ".claude/agents/qa-lead.md"), "\nhand edit\n", "a")
        self.review()
        out = self.validate().stdout
        self.assertEqual(self.row(out, "V25"), "CONCERNS")
        self.assertIn("qa-lead.md", out)
        bp = jl(os.path.join(self.rd, "proposal.json"))
        bp["open_questions"].append("edited after generation")
        jd(bp, os.path.join(self.rd, "proposal.json"))
        out = self.validate().stdout
        # an edited proposal invalidates the approval, so the run is back at the proposal stop
        self.assertIn("VALIDATE proposal:", out)
        self.assertEqual(self.row(out, "V14"), "FAIL")

    # ---- trial run (V26)
    def test_trial_pick_is_deterministic(self):
        self.generate()
        a = script("trial.py", "pick", self.t).stdout
        self.assertEqual(a, script("trial.py", "pick", self.t).stdout)
        self.assertIn("gate  .claude/agents/compliance-lead.md", a)  # owner of the first gate by id
        self.assertIn("skill .claude/skills/functional-spec/SKILL.md", a)
        b = script("trial.py", "brief", self.t).stdout
        self.assertIn("CL-RULE-COMPLIANCE: <word>", b)
        self.assertIn("May I write", b)

    def test_missing_trial_is_not_assessed(self):
        self.generate()
        out = self.validate().stdout
        self.assertEqual(self.row(out, "V26"), "NOT ASSESSED")
        self.assertIn("no .ssb/trial.md", out)

    def test_failed_trial_fails_the_stage(self):
        self.generate()
        self.trial(result="Fail")
        r = self.validate()
        self.assertEqual(self.row(r.stdout, "V26"), "FAIL", r.stdout)
        self.assertEqual(r.returncode, 1)

    def test_untried_pick_is_not_assessed(self):
        self.generate()
        self.trial(skip={".claude/agents/backend-engineer.md"})
        out = self.validate().stdout
        self.assertEqual(self.row(out, "V26"), "NOT ASSESSED")
        self.assertIn("not tried: .claude/agents/backend-engineer.md", out)

    def test_self_trial_is_capped_at_concerns(self):
        self.generate()
        self.trial(independent="no")
        self.assertEqual(self.row(self.validate().stdout, "V26"), "CONCERNS")

    def test_generated_message_count_checked_against_disk(self):
        self.generate()
        self.trial()
        self.message("Built 13 agents.\n")
        self.review()
        out = self.validate().stdout
        self.assertEqual(self.row(out, "V92"), "FAIL")
        self.assertIn("says '13 agents', the files give 12", out)

    def test_generated_stop_with_broken_studio_fails(self):
        self.generate()
        os.remove(os.path.join(self.t, ".claude/docs/coordination-rules.md"))
        self.review()
        out = self.validate().stdout
        self.assertEqual(self.row(out, "V23"), "FAIL", out)
        self.assertIn("VALIDATE generated: FAIL", out)


class ResolverTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.t)
        shutil.copytree(os.path.join(SKILL, "assets/skeleton/.claude/scripts"), os.path.join(self.t, ".claude/scripts"))
        os.makedirs(os.path.join(self.t, ".claude/docs"))
        wr(os.path.join(self.t, ".claude/docs/stacks.tsv"), "stack\tcode_root\ttest_root\tbuild\ttest\trun\nNode\tsrc\ttests\tnpm run build\t-\tnpm start\n")

    def resolve(self, *args):
        env = {**os.environ, "STUDIO_ROOT": self.t}
        return subprocess.run([PY, os.path.join(self.t, ".claude/scripts/resolve_config.py"), *args],
                              capture_output=True, text=True, env=env)

    def write(self, name, text):
        wr(os.path.join(self.t, name), text)

    def test_rigor_fans_out(self):
        self.write("project.yaml", "modes:\n  rigor: full\n")
        out = self.resolve().stdout
        self.assertIn("modes.review_mode = full  (modes.rigor=full)", out)
        self.assertIn("modes.docs_density = thorough  (modes.rigor=full)", out)

    def test_explicit_knob_beats_rigor_and_local_beats_team(self):
        self.write("project.yaml", "modes:\n  rigor: full\n  review_mode: lean\n")
        self.assertIn("modes.review_mode = lean  (project.yaml)", self.resolve().stdout)
        self.write("project.local.yaml", "modes:\n  review_mode: solo\n  rigor: minimal\n")
        out = self.resolve().stdout
        self.assertIn("modes.review_mode = solo  (project.local.yaml)", out)
        self.assertIn("team-wide only; ignored", out)

    def test_invalid_value_is_skipped_not_coerced(self):
        self.write("project.yaml", "modes:\n  rigor: extreme\n")
        out = self.resolve().stdout
        self.assertIn("modes.rigor = minimal  (default)", out)
        self.assertIn("'extreme' is not one of", out)

    def test_stack_row_and_not_assessed(self):
        self.write("project.yaml", "stack:\n  name: Node\n")
        out = self.resolve().stdout
        self.assertIn("stack.code_root = src  (stacks.tsv row Node)", out)
        self.assertIn("commands.test =   (NOT ASSESSED (stacks.tsv row 'Node' leaves it empty))", out)

    def test_unreadable_yaml_never_fails_caller(self):
        self.write("project.yaml", "modes:\n\tbad\n")
        r = self.resolve()
        self.assertEqual(r.returncode, 0)
        self.assertIn("could not be read", r.stdout)


if __name__ == "__main__":
    unittest.main()
