"""A deliberately small YAML subset, stdlib only.

The studio's config files (project.yaml, project.local.yaml, .claude/agent-models.yaml)
are written in this subset so that every helper can read them without PyYAML:

    # comment
    key: scalar            # strings, ints, true/false, null/~ ; quotes optional
    key: [a, b, "c d"]     # inline list of scalars
    key:                   # nested mapping, indented by two spaces
      child: value
    key:                   # block list of scalars
      - a
      - b

Anything outside the subset (anchors, multi-line strings, lists of mappings) raises
MiniYamlError naming the line, so a file that cannot be read is reported, never guessed.
"""
from __future__ import annotations

import re


class MiniYamlError(ValueError):
    pass


def _scalar(text: str):
    t = text.strip()
    if t == "" or t in ("~", "null"):
        return None
    if t in ("true", "false"):
        return t == "true"
    if (t[0] == t[-1]) and t[0] in "\"'" and len(t) >= 2:
        return t[1:-1]
    if re.fullmatch(r"-?\d+", t):
        return int(t)
    if re.fullmatch(r"-?\d+\.\d+", t):
        return float(t)
    return t


def _strip_comment(line: str) -> str:
    out, q = [], None
    for i, ch in enumerate(line):
        if q:
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out).rstrip()


def _inline_list(text: str, lineno: int):
    inner = text.strip()[1:-1].strip()
    if not inner:
        return []
    items, cur, q = [], [], None
    for ch in inner:
        if q:
            cur.append(ch)
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
            cur.append(ch)
        elif ch == ",":
            items.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    items.append("".join(cur))
    return [_scalar(i) for i in items]


def loads(text: str) -> dict:
    lines = []
    for n, raw in enumerate(text.splitlines(), 1):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise MiniYamlError(f"line {n}: tab indentation is not supported")
        s = _strip_comment(raw)
        if s.strip():
            lines.append((n, len(s) - len(s.lstrip(" ")), s.strip()))
    root: dict = {}
    # stack of (indent, container, pending_key_parent)
    stack: list[tuple[int, object]] = [(-1, root)]
    pending: tuple[dict, str, int] | None = None  # (parent, key, indent) awaiting a block
    for n, ind, s in lines:
        if pending is not None:
            parent, key, pind = pending
            pending = None
            if ind > pind:
                container = [] if s.startswith("- ") or s == "-" else {}
                parent[key] = container
                stack.append((ind, container))
            # else: the key keeps its None value
        while stack and ind < stack[-1][0]:
            stack.pop()
        if not stack:
            raise MiniYamlError(f"line {n}: bad indentation")
        cind, container = stack[-1]
        if ind != cind and cind != -1:
            raise MiniYamlError(f"line {n}: inconsistent indentation")
        if cind == -1 and ind != 0:
            raise MiniYamlError(f"line {n}: top-level keys must not be indented")
        if s.startswith("- ") or s == "-":
            if not isinstance(container, list):
                raise MiniYamlError(f"line {n}: list item where a mapping key was expected")
            item = s[1:].strip()
            if re.match(r"^[^\"'\[][^:]*:\s", item + " ") and not item.startswith("["):
                raise MiniYamlError(f"line {n}: lists of mappings are outside the subset")
            container.append(_inline_list(item, n) if item.startswith("[") else _scalar(item))
            continue
        if not isinstance(container, dict):
            raise MiniYamlError(f"line {n}: mapping key inside a list")
        m = re.match(r"^([A-Za-z0-9_.\-/]+|\"[^\"]+\"|'[^']+'):(?:\s+(.*))?$", s)
        if not m:
            raise MiniYamlError(f"line {n}: not a 'key: value' line: {s!r}")
        key = _scalar(m.group(1))
        val = m.group(2)
        if key in container:
            raise MiniYamlError(f"line {n}: duplicate key {key!r}")
        if val is None or val.strip() == "":
            container[key] = None
            pending = (container, key, ind)
        elif val.strip().startswith("["):
            if not val.strip().endswith("]"):
                raise MiniYamlError(f"line {n}: unterminated inline list")
            container[key] = _inline_list(val, n)
        elif val.strip()[0] in "{&*|>":
            raise MiniYamlError(f"line {n}: {val.strip()[0]!r} syntax is outside the subset")
        else:
            container[key] = _scalar(val)
    return root


def load(path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return loads(fh.read())


def _dump_scalar(v) -> str:
    if v is None:
        return "~"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if s == "" or re.search(r"[:#\[\]{},&*|>!%@`\"']|^\s|\s$|^-", s) or s in ("true", "false", "null", "~") \
            or re.fullmatch(r"-?\d+(\.\d+)?", s):
        return '"' + s.replace('"', "'") + '"'
    return s


def dumps(data: dict, indent: int = 0) -> str:
    out = []
    pad = " " * indent
    for k, v in data.items():
        if isinstance(v, dict):
            out.append(f"{pad}{k}:")
            out.append(dumps(v, indent + 2).rstrip("\n"))
        elif isinstance(v, list):
            out.append(f"{pad}{k}: [" + ", ".join(_dump_scalar(i) for i in v) + "]")
        else:
            out.append(f"{pad}{k}: {_dump_scalar(v)}")
    return "\n".join(x for x in out if x != "") + "\n"


def get(data: dict, dotted: str):
    cur = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur
