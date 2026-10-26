#!/usr/bin/env python3
"""Tests for arch.py — run: python3 scripts/test_arch.py (stdlib unittest, no deps).

Every test builds a throwaway git repository from the committed worked example
(examples/brownfield-api-keys), drives arch.py through its CLI exactly as a workflow
would, and asserts on the JSON contract and on the files left behind."""
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
ARCH = os.path.join(HERE, "arch.py")
LINT = os.path.join(SKILL, "assets", "ci", "tools", "arch_lint.py")
EXAMPLE = os.path.join(SKILL, "examples", "brownfield-api-keys")
sys.path.insert(0, HERE)
import arch  # noqa: E402

ADR_BODY = """
## Context
Clients cannot replace a leaked key without downtime (F.01).

## Decision
We will keep the old key valid for a 24-hour overlap window.

## Consequences
Rotation needs no downtime; two hashes per key during the window.
"""

CHANGE_BODY = """
# Change: {title}

## Intent
Rotate keys without downtime. Serves F.01.

## Evidence
Observed: keys are hashed at rest (`src/keys.py:6`). See [ADR-0001](../../decisions/ADR-0001-hashed-api-key-storage.md).

## Decisions on record
ADR-0001 binds this change.

## Triage
Software altitude, significant. Needs an ADR and an SD update.

## Assumptions and gaps
The 24h window is assumed.
"""


class Repo:
    def __init__(self, with_git=True, empty=False):
        self.dir = tempfile.mkdtemp(prefix="arch-test-")
        if not empty:
            shutil.copytree(EXAMPLE, self.dir, dirs_exist_ok=True)
        if with_git:
            self.git("init", "-q", "-b", "main")
            self.git("add", "-A")
            self.git("commit", "-q", "--allow-empty", "-m", "init")
            self.git("checkout", "-q", "-b", "feature")
        self.root = os.path.join(self.dir, "docs", "architecture")

    def git(self, *args):
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t"] + list(args),
                       cwd=self.dir, check=True, capture_output=True)

    def run(self, *args, expect=None):
        p = subprocess.run([sys.executable, ARCH] + list(args) + ["--json"], cwd=self.dir,
                           capture_output=True, text=True)
        if expect is not None:
            assert p.returncode == expect, f"{args}: exit {p.returncode}\n{p.stdout}\n{p.stderr}"
        try:
            return json.loads(p.stdout), p.returncode
        except json.JSONDecodeError:
            raise AssertionError(f"{args}: not JSON (exit {p.returncode})\n{p.stdout}\n{p.stderr}")

    def path(self, *parts):
        return os.path.join(self.dir, *parts)

    def read(self, *parts):
        with open(self.path(*parts), encoding="utf-8") as fh:
            return fh.read()

    def write(self, rel, text):
        p = self.path(rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)

    def append(self, rel, text):
        with open(self.path(rel), "a", encoding="utf-8") as fh:
            fh.write(text)

    def lint(self):
        return subprocess.run([sys.executable, LINT, "all", "--root", self.root, "--src",
                               self.path("src"), "--max-age-days", "0"], capture_output=True, text=True)

    # --- what a model does during propose/apply, scripted ---
    def plan(self, cid, title="Add key rotation", conflicts="[]", records_kind="adr", extra=None):
        self.run("new", cid, "--title", title, "--archetype", "significant", expect=0)
        cpath = f"docs/architecture/changes/{cid}/change.md"
        fm = self.read(cpath).split("\n# Change:")[0]
        fm = fm.replace("affects: []", "affects: [api-keys]").replace("conflicts: []", f"conflicts: {conflicts}")
        self.write(cpath, fm + "\n" + CHANGE_BODY.format(title=title).lstrip("\n"))
        rec, _ = self.run("record", records_kind, "--change", cid, "--title", title, *(extra or []), expect=0)
        self.fill_record(rec["path"])
        return rec

    def fill_record(self, relpath):
        text = self.read(relpath).split("<!-- OPTIONAL")[0]
        text = re.sub(r"^(owner|author): <[^>]+>.*$", r"\1: team-identity", text, flags=re.M)
        text = re.sub(r"^(\w[\w-]*): \[<[^\]]*\]\]?.*$", r"\1: [x]", text, flags=re.M)
        text = re.sub(r"^(deciders|reviewers|tags|satisfies|complies-with): \[[^\]]*<[^\]]*\].*$",
                      r"\1: [x]", text, flags=re.M)
        text = text.replace("affects: [<component>, <area>]", "affects: [api-keys]")
        if "## Context" in text:
            text = text.split("## Context")[0] + ADR_BODY.lstrip("\n")
        else:  # RFC: keep the heading, replace the body
            head = text.split("\n# ")[0]
            title = re.search(r"^title: (.*)$", text, flags=re.M).group(1)
            rid = re.search(r"^id: (\S+)", text, flags=re.M).group(1)
            text = head + f"\n# {rid}: {title}\n\n## Summary\nRotate keys without downtime.\n"
        self.write(relpath, text)

    def tasks(self, cid, body):
        self.write(f"docs/architecture/changes/{cid}/tasks.md", "# Tasks\n\n" + body)


class PlaceholderTests(unittest.TestCase):
    def test_detects_single_and_multiline(self):
        found = arch.placeholders("a <one>\nb <two words\nacross lines> c\n")
        self.assertEqual([ln for ln, _ in found], [1, 2])

    def test_ignores_comments_code_tags_and_arrows(self):
        text = ("<!-- <in comment> -->\n```\n<in fence>\n```\nuse `<inline>` and <br> "
                "and <https://x.y> and a <-> b and x < y > z\n")
        self.assertEqual(arch.placeholders(text), [])

    def test_tasks_inside_comments_are_not_tasks(self):
        r = Repo(with_git=False)
        r.write("t.md", "<!--\n- [ ] 1.1 example `a.md`\n-->\n## 1. G\n- [x] 1.1 real `b/c.md` and `src/x.py`\n")
        tasks = arch.parse_tasks(r.path("t.md"))
        self.assertEqual(len(tasks), 1)
        self.assertTrue(tasks[0]["done"])
        self.assertEqual(tasks[0]["paths"], ["b/c.md", "src/x.py"])
        self.assertEqual(tasks[0]["number"], "1.1")


class LifecycleTests(unittest.TestCase):
    def test_context_resolves_existing_root(self):
        r = Repo()
        ctx, _ = r.run("context", expect=0)
        self.assertEqual(ctx["state"], "ok")
        self.assertEqual(ctx["root"], "docs/architecture")
        self.assertEqual(ctx["root_resolved_by"], "existing")
        self.assertEqual(ctx["next_ids"]["ADR"], "ADR-0002")

    def test_full_cycle_new_to_archive(self):
        r = Repo()
        s, _ = r.run("new", "add-rotation", "--title", "Add key rotation", "--archetype", "significant", expect=0)
        st, _ = r.run("status", expect=0)
        self.assertEqual(st["state"], "blocked")
        problems = " ".join(m["problem"] for m in st["missing"])
        for needle in ("Intent", "affects is empty", "requires a decision record", "no tasks"):
            self.assertIn(needle, problems)

        rec = r.plan("add-rotation-2")  # second change exercises the scripted planner
        self.assertEqual(rec["id"], "ADR-0002")
        shutil.rmtree(r.path("docs/architecture/changes/add-rotation"))
        cid = "add-rotation-2"
        r.tasks(cid, "## 1. Records\n- [ ] 1.1 Fill the ADR\n\n## 2. Docs\n"
                     "- [ ] 2.1 Update `software/SD-api-keys.md`: rotation flow\n\n## 3. Code\n"
                     "- [ ] 3.1 Mark `src/keys.py` with the ADR\n")
        st, _ = r.run("status", expect=0)
        self.assertEqual(st["state"], "ready", st["missing"])
        self.assertEqual(st["selected_by"], "only-active")
        self.assertEqual(st["progress"], {"total": 3, "done": 0, "remaining": 3})
        self.assertTrue(all(t["line"] and t["source"].endswith("tasks.md") for t in st["tasks"]))

        # partial apply: claim 2.1 done without editing the file -> coverage warning
        tpath = f"docs/architecture/changes/{cid}/tasks.md"
        r.write(tpath, r.read(tpath).replace("- [ ] 1.1", "- [x] 1.1").replace("- [ ] 2.1", "- [x] 2.1"))
        st, _ = r.run("status", expect=0)
        self.assertEqual(st["state"], "in_progress")
        v, rc = r.run("verify")
        self.assertEqual(rc, 1)
        self.assertEqual(v["verdict"], "fix_critical")
        msgs = [i["message"] for i in v["issues"]]
        self.assertTrue(any("task not done: 3.1" in m for m in msgs))
        self.assertTrue(any("unchanged since" in m and "SD-api-keys.md" in m for m in msgs))

        # finish the work
        r.append("docs/architecture/software/SD-api-keys.md", "\n## Rotation\nSee ADR-0002.\n")
        r.append("src/keys.py", "\n# ARCH-REF: ADR-0002 — overlap window\ndef rotate(k): ...\n")
        r.write(tpath, r.read(tpath).replace("- [ ]", "- [x]"))
        st, _ = r.run("status", expect=0)
        self.assertEqual(st["state"], "all_done")
        v, rc = r.run("verify", expect=0)
        self.assertEqual(v["verdict"], "mechanically_clean", v["issues"])
        self.assertEqual(len(v["judgement_gate"]), 6)

        # archive: dry run changes nothing
        before = r.read(rec["path"])
        a, _ = r.run("archive", expect=0)
        self.assertFalse(a["applied"])
        self.assertEqual(r.read(rec["path"]), before)

        a, _ = r.run("archive", "--yes", expect=0)
        self.assertTrue(a["applied"])
        self.assertEqual(a["lint_after"]["exit"], 0, a["lint_after"])
        adr = r.read(rec["path"])
        self.assertRegex(adr, r"(?m)^status: accepted")
        self.assertRegex(adr, r"(?m)^## Status\nAccepted$")
        self.assertIn("ADR-0002", r.read("docs/architecture/decisions/README.md"))
        dest = a["archived_to"]
        self.assertFalse(os.path.exists(r.path(f"docs/architecture/changes/{cid}")))
        moved = r.read(dest, "change.md")
        self.assertRegex(moved, r"(?m)^status: done")
        self.assertIn("](../../../decisions/ADR-0001-hashed-api-key-storage.md)", moved)
        self.assertEqual(r.lint().returncode, 0, r.lint().stdout)
        st, _ = r.run("status", "--change", cid, expect=0)
        self.assertEqual(st["state"], "archived")
        log, _ = r.run("log", expect=0)
        self.assertTrue(log["in_sync"], log["issues"])

    def test_conflict_blocks_until_superseded(self):
        r = Repo()
        r.run("new", "replace-hashing", "--title", "Switch to argon2", "--archetype", "significant", expect=0)
        cpath = "docs/architecture/changes/replace-hashing/change.md"
        fm = r.read(cpath).split("\n# Change:")[0].replace("affects: []", "affects: [api-keys]")
        r.write(cpath, fm.replace("conflicts: []", "conflicts: [ADR-0001]") + "\n"
                + CHANGE_BODY.format(title="Switch to argon2").lstrip("\n"))
        r.tasks("replace-hashing", "## 1\n- [ ] 1.1 Fill the ADR\n")
        rec, _ = r.run("record", "adr", "--title", "Hash API keys with argon2", expect=0)
        r.fill_record(rec["path"])
        st, _ = r.run("status", expect=0)
        self.assertEqual(st["state"], "blocked")
        self.assertTrue(any("conflict with ADR-0001" in m["problem"] for m in st["missing"]))

        # a second record that supersedes ADR-0001 resolves the conflict
        sup, _ = r.run("record", "adr", "--title", "Supersede hashing", "--supersedes", "ADR-0001", expect=0)
        r.fill_record(sup["path"])
        st, _ = r.run("status", expect=0)
        self.assertEqual(st["state"], "ready", st["missing"])

        r.write("docs/architecture/changes/replace-hashing/tasks.md", "## 1\n- [x] 1.1 Fill the ADRs\n")
        r.append("src/keys.py", f"\n# ARCH-REF: {rec['id']}\n# ARCH-REF: {sup['id']}\n")
        a, _ = r.run("archive", "--yes", expect=0)
        self.assertTrue(a["applied"], a["refusals"])
        old = r.read("docs/architecture/decisions/ADR-0001-hashed-api-key-storage.md")
        self.assertRegex(old, r"(?m)^status: superseded")
        self.assertRegex(old, rf"(?m)^superseded-by: {sup['id']}")
        self.assertIn(f"Superseded by {sup['id']}", old)
        self.assertIn("Accepted — supersedes ADR-0001", r.read(sup["path"]))
        out = r.lint()
        self.assertNotIn("does not 'supersedes'", out.stdout)
        self.assertEqual(out.returncode, 0, out.stdout)

    def test_supersedes_requires_existing_unsuperseded_adr(self):
        r = Repo()
        r.run("new", "x-change", "--title", "X", expect=0)
        e, rc = r.run("record", "adr", "--title", "Y", "--supersedes", "ADR-0099")
        self.assertEqual((rc, e["error"]), (2, "supersedes_not_found"))
        self.assertFalse(any(f.startswith("ADR-0002") for f in os.listdir(r.path("docs/architecture/decisions"))))

    def test_rfc_route_accepts_rfc_with_its_adr(self):
        r = Repo()
        rfc = r.plan("rfc-route", records_kind="rfc")
        self.assertTrue(rfc["path"].startswith("docs/architecture/decisions/rfc/RFC-0001-"))
        self.assertRegex(r.read(rfc["path"]), r"(?m)^status: draft")
        adr, _ = r.run("record", "adr", "--title", "Rotate keys", "--from-rfc", "RFC-0001", expect=0)
        r.fill_record(adr["path"])
        self.assertRegex(r.read(rfc["path"]), rf"(?m)^resulting-adr: {adr['id']}")
        self.assertRegex(r.read(adr["path"]), r"(?m)^derived-from-rfc: RFC-0001")
        r.tasks("rfc-route", "## 1\n- [x] 1.1 Fill the RFC and the ADR\n")
        r.append("src/keys.py", f"\n# ARCH-REF: {adr['id']}\n")
        a, _ = r.run("archive", "--yes", expect=0)
        self.assertTrue(a["applied"], a["refusals"])
        self.assertRegex(r.read(rfc["path"]), r"(?m)^status: accepted")
        self.assertRegex(r.read(adr["path"]), r"(?m)^status: accepted")

    def test_leave_proposed_keeps_decision_open(self):
        r = Repo()
        rec = r.plan("board-pending")
        r.tasks("board-pending", "## 1\n- [x] 1.1 Fill the ADR\n")
        r.append("src/keys.py", f"\n# ARCH-REF: {rec['id']}\n")
        a, _ = r.run("archive", "--yes", "--leave-proposed", expect=0)
        self.assertTrue(a["applied"])
        self.assertRegex(r.read(rec["path"]), r"(?m)^status: proposed")

    def test_archive_refuses_incomplete_and_critical(self):
        r = Repo()
        r.plan("half-done")
        r.tasks("half-done", "## 1\n- [x] 1.1 a\n- [ ] 1.2 b\n")
        a, rc = r.run("archive", "--yes")
        self.assertEqual(rc, 1)
        self.assertTrue(a["refused"])
        self.assertTrue(any("not done" in x for x in a["refusals"]))
        self.assertTrue(os.path.isdir(r.path("docs/architecture/changes/half-done")))
        a, rc = r.run("archive", "--yes", "--allow-incomplete")
        self.assertEqual(rc, 0, a["refusals"])

    def test_trivial_needs_no_change(self):
        r = Repo()
        e, rc = r.run("new", "fix-typo", "--title", "Fix typo", "--archetype", "trivial")
        self.assertEqual((rc, e["error"]), (2, "not_needed"))

    def test_invalid_ids_and_duplicates(self):
        r = Repo()
        e, rc = r.run("new", "Bad_Name", "--title", "x")
        self.assertEqual(e["error"], "invalid_change_id")
        r.run("new", "dup", "--title", "x", expect=0)
        e, rc = r.run("new", "dup", "--title", "x")
        self.assertEqual(e["error"], "change_exists")

    def test_ambiguous_change_selection(self):
        r = Repo()
        r.run("new", "one", "--title", "x", expect=0)
        r.run("new", "two", "--title", "y", expect=0)
        e, rc = r.run("status")
        self.assertEqual((rc, e["error"]), (2, "change_required"))
        self.assertEqual(e["active"], ["one", "two"])
        lst, _ = r.run("list", expect=0)
        self.assertEqual([c["change"] for c in lst["changes"]], ["one", "two"])


class ConsultTests(unittest.TestCase):
    def test_marker_binds_and_warns(self):
        r = Repo()
        r.append("src/keys.py", "\n# ARCH-REF: ADR-0042\n")
        c, _ = r.run("consult", expect=0)
        self.assertIn("src/keys.py", c["code"])
        self.assertEqual(c["binding"], ["ADR-0001"])
        d = c["decisions"][0]
        self.assertEqual(d["strength"], "strong")
        self.assertTrue(any("ADR-0042" in w and "no record" in w for w in c["warnings"]))
        self.assertTrue(any(p.endswith("SD-api-keys.md") for p in c["suggested_reads"]))

    def test_paths_and_affects_without_diff(self):
        r = Repo()
        c, _ = r.run("consult", "--paths", "src/other.py", "--affects", "api-keys", expect=0)
        self.assertIn("ADR-0001", [d["id"] for d in c["decisions"]])
        self.assertEqual(c["decisions"][0]["strength"], "candidate")


class EnvironmentTests(unittest.TestCase):
    def test_no_docs_root_then_init(self):
        r = Repo(empty=True)
        ctx, _ = r.run("context", expect=0)
        self.assertEqual(ctx["state"], "no_docs_root")
        e, rc = r.run("status")
        self.assertEqual((rc, e["error"]), (2, "no_docs_root"))
        dry, _ = r.run("init", expect=0)
        self.assertFalse(dry["applied"])
        self.assertFalse(os.path.exists(r.root))
        done, _ = r.run("init", "--yes", "--with-ci", expect=0)
        self.assertTrue(done["applied"])
        for f in ("README.md", "AD.md", "GLOSSARY.md", "conformance-checklist.md", "decisions/README.md"):
            self.assertTrue(os.path.exists(os.path.join(r.root, f)), f)
        self.assertTrue(os.path.exists(r.path("tools/arch_lint.py")))
        ctx, _ = r.run("context", expect=0)
        self.assertEqual((ctx["state"], ctx["validator_source"]), ("ok", "repo"))

    def test_outside_git_checks_are_skipped_not_passed(self):
        r = Repo(with_git=False)
        rec = r.plan("no-git")
        r.tasks("no-git", "## 1\n- [x] 1.1 Fill the ADR\n")
        v, rc = r.run("verify")
        self.assertEqual(v["verdict"], "not_fully_verified", v["issues"])
        skipped = {c["name"] for c in v["checks"] if c["status"] == "skipped"}
        self.assertTrue({"task_coverage", "breadcrumbs", "index"} <= skipped)

    def test_log_check_and_write(self):
        r = Repo()
        os.remove(os.path.join(r.root, "decisions", "README.md"))
        log, rc = r.run("log")
        self.assertEqual(rc, 1)
        self.assertFalse(log["in_sync"])
        w, _ = r.run("log", "--write", expect=0)
        text = r.read("docs/architecture/decisions/README.md")
        self.assertIn("[ADR-0001](./ADR-0001-hashed-api-key-storage.md)", text)
        self.assertNotIn("<slug>", text)
        log, _ = r.run("log", expect=0)
        self.assertTrue(log["in_sync"], log["issues"])


class ExportTests(unittest.TestCase):
    """The hand-over from the standards-based record to OpenSpec / spec-kit."""

    OPENSPEC = shutil.which("openspec") or os.environ.get("OPENSPEC_BIN")

    def planned(self):
        r = Repo()
        rec = r.plan("add-key-rotation")
        r.tasks("add-key-rotation", "## 1\n- [ ] 1.1 Fill the ADR\n")
        st, _ = r.run("status", expect=0)
        self.assertEqual(st["state"], "ready", st["missing"])
        return r, rec

    def test_blocked_change_cannot_be_handed_over(self):
        r = Repo()
        r.run("new", "half", "--title", "Half planned", "--archetype", "significant", expect=0)
        e, rc = r.run("export", "openspec", "--change", "half")
        self.assertEqual((rc, e["error"]), (2, "not_ready"))

    def test_openspec_seed_is_derived_and_validates(self):
        r, rec = self.planned()
        dry, _ = r.run("export", "openspec", expect=0)
        self.assertFalse(dry["applied"])
        self.assertFalse(os.path.exists(r.path("openspec")))
        d = dry["derived"]
        self.assertEqual(d["records"], [rec["id"]])
        self.assertEqual(d["drivers"], ["F.01"])            # from the ADR's satisfies: and the story
        self.assertEqual(d["stories"], ["US-001"])
        self.assertEqual(d["capability"], "developer-platform")  # from realizes-capabilities: CAP-developer-platform
        self.assertIn("docs/architecture/contracts/openapi.yaml", d["contracts"])
        self.assertEqual(dry["gaps"], [])

        done, _ = r.run("export", "openspec", "--yes", expect=0)
        self.assertTrue(done["applied"])
        spec = r.read("openspec/changes/add-key-rotation/specs/developer-platform/spec.md")
        self.assertIn("## Purpose\n\nExternal integrators can authenticate", spec)   # '**So that**' stripped
        self.assertIn("### Requirement: Generate an API key", spec)
        self.assertIn("The system MUST let an authenticated integrator", spec)
        self.assertEqual(spec.count("#### Scenario:"), 3)                        # one per Gherkin scenario
        self.assertIn("- **WHEN** I am an authenticated integrator with no API key\n- **AND** I POST /api/keys\n- **THEN** I receive a 201", spec)
        self.assertIn("*(trace: F.01)*", spec)
        proposal = r.read("openspec/changes/add-key-rotation/proposal.md")
        self.assertIn("## Why\n\nRotate keys without downtime. Serves F.01.", proposal)
        self.assertIn("- `developer-platform`:", proposal)
        design = r.read("openspec/changes/add-key-rotation/design.md")
        self.assertIn("### ADR-0002:", design)
        self.assertIn("OAuth flows, per-endpoint scopes, billing. (EP-001)", design)      # epic out-of-scope → Non-Goals
        self.assertIn("consequence accepted in ADR-0002", design)                         # plain-prose Consequences kept
        self.assertIn("## Open Questions\n\n- The 24h window is assumed.", design)
        tasks = r.read("openspec/changes/add-key-rotation/tasks.md")
        self.assertIn("ARCH-REF: ADR-0002", tasks)
        self.assertRegex(tasks, r"(?m)^- \[ \] 2\.1 Implement US-001")
        self.assertIn("schema: spec-driven", r.read("openspec/changes/add-key-rotation/.openspec.yaml"))
        self.assertRegex(r.read("docs/architecture/changes/add-key-rotation/change.md"),
                         r"(?m)^handoff: \[openspec:openspec/changes/add-key-rotation@[0-9a-f]{12}\]")

        e, rc = r.run("export", "openspec", "--yes")
        self.assertEqual((rc, e["error"]), (2, "target_exists"))
        r.run("export", "openspec", "--yes", "--force", expect=0)

        if not self.OPENSPEC:
            self.skipTest("openspec CLI not available (set OPENSPEC_BIN to run the real validator)")
        subprocess.run([self.OPENSPEC, "init", "--tools", "none", "--no-animation", "."], cwd=r.dir,
                       capture_output=True, text=True, check=True)
        p = subprocess.run([self.OPENSPEC, "validate", "add-key-rotation", "--strict", "--no-interactive"],
                           cwd=r.dir, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        st = subprocess.run([self.OPENSPEC, "status", "--change", "add-key-rotation", "--json"],
                            cwd=r.dir, capture_output=True, text=True, check=True)
        self.assertTrue(json.loads(st.stdout)["isPlanningComplete"])

    def test_openspec_modified_when_capability_exists(self):
        r, rec = self.planned()
        r.write("openspec/specs/developer-platform/spec.md",
                "# developer-platform\n\n## Purpose\n\nx\n\n## Requirements\n\n### Requirement: Generate an API key\nold\n\n#### Scenario: s\n- **WHEN** a\n- **THEN** b\n")
        # the PRD changes F.01 on this branch → MODIFIED against the base branch's PRD
        prd = "docs/architecture/PRD.md"
        r.write(prd, r.read(prd).replace("returning the key value exactly once.", "returning the key value exactly once and a rotation handle."))
        out, _ = r.run("export", "openspec", "--yes", expect=0)
        self.assertEqual(out["derived"]["prd_delta"]["modified"], ["F.01"])
        spec = r.read("openspec/changes/add-key-rotation/specs/developer-platform/spec.md")
        self.assertNotIn("## Purpose", spec)
        self.assertIn("## MODIFIED Requirements", spec)
        self.assertIn("a rotation handle", spec)
        proposal = r.read("openspec/changes/add-key-rotation/proposal.md")
        self.assertIn("### Modified Capabilities\n- `developer-platform`", proposal)

    def test_speckit_seed(self):
        r, rec = self.planned()
        os.makedirs(r.path(".specify/memory"))
        os.makedirs(r.path("specs/002-older-feature"))        # numbering continues after the highest
        out, _ = r.run("export", "speckit", "--yes", expect=0)
        self.assertEqual(out["dest"], "specs/003-add-key-rotation")
        self.assertEqual(json.loads(r.read(".specify/feature.json")), {"feature_directory": "specs/003-add-key-rotation"})
        spec = r.read("specs/003-add-key-rotation/spec.md")
        self.assertIn("### User Story 1 - Generate an API key (Priority: P1)", spec)   # must → P1
        self.assertIn("**Given** I am an authenticated integrator with no API key, **When** I POST /api/keys, **Then**", spec)
        self.assertIn("- **FR-001**: The system MUST let an authenticated integrator", spec)
        self.assertIn("*(trace: F.01)*", spec)
        self.assertIn("- **SC-001**:", spec)
        self.assertIn("## Assumptions\n\n- The 24h window is assumed.", spec)
        self.assertNotIn("NEEDS CLARIFICATION", spec)
        research = r.read("specs/003-add-key-rotation/research.md")
        self.assertIn("- **Decision**: We will keep the old key valid", research)
        plan = r.read("specs/003-add-key-rotation/plan.md")
        self.assertIn("**Constraints**: C.01:", plan)
        self.assertIn("**Language/Version**: NEEDS CLARIFICATION", plan)       # honest: the record does not say
        tasks = r.read("specs/003-add-key-rotation/tasks.md")
        self.assertRegex(tasks, r"(?m)^- \[ \] T003 \[US1\] Implement US-001")
        self.assertIn("ARCH-REF: ADR-0002", tasks)
        self.assertTrue(os.path.exists(r.path("specs/003-add-key-rotation/contracts/openapi.yaml")))
        self.assertTrue(os.path.exists(r.path("specs/003-add-key-rotation/checklists/requirements.md")))
        self.assertRegex(r.read("docs/architecture/changes/add-key-rotation/change.md"),
                         r"(?m)^handoff: \[speckit:specs/003-add-key-rotation@[0-9a-f]{12}\]")

    def test_constitution_from_principles(self):
        r = Repo()
        e, rc = r.run("export", "constitution")
        self.assertEqual((rc, e["error"]), (2, "no_principles"))
        r.write("docs/architecture/enterprise/enterprise-architecture.md",
                "---\nid: EA\ntitle: EA\nstatus: current\nlevel: enterprise\nupdated: 2026-01-01\n---\n# EA\n\n"
                "## 2. Architecture principles\n| ID | Principle | Statement | Rationale |\n|---|---|---|---|\n"
                "| PR.01 | Buy before build | Prefer a product over bespoke code. | Our edge is not infrastructure. |\n"
                "| PR.02 | Boring technology | New tech needs an innovation token. | Operability. |\n")
        dry, _ = r.run("export", "constitution", expect=0)
        self.assertEqual(dry["principles"], ["PR.01", "PR.02"])
        self.assertFalse(dry["applied"])
        done, _ = r.run("export", "constitution", "--yes", expect=0)
        text = r.read(".specify/memory/constitution.md")
        self.assertIn("### I. Buy before build (PR.01)", text)
        self.assertIn("### II. Boring technology (PR.02)", text)
        self.assertIn("## Additional Constraints\n\n- C.01:", text)
        self.assertIn("**Version**: 1.0.0", text)
        e, rc = r.run("export", "constitution", "--yes")
        self.assertEqual(e["error"], "target_exists")

    def test_handoff_is_visible_and_drift_is_detected_but_nothing_locks(self):
        r, rec = self.planned()
        r.tasks("add-key-rotation", "## 1\n- [x] 1.1 Fill the ADR\n")
        r.append("src/keys.py", "\n# ARCH-REF: ADR-0002\n")
        cpath = "docs/architecture/changes/add-key-rotation/change.md"
        out, _ = r.run("export", "openspec", "--yes", expect=0)
        self.assertRegex(r.read(cpath), r"(?m)^handoff: \[openspec:openspec/changes/add-key-rotation@[0-9a-f]{12}\]")
        self.assertIn(f"record fingerprint {out['fingerprint']}", r.read("openspec/changes/add-key-rotation/proposal.md"))

        st, _ = r.run("status", expect=0)
        h = st["implementation"][0]
        self.assertEqual((h["target"], h["state"], h["seed_current"]), ("openspec", "not_started", True))
        v, _ = r.run("verify", expect=0)
        self.assertEqual(next(c for c in v["checks"] if c["name"] == "handoff")["status"], "passed")

        # the implementer ticks a task: progress is visible from the architecture side
        tp = "openspec/changes/add-key-rotation/tasks.md"
        r.write(tp, r.read(tp).replace("- [ ] 2.1", "- [x] 2.1"))
        st, _ = r.run("status", expect=0)
        self.assertEqual(st["implementation"][0]["state"], "in_progress")

        # the record moves on after the seed: drift is reported, with the way out
        r.write(rec["path"], r.read(rec["path"]).replace("24-hour", "48-hour"))
        v, _ = r.run("verify", expect=0)
        drift = [i for i in v["issues"] if i["dimension"] == "Implementation"]
        self.assertEqual(len(drift), 1)
        self.assertIn("changed after the openspec seed", drift[0]["message"])
        self.assertEqual(drift[0]["severity"], "WARNING")

        # the implementer also refined proposal.md by hand; a re-export must not undo either
        pp = "openspec/changes/add-key-rotation/proposal.md"
        r.append(pp, "\nHand-written note from the implementer.\n")
        re_out, _ = r.run("export", "openspec", "--yes", "--force", expect=0)
        self.assertEqual(re_out["kept"], ["proposal.md"])
        self.assertIn("Hand-written note", r.read(pp))                          # kept
        self.assertIn("48-hour", r.read("openspec/changes/add-key-rotation/design.md"))   # regenerated
        self.assertIn("- [x] 2.1", r.read(tp))                                   # tick carried over
        self.assertTrue(any(p["action"] == "keep" and p["path"].endswith("proposal.md") for p in re_out["plan"]))
        self.assertTrue(any("carry the record" in g for g in re_out["gaps"]))
        v, _ = r.run("verify", expect=0)
        self.assertEqual([i for i in v["issues"] if i["dimension"] == "Implementation"], [])

        # archive is not held back by an open implementation, but says where it stands
        a, _ = r.run("archive", expect=0)
        self.assertFalse(a["refused"])
        self.assertTrue(any(p.startswith("implementation (openspec): in_progress 1/") for p in a["plan"]), a["plan"])
        a, _ = r.run("archive", "--yes", expect=0)
        self.assertTrue(a["applied"])
        st, _ = r.run("status", "--change", "add-key-rotation", expect=0)
        self.assertEqual((st["state"], st["implementation"][0]["state"]), ("archived", "in_progress"))
        self.assertTrue(st["implementation"][0]["seed_current"])  # accepting the ADR is not drift

        # OpenSpec archives its change: the link follows it into changes/archive/
        os.makedirs(r.path("openspec/changes/archive"))
        shutil.move(r.path("openspec/changes/add-key-rotation"),
                    r.path("openspec/changes/archive/2026-11-01-add-key-rotation"))
        st, _ = r.run("status", "--change", "add-key-rotation", expect=0)
        self.assertEqual(st["implementation"][0]["state"], "archived")
        self.assertEqual(st["implementation"][0]["path"], "openspec/changes/archive/2026-11-01-add-key-rotation")

        # the target disappears: a warning, never a crash or a lock
        shutil.rmtree(r.path("openspec/changes/archive/2026-11-01-add-key-rotation"))
        v, _ = r.run("verify", "--change", "add-key-rotation", expect=0)
        self.assertTrue(any("no longer exists" in i["message"] for i in v["issues"]))


if __name__ == "__main__":
    unittest.main(verbosity=1)
