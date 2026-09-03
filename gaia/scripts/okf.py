"""Reading OKF front matter, in the strict subset Gaia writes.

Open Knowledge Format: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
Per the spec, front matter is YAML between `---` fences and `type` is the only always-required
key; `title`, `description`, `resource` and `tags` are recommended; `status` is one of
`draft | stable | deprecated`; and `okf_version` belongs in the bundle-root index only.

WHY THIS PARSES A SUBSET INSTEAD OF IMPORTING PyYAML

Gaia ships no dependencies on purpose -- it is prose and two scripts, and a reader who clones
it should be able to run the guard with a bare Python. A strict subset parser buys something
better than convenience, though: it makes the FORMAT part of the contract. Anything this
parser cannot read is rejected loudly, so the corpus cannot drift into anchors, multi-line
folded scalars or nested maps that a later reader would have to guess at. The restriction is
the feature; `Unparseable` is the enforcement.

Accepted:
    key: scalar
    key: [a, b, c]
    key: { k: v, k2: v2 }
    key:
      - scalar
      - { k: v, k2: v2 }
Everything else raises.
"""
from __future__ import annotations

import re
from pathlib import Path


class Unparseable(Exception):
    """The document's front matter is outside the subset Gaia allows.

    Raised rather than skipped. A guard that silently ignores what it cannot read reports
    coverage it does not have -- the failure this repo has hit repeatedly.
    """


_FENCE = "---"
_SCALAR = re.compile(r"^[^:\[\]{}#]*$")


def _scalar(raw: str) -> str | bool | int:
    s = raw.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    if s in ("true", "false"):
        return s == "true"
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    return s


def _inline_map(raw: str, where: str) -> dict:
    """`{ k: v, k2: v2 }` -- one level, no nesting, which is all the spec's examples need."""
    s = raw.strip()
    if not (s.startswith("{") and s.endswith("}")):
        raise Unparseable(f"{where}: `{s}` is not a closed inline map")
    body = s[1:-1].strip()
    # One level only. Without this, `{a: {b: c}}` splits on the first colon and yields
    # {'a': '{b'} -- silently wrong data from a parser that looked like it worked, which is
    # worse than a crash. Nesting is rejected, not flattened.
    if any(ch in body for ch in "{}[]"):
        raise Unparseable(
            f"{where}: nested map or list inside an inline map is outside the subset")
    out: dict = {}
    if not body:
        return out
    for part in _split_commas(body, where):
        if ":" not in part:
            raise Unparseable(f"{where}: `{part.strip()}` in an inline map has no `key: value`")
        k, v = part.split(":", 1)
        out[k.strip()] = _scalar(v)
    return out


def _split_commas(body: str, where: str) -> list[str]:
    """Split on commas that are not inside quotes -- titles contain commas constantly."""
    parts, buf, quote = [], [], ""
    for ch in body:
        if quote:
            if ch == quote:
                quote = ""
            buf.append(ch)
        elif ch == '"':
            # Only the DOUBLE quote opens a quoted span. An apostrophe must not: YAML uses
            # single quotes too, but this subset does not, and treating ' as a delimiter meant
            # an ordinary possessive silently swallowed the following commas --
            #   [don't, generation, won't]   -> one item, three tags merged
            #   [rock's, sand's, generation] -> two items instead of three
            # with no error raised. The FIRST tag is the document's axis, so a merged tag
            # refiles the document, which is precisely what this function's caller warns about.
            quote = ch
            buf.append(ch)
        elif ch == ",":
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if quote:
        raise Unparseable(f"{where}: unterminated quote")
    parts.append("".join(buf))
    return [p for p in parts if p.strip()]


def _inline_list(raw: str, where: str) -> list:
    """`[a, b, c]` -- one level, closed, no nesting.

    This function originally had NONE of the guards `_inline_map` has, so it carried the exact
    bug that one was fixed for: `[a, [b, c]]` yielded `['a', '[b', 'c]']`, and `[a, b` (never
    closed) silently DROPPED the last element. Tags decide a document's routing axis, so a
    mangled or dropped tag quietly refiles it. Fixing one function and not its sibling is how
    that survived; they now share the same three rules.
    """
    s = raw.strip()
    if not (s.startswith("[") and s.endswith("]")):
        raise Unparseable(f"{where}: `{s}` is not a closed inline list")
    body = s[1:-1].strip()
    if any(ch in body for ch in "{}[]"):
        raise Unparseable(f"{where}: nested list or map inside an inline list is outside "
                          "the subset")
    if not body:
        return []
    return [_scalar(p) for p in _split_commas(body, where)]


def parse_front_matter(path: Path) -> tuple[dict, str]:
    """Return (front matter, body). Raises Unparseable rather than guessing."""
    text = path.read_text(encoding="utf-8")
    # str.splitlines() breaks on U+2028, U+2029, U+000B, U+000C and U+0085 -- none of which a
    # reader or a diff sees as a line break. A quoted value containing one could therefore
    # inject a front-matter key, overwrite `type`, or close the front matter early. Split on
    # real newlines only, and reject the separators outright so nothing depends on subtlety.
    for bad in ("\u2028", "\u2029", "\u0085", "\x0b", "\x0c"):
        if bad in text.split("---")[0] + (text.split("---")[1] if "---" in text[3:] else ""):
            raise Unparseable(f"{path}: front matter contains U+{ord(bad):04X}, a separator "
                              "that is invisible in a diff but splits lines")
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != _FENCE:
        raise Unparseable(f"{path}: no OKF front matter (first line is not `---`)")
    try:
        close = next(i for i in range(1, len(lines)) if lines[i].strip() == _FENCE)
    except StopIteration:
        raise Unparseable(f"{path}: front matter is never closed by `---`") from None

    fm: dict = {}
    key = None
    i = 1
    while i < close:
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        where = f"{path}:{i + 1}"
        if line.startswith((" ", "\t")):
            stripped = line.strip()
            if not stripped.startswith("- "):
                raise Unparseable(f"{where}: indented line that is not a `- ` list item")
            if key is None:
                raise Unparseable(f"{where}: list item before any key")
            item = stripped[2:].strip()
            fm.setdefault(key, [])
            if not isinstance(fm[key], list):
                raise Unparseable(f"{where}: `{key}` already has a scalar value")
            fm[key].append(_inline_map(item, where) if item.startswith("{") else _scalar(item))
            i += 1
            continue

        if ":" not in line:
            raise Unparseable(f"{where}: `{line.strip()}` is not `key: value`")
        key, raw = line.split(":", 1)
        key, raw = key.strip(), raw.strip()
        # A repeated key silently overwrote the first. With `sources:` that REMOVES attribution
        # -- half a document's citations vanish and the guard reports the remainder as
        # complete. Removing evidence is the worst thing this parser could do quietly.
        if key in fm:
            raise Unparseable(f"{where}: duplicate key `{key}`; the first would be discarded")
        if raw in (">", ">-", "|", "|-"):
            # YAML block scalars. Excluded at first, which meant this parser could not read
            # Gaia's own SKILL.md -- every skill in this repo writes its `description` this
            # way, so the "strict subset" was strict against the one format it had to accept.
            # Folded (`>`) joins lines with spaces; literal (`|`) keeps the breaks.
            block, j = [], i + 1
            while j < close and (not lines[j].strip() or lines[j].startswith((" ", "\t"))):
                block.append(lines[j].strip() if raw[0] == ">" else lines[j])
                j += 1
            if not block:
                raise Unparseable(f"{where}: `{key}: {raw}` with no indented block beneath it")
            joined = (" ".join(b for b in block if b) if raw[0] == ">"
                      else "\n".join(block).rstrip())
            fm[key] = joined.strip() if raw.endswith("-") else joined
            i = j
            continue
        if not raw:
            fm[key] = []                       # a block list follows, or the key is empty
        elif raw.startswith("{"):
            fm[key] = _inline_map(raw, where)
        elif raw.startswith("["):
            fm[key] = _inline_list(raw, where)
        elif _SCALAR.match(raw) or raw[0] in "\"'":
            fm[key] = _scalar(raw)
        else:
            raise Unparseable(
                f"{where}: `{raw}` is outside the subset (quote it, or use [..] / {{..}})")
        i += 1

    return fm, "\n".join(lines[close + 1:])


def documents(root: Path) -> list[Path]:
    """Every Gaia reference document, from disk rather than a hand-kept list."""
    return sorted(p for p in (root / "references").glob("*.md"))
