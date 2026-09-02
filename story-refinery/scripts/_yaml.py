"""Minimal YAML-subset reader (stdlib only).

Supports exactly what refinery.yaml needs: nested maps, lists of scalars,
lists of flat maps, quoted/unquoted scalars, comments. No anchors, no block
scalars, no flow style. If a config uses more than this, save it as JSON
instead - every loader here accepts .json transparently.
"""

import json
import os

__all__ = ["loads", "load_config"]


def _strip_comment(line: str) -> str:
    out, quote = [], None
    for i, ch in enumerate(line):
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
            out.append(ch)
            continue
        if ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out).rstrip()


def _split_flow(text: str):
    parts, buf, quote = [], [], None
    for ch in text:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            continue
        if ch == ",":
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def _scalar(text: str):
    t = text.strip()
    if len(t) >= 2 and t[0] == t[-1] and t[0] in ("'", '"'):
        return t[1:-1]
    if len(t) >= 2 and t[0] == "[" and t[-1] == "]":
        inner = t[1:-1].strip()
        return [] if not inner else [_scalar(part) for part in _split_flow(inner)]
    low = t.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "~", ""):
        return None
    try:
        return int(t)
    except ValueError:
        pass
    try:
        return float(t)
    except ValueError:
        pass
    return t


def _split_kv(text: str):
    quote = None
    for i, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
            continue
        if ch == ":" and (i + 1 == len(text) or text[i + 1] in " \t"):
            return text[:i].strip(), text[i + 1 :].strip()
    return text.strip(), ""


def _looks_like_kv(text: str) -> bool:
    k, _ = _split_kv(text)
    return k != text.strip()


def _parse_list(lines, i, indent):
    out = []
    while i < len(lines) and lines[i][0] == indent and lines[i][1].startswith("- "):
        item = lines[i][1][2:].strip()
        i += 1
        if _looks_like_kv(item):
            k, v = _split_kv(item)
            d = {}
            if v == "" and i < len(lines) and lines[i][0] > indent:
                sub, i = _parse_block(lines, i, lines[i][0])
                d[k] = sub
            else:
                d[k] = _scalar(v)
            if i < len(lines) and lines[i][0] > indent and not lines[i][1].startswith("- "):
                sub, i = _parse_block(lines, i, lines[i][0])
                if isinstance(sub, dict):
                    d.update(sub)
            out.append(d)
        else:
            out.append(_scalar(item))
    return out, i


def _parse_block(lines, i, indent):
    if i >= len(lines):
        return None, i
    if lines[i][1].startswith("- "):
        return _parse_list(lines, i, indent)
    out = {}
    while i < len(lines) and lines[i][0] == indent:
        text = lines[i][1]
        if text.startswith("- "):
            break
        k, v = _split_kv(text)
        i += 1
        if v == "":
            if i < len(lines) and lines[i][0] > indent:
                sub, i = _parse_block(lines, i, lines[i][0])
                out[k] = sub
            elif i < len(lines) and lines[i][0] == indent and lines[i][1].startswith("- "):
                sub, i = _parse_list(lines, i, indent)
                out[k] = sub
            else:
                out[k] = None
        else:
            out[k] = _scalar(v)
    return out, i


def loads(text: str):
    lines = []
    for raw in text.splitlines():
        clean = _strip_comment(raw.replace("\t", "  "))
        if not clean.strip():
            continue
        lines.append((len(clean) - len(clean.lstrip(" ")), clean.strip()))
    if not lines:
        return {}
    value, _ = _parse_block(lines, 0, lines[0][0])
    return value if value is not None else {}


def load_config(path):
    """Load refinery config from .yaml/.yml/.json. Returns {} if path is None."""
    if not path:
        return {}
    if not os.path.exists(path):
        raise SystemExit("config not found: %s" % path)
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    if path.endswith(".json"):
        return json.loads(text)
    return loads(text)


def get(cfg, dotted, default=None):
    """cfg lookup by dotted path, tolerant of missing branches."""
    cur = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur or cur[part] is None:
            return default
        cur = cur[part]
    return cur
