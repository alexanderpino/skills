#!/usr/bin/env python3
"""Periodically save gauntlet workflow state (journal, result files) to a dedicated git branch.

Why a separate branch: it never collides with the working branch, and each push replaces a single commit
(force-with-lease), so a large, growing journal does not bloat history.

Usage: python3 scripts/checkpoint.py [--interval 600] [--once] [--round 3]
Env:   WF_DIR   workflow transcript dir (default: newest under ~/.claude/projects/*/subagents/workflows/)
"""
import argparse
import glob
import hashlib
import os
import shutil
import subprocess
import sys
import time

REPO = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
BRANCH = "claude/engine-skill-framework-checkpoints"
WT = os.path.join("/tmp", "engine-skill-framework-ckpt-worktree")


def run(*a, cwd=REPO, check=True):
    return subprocess.run(a, cwd=cwd, check=check, capture_output=True, text=True)


def newest_wf():
    d = os.environ.get("WF_DIR")
    if d:
        return d
    c = glob.glob(os.path.expanduser("~/.claude/projects/*/*/workflows/wf_*")) + \
        glob.glob(os.path.expanduser("~/.claude/projects/*/subagents/workflows/wf_*"))
    return max(c, key=os.path.getmtime) if c else None


def sources(wf):
    out = []
    if wf:
        out += [p for p in glob.glob(os.path.join(wf, "journal.jsonl"))]
    out += glob.glob("/tmp/claude-0/*/*/tasks/*.output")      # workflow/agent result files, if present
    return [p for p in out if os.path.isfile(p) and os.path.getsize(p) > 0]


def digest(paths):
    h = hashlib.sha1()
    for p in sorted(paths):
        st = os.stat(p)
        h.update(f"{p}:{st.st_size}:{int(st.st_mtime)}".encode())
    return h.hexdigest()


def snapshot(paths, rnd):
    head = run("git", "rev-parse", "HEAD").stdout.strip()
    if os.path.exists(WT):
        run("git", "worktree", "remove", "--force", WT, check=False)
    run("git", "worktree", "add", "--force", "-B", BRANCH, WT, head)
    dest = os.path.join(WT, "engine-skill-framework", "gauntlet", f"round-{rnd}", "workflow", "checkpoint")
    os.makedirs(dest, exist_ok=True)
    for p in paths:
        name = os.path.basename(os.path.dirname(p)) + "__" + os.path.basename(p) \
            if os.path.basename(p) == "journal.jsonl" else os.path.basename(p)
        shutil.copyfile(p, os.path.join(dest, name))
    run("git", "add", "-A", cwd=WT)
    msg = f"checkpoint: workflow state ({len(paths)} files, {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} UTC)"
    run("git", "-c", "user.name=checkpoint", "-c", "user.email=checkpoint@localhost", "commit", "-q", "-m", msg,
        "--allow-empty", cwd=WT)
    for i in range(4):
        r = run("git", "push", "-q", "--force", "-u", "origin", BRANCH, cwd=WT, check=False)
        if r.returncode == 0:
            return True
        time.sleep(2 ** (i + 1))
    print("push failed:", r.stderr.strip(), file=sys.stderr)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=600)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--round", type=int, default=3)
    a = ap.parse_args()
    last = None
    while True:
        paths = sources(newest_wf())
        d = digest(paths) if paths else None
        if d and d != last:
            ok = snapshot(paths, a.round)
            print(time.strftime("%H:%M:%S"), "checkpoint", "pushed" if ok else "FAILED", len(paths), "files", flush=True)
            if ok:
                last = d
        if a.once:
            break
        time.sleep(a.interval)


if __name__ == "__main__":
    main()
