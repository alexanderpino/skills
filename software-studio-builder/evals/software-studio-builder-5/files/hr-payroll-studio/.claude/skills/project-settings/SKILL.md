---
name: project-settings
description: "Shows or changes one HR Payroll Studio setting and where its value comes from. Use when the user asks what a setting is, where a value comes from, or to change a project.yaml or project.local.yaml value."
argument-hint: "[key] | [key=value] | --local key=value"
user-invocable: true
allowed-tools: Read, Edit, Write, Bash(python3 .claude/scripts/resolve_config.py*)
---

# /project-settings

- **No argument:** run `python3 .claude/scripts/resolve_config.py` and show the table.
- **`key`:** run it with `--keys <key>` and explain the source shown in brackets.
- **`key=value`:** show the line you will change in `project.yaml` (or
  `project.local.yaml` with `--local`, which accepts only `modes.review_mode` and
  `modes.automation`). Ask "May I write this to `<file>`?", edit on a yes, then run
  `--validate`. A `notes:` line after the write means the value was rejected: report it and
  offer to revert.

`modes.rigor` sets `workflow`, `docs_density`, `qa_level` and `review_mode` together; a
knob set explicitly wins over rigor.

## Return

End with `SETTING <key>: <value> (<source>)`, or `SETTING <key>: NOT ASSESSED — <why>`.
