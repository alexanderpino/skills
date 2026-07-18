#!/usr/bin/env python3
"""Run a command under a named machine-wide mutex.

Parallel implementers each work in their own worktree, but some tools still
share machine-level state: every worktree's `git` hits the same .git common
dir, `cmake` and package managers write shared caches, installers touch global
paths. Two such calls racing produce lock errors ("index.lock exists") or
corrupted caches. This wrapper serializes them: callers with the same lock
name queue up and run one at a time; different names don't block each other.

Usage:
  wait-in-line.py cmake --build build
  wait-in-line.py git fetch origin
  wait-in-line.py --name npm --timeout 600 -- npm install

The lock name defaults to the basename of the command (so every wrapped `git`
call queues in one line). Use --name to widen or narrow the scope — e.g. give
two different commands that fight over the same cache a shared name.

Locks are lock files under $WAIT_IN_LINE_LOCK_DIR (default: <tmpdir>/
wait-in-line), held via OS advisory locking (fcntl.flock / msvcrt.locking),
so a killed process releases its lock automatically — no stale-lock cleanup.

Exit status: the wrapped command's own exit code (128+signal if it died on a
signal); 124 if --timeout expired waiting for the lock; 127 command not found.
"""

import argparse
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time

POLL_INTERVAL = 0.2

if os.name == "nt":
    import msvcrt

    def try_lock(fh):
        try:
            fh.seek(1024)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False
else:
    import fcntl

    def try_lock(fh):
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            return False


def lock_path(name):
    user = os.environ.get("USER") or os.environ.get("USERNAME") or "shared"
    lock_dir = os.environ.get("WAIT_IN_LINE_LOCK_DIR") or os.path.join(
        tempfile.gettempdir(), f"wait-in-line-{user}"
    )
    os.makedirs(lock_dir, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name) or "default"
    return os.path.join(lock_dir, safe + ".lock")


def holder_info(path):
    """Best-effort peek at who holds the lock, for the waiting message."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read().strip() or None
    except OSError:
        return None


def main():
    parser = argparse.ArgumentParser(
        prog="wait-in-line.py",
        description="Run a command under a named machine-wide mutex.",
    )
    parser.add_argument(
        "--name",
        help="lock name (default: basename of the command); calls sharing a "
        "name run one at a time",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        metavar="SECONDS",
        help="give up waiting for the lock after this long (default: wait "
        "forever); exits 124 on expiry",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        metavar="command [args...]",
        help="the command to run; prefix with -- if it starts with a dash",
    )
    args = parser.parse_args()

    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("no command given")

    name = args.name or os.path.basename(command[0])
    path = lock_path(name)
    deadline = time.monotonic() + args.timeout if args.timeout else None

    fh = open(path, "a+", encoding="utf-8")
    try:
        waited = False
        while not try_lock(fh):
            if not waited:
                waited = True
                holder = holder_info(path)
                print(
                    "[wait-in-line] waiting for lock '%s'%s"
                    % (name, " (held by %s)" % holder if holder else ""),
                    file=sys.stderr,
                    flush=True,
                )
            if deadline is not None and time.monotonic() >= deadline:
                print(
                    "[wait-in-line] timed out after %gs waiting for lock '%s'"
                    % (args.timeout, name),
                    file=sys.stderr,
                )
                return 124
            time.sleep(POLL_INTERVAL)

        try:
            fh.seek(0)
            fh.truncate()
            fh.write("pid %d: %s\n" % (os.getpid(), shlex.join(command)))
            fh.flush()
        except OSError:
            pass  # holder info is diagnostic only

        try:
            proc = subprocess.run(command)
        except FileNotFoundError:
            print(
                "[wait-in-line] command not found: %s" % command[0],
                file=sys.stderr,
            )
            return 127
        except KeyboardInterrupt:
            return 130
        rc = proc.returncode
        return 128 - rc if rc < 0 else rc
    finally:
        fh.close()  # closing the fd releases the OS lock on both platforms


if __name__ == "__main__":
    sys.exit(main())
