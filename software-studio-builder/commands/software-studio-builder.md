---
description: Research a software domain and build a Claude Code studio template for it (proposal first, approval, then generation)
argument-hint: <domain> [target-dir]
---

Use the `software-studio-builder` skill for: $ARGUMENTS

Start at Phase 0 (intake). If `<target>/.ssb/state.json` exists, resume that run instead:
`python3 <skill>/scripts/state.py show <target>/.ssb`.
