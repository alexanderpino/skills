#!/usr/bin/env python3
"""Check a directory tree against the OKF v0.2 conformance rules.

    python3 tools/okf_check.py water-physics terrain-renderer
    python3 tools/okf_check.py --all          # every skill in the repo
    python3 tools/okf_check.py --bugs         # prove the checks can fail

Exits non-zero when a tree is non-conformant, so this is a gate rather than a
report. It is deliberately a SEPARATE file from `okf_apply.py`: a generator
that also grades its own output cannot catch a document edited by hand
afterwards, and hand edits are the normal case.

THE RULES, from `okf/SPEC.md` section 11 (Google Cloud's knowledge-catalog
repository, read 2026-08-24). A bundle is conformant when:

  1. every non-reserved `.md` file has a parseable YAML frontmatter block
  2. every such block carries a non-empty `type`
  3. reserved filenames (`index.md`, `log.md`) follow sections 8 and 9

⚠️ AND ONE LOCAL RULE THE SPEC DOES NOT IMPOSE. The spec permits `verified`
anywhere. This repository forbids it on a document that nothing actually
verifies, because a trust signal that is applied by habit stops being a
signal -- it is the same rule the suites apply to tolerances. So a `verified`
entry naming a `process:` actor must name a checker THAT EXISTS in the tree,
and the check below resolves it. A verifier that cannot be found is a stronger
failure here than a missing header.

⚠️ WHAT THIS DOES NOT CHECK, stated so the exit code is not over-read. It does
not confirm that a named verifier PASSES -- only that it exists and is named.
Run the suites for that. Conformance is about whether the corpus describes
itself honestly, not about whether the physics is right.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESERVED = ('index.md', 'log.md')
# ⚠️ `evidence` IS NOT SKIPPED, and an earlier draft skipped it. Those
# directories hold README files that `okf_apply.py` stamps, so excluding
# them here made the checker report 30 documents where 32 exist -- a
# checker whose scope disagrees with the writer's is worse than none,
# because the two silently cover different sets.
SKIP_DIRS = ('.git', '__pycache__', 'node_modules')

# The trust tiers OKF section 5.3 derives from `verified`, lowest to highest.
TIER_UNVERIFIED = 'unverified'
TIER_MACHINE = 'machine-confirmed'
TIER_HUMAN = 'human-reviewed'


def frontmatter(path):
    """Return (block_text, ok). A missing or unterminated block is not ok."""
    src = open(path, encoding='utf-8', errors='replace').read()
    if not src.startswith('---\n'):
        return None, False
    end = src.find('\n---\n', 3)
    if end < 0:
        return None, False
    return src[4:end + 1], True


def top_keys(block):
    return re.findall(r'^([a-zA-Z_][\w-]*):', block, re.M)


def field(block, name):
    """The value of a top-level scalar key, or None if the key is absent.

    ⚠️ `[ \t]*` AND NOT `\s*`, and the difference is a silent misread. `\s`
    matches newlines, so on an EMPTY field the pattern skipped the line break
    and captured the next line: `type:` followed by `name: water-physics`
    returned "name: water-physics" as the type. An empty `type` is exactly the
    non-conformance this file exists to catch, and it read as the most
    conformant possible answer. Found by the --bugs harness, which reported
    the emptied-type case as MISSED.
    """
    m = re.search(r'^%s:[ \t]*(.*)$' % re.escape(name), block, re.M)
    return m.group(1).strip() if m else None


def trust_tier(block):
    """Section 5.3, applied literally."""
    if 'verified:' not in block:
        return TIER_UNVERIFIED
    ver = re.findall(r'by:[ \t]*([^\s,}]+)', block[block.index('verified:'):])
    if any(v.startswith('human:') for v in ver):
        return TIER_HUMAN
    return TIER_MACHINE


def verifiers(block):
    if 'verified:' not in block:
        return []
    return re.findall(r'by:[ \t]*process:([^\s,}]+)',
                      block[block.index('verified:'):])


def walk(tree):
    for dp, dn, fn in os.walk(os.path.join(ROOT, tree)):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in sorted(fn):
            if f.endswith('.md'):
                yield os.path.join(dp, f)


def check(trees, quiet=False):
    problems, tiers, n = [], {}, 0
    checkers = set()
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in ('.git', '__pycache__')]
        checkers.update(f for f in fn if f.endswith('.py'))
    for tree in trees:
        for path in walk(tree):
            rel = os.path.relpath(path, ROOT)
            if os.path.basename(path) in RESERVED:
                continue
            n += 1
            block, ok = frontmatter(path)
            if not ok:
                problems.append((rel, 'no parseable frontmatter block'))
                continue
            t = field(block, 'type')
            if not t:
                problems.append((rel, 'frontmatter has no non-empty `type`'))
                continue
            tier = trust_tier(block)
            tiers[tier] = tiers.get(tier, 0) + 1
            for v in verifiers(block):
                if v not in checkers:
                    problems.append(
                        (rel, 'claims verification by process:%s, which does '
                              'not exist in this tree' % v))
            st = field(block, 'status')
            if st and st.split('#')[0].strip() not in (
                    'draft', 'stable', 'deprecated'):
                problems.append((rel, 'status %r is not draft/stable/deprecated'
                                 % st))
    if not quiet:
        print('OKF v0.2 conformance: %s' % ', '.join(trees))
        print('  %d concept documents' % n)
        for k in (TIER_HUMAN, TIER_MACHINE, TIER_UNVERIFIED):
            if tiers.get(k):
                print('  %-18s %d' % (k, tiers[k]))
        if problems:
            print()
            for rel, why in problems:
                print('  NOT CONFORMANT  %-56s %s' % (rel, why))
        print()
        print('  %s' % ('conformant' if not problems
                        else '%d problem(s)' % len(problems)))
    return problems


def bugs(trees):
    """⚠️ Prove each rule can fail, by breaking one document at a time.

    A conformance checker that has never been seen to reject anything is a
    print statement. Each case edits one real file, re-runs, and restores it.
    """
    import shutil
    target = None
    for path in walk(trees[0]):
        if os.path.basename(path) not in RESERVED:
            target = path
            break
    if target is None:
        raise SystemExit('no document to perturb')
    backup = target + '.okfbak'
    shutil.copy2(target, backup)
    src = open(target, encoding='utf-8').read()
    cases = [
        ('frontmatter removed', src[src.find('\n---\n', 3) + 5:]),
        ('type emptied', re.sub(r'^type:.*$', 'type:', src, count=1, flags=re.M)),
        ('status not in the enum',
         re.sub(r'^status:.*$', 'status: current', src, count=1, flags=re.M)),
        ('verifier that does not exist',
         src.replace('---\n', '---\nverified: { by: process:no_such.py, '
                     'at: 2026-01-01T00:00:00Z }\n', 1)),
    ]
    good = True
    print('proving the OKF checks can fail (on %s):'
          % os.path.relpath(target, ROOT))
    for name, broken in cases:
        open(target, 'w', encoding='utf-8').write(broken)
        fired = bool(check(trees, quiet=True))
        print('  %-32s %s' % (name, 'caught' if fired
                              else 'MISSED  <-- the check is blind here'))
        good &= fired
    shutil.move(backup, target)
    ok_after = not check(trees, quiet=True)
    print('  %-32s %s' % ('restored, clean again',
                          'yes' if ok_after else 'NO  <-- restore failed'))
    return 0 if (good and ok_after) else 1


def main(argv):
    args = [a for a in argv[1:] if not a.startswith('--')]
    if '--all' in argv:
        args = sorted(d for d in os.listdir(ROOT)
                      if os.path.isdir(os.path.join(ROOT, d))
                      and not d.startswith('.'))
    if not args:
        args = ['water-physics', 'terrain-renderer']
    if '--bugs' in argv:
        return bugs(args)
    return 1 if check(args) else 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
