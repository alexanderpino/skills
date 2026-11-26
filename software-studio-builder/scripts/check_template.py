#!/usr/bin/env python3
"""Run the template checker on a generated studio, from the skill's side.

    check_template.py TARGET [--proposal TARGET/.ssb/proposal.json] [--only C04,C05]

The checker itself lives in the skeleton (assets/skeleton/.claude/scripts/check_template.py)
so that every generated studio carries the same checker it was verified with. This wrapper
runs the TARGET's copy when it exists (what the studio will run on itself) and the skeleton's
copy otherwise, and passes the proposal by default so coverage (C12) is checked.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKELETON_CHECK = os.path.join(os.path.dirname(HERE), "assets", "skeleton", ".claude", "scripts", "check_template.py")


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    target = os.path.abspath(argv[0])
    rest = argv[1:]
    own = os.path.join(target, ".claude", "scripts", "check_template.py")
    checker = own if os.path.exists(own) else SKELETON_CHECK
    bp = os.path.join(target, ".ssb", "proposal.json")
    if "--proposal" not in rest and os.path.exists(bp):
        rest += ["--proposal", bp]
    print(f"checker: {os.path.relpath(checker, target) if checker == own else checker}")
    return subprocess.call([sys.executable, checker, target, *rest])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
