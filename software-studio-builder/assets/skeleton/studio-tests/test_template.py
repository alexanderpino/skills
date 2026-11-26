"""Self-tests for the studio template itself (not for the product built with it).

    python3 -m unittest discover -s studio-tests -p 'test_*.py'
"""
import os
import subprocess
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS = os.path.join(ROOT, ".claude", "scripts")


def run(script, *args):
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args], capture_output=True,
                          text=True, env={**os.environ, "STUDIO_ROOT": ROOT})


class TemplateConsistency(unittest.TestCase):
    def test_check_template_has_no_failures(self):
        r = run("check_template.py", ROOT)
        self.assertNotIn("VERDICT: FAIL", r.stdout, r.stdout)
        self.assertIn("VERDICT:", r.stdout)

    def test_resolver_reports_rigor_and_source(self):
        r = run("resolve_config.py", "--keys", "modes.rigor,modes.workflow")
        self.assertEqual(r.returncode, 0)
        self.assertRegex(r.stdout, r"modes\.rigor = (minimal|standard|full)  \(")
        self.assertRegex(r.stdout, r"modes\.workflow = \w+  \(")

    def test_resolver_validate_is_clean(self):
        r = run("resolve_config.py", "--validate")
        self.assertIn("notes: none", r.stdout, r.stdout)

    def test_artifact_check_reads_catalog(self):
        r = run("artifact_check.py")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("STEPS:", r.stdout)


if __name__ == "__main__":
    unittest.main()
