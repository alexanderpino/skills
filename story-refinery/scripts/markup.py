"""Convert the rendered markdown into what a tracker will actually accept.

Without this, a Jira Cloud description shows literal asterisks and a Server
description shows literal hashes. Supported targets:

  markdown   passthrough
  wiki       Jira Server / Data Center wiki markup
  adf        Atlassian Document Format, core nodes only [?]
  html       minimal, for Azure DevOps [?]
  plaintext  markers stripped, safe everywhere

ADF caveat, stated plainly: only doc, heading, paragraph, bulletList, codeBlock,
blockquote and rule are emitted. Markdown tables are flattened to bullet lists
because ADF table cell nesting is easy to get subtly wrong and a malformed table
node is rejected for the whole document. Verify against a live instance before
relying on it.
"""

import re

__all__ = ["render_markup", "to_wiki", "to_adf", "to_html", "to_plaintext"]

BOLD = re.compile(r"\*\*(.+?)\*\*")
CODE = re.compile(r"`([^`]+)`")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET = re.compile(r"^(\s*)[-*]\s+(.*)$")
TABLE_SEP = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
RULE = re.compile(r"^\s*(-{3,}|_{3,})\s*$")


def _blocks(md):
    """Split markdown into (kind, payload) blocks. kind in:
    heading, para, bullets, code, quote, rule, table."""
    lines = md.splitlines()
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            lang = line.strip()[3:].strip()
            body, i = [], i + 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                body.append(lines[i])
                i += 1
            i += 1
            out.append(("code", (lang, "\n".join(body))))
            continue
        if not line.strip():
            i += 1
            continue
        m = HEADING.match(line)
        if m:
            out.append(("heading", (len(m.group(1)), m.group(2).strip())))
            i += 1
            continue
        if RULE.match(line):
            out.append(("rule", None))
            i += 1
            continue
        if line.lstrip().startswith(">"):
            body = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                body.append(lines[i].lstrip()[1:].strip())
                i += 1
            out.append(("quote", " ".join(body)))
            continue
        if line.lstrip().startswith("|"):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                if not TABLE_SEP.match(lines[i]):
                    cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                    rows.append(cells)
                i += 1
            out.append(("table", rows))
            continue
        if BULLET.match(line):
            items = []
            while i < len(lines) and BULLET.match(lines[i]):
                m = BULLET.match(lines[i])
                items.append((len(m.group(1)) // 2, m.group(2)))
                i += 1
            out.append(("bullets", items))
            continue
        body = []
        while i < len(lines) and lines[i].strip() and not HEADING.match(lines[i]) \
                and not BULLET.match(lines[i]) and not RULE.match(lines[i]) \
                and not lines[i].lstrip().startswith(("|", ">", "```")):
            body.append(lines[i].strip())
            i += 1
        out.append(("para", " ".join(body)))
    return out


# ------------------------------------------------------------------------ wiki

def _inline_wiki(text):
    text = CODE.sub(lambda m: "{{%s}}" % m.group(1), text)
    return BOLD.sub(lambda m: "*%s*" % m.group(1), text)


def to_wiki(md):
    out = []
    for kind, payload in _blocks(md):
        if kind == "heading":
            level, text = payload
            out.append("h%d. %s" % (min(level, 6), _inline_wiki(text)))
        elif kind == "para":
            out.append(_inline_wiki(payload))
        elif kind == "bullets":
            out += ["%s %s" % ("*" * (depth + 1), _inline_wiki(t)) for depth, t in payload]
        elif kind == "code":
            lang, body = payload
            out.append("{code%s}\n%s\n{code}" % (":" + lang if lang else "", body))
        elif kind == "quote":
            out.append("bq. %s" % _inline_wiki(payload))
        elif kind == "rule":
            out.append("----")
        elif kind == "table":
            for idx, row in enumerate(payload):
                bar = "||" if idx == 0 else "|"
                out.append(bar + bar.join(_inline_wiki(c) for c in row) + bar)
        out.append("")
    return "\n".join(out).strip() + "\n"


# ------------------------------------------------------------------------- adf

def _inline_adf(text):
    nodes, pos = [], 0
    pattern = re.compile(r"\*\*(.+?)\*\*|`([^`]+)`")
    for m in pattern.finditer(text):
        if m.start() > pos:
            nodes.append({"type": "text", "text": text[pos:m.start()]})
        if m.group(1) is not None:
            nodes.append({"type": "text", "text": m.group(1),
                          "marks": [{"type": "strong"}]})
        else:
            nodes.append({"type": "text", "text": m.group(2),
                          "marks": [{"type": "code"}]})
        pos = m.end()
    if pos < len(text):
        nodes.append({"type": "text", "text": text[pos:]})
    return [n for n in nodes if n.get("text")] or [{"type": "text", "text": " "}]


def _adf_para(text):
    return {"type": "paragraph", "content": _inline_adf(text)}


def to_adf(md):
    content = []
    for kind, payload in _blocks(md):
        if kind == "heading":
            level, text = payload
            content.append({"type": "heading", "attrs": {"level": min(max(level, 1), 6)},
                            "content": _inline_adf(text)})
        elif kind == "para":
            content.append(_adf_para(payload))
        elif kind == "bullets":
            content.append({"type": "bulletList", "content": [
                {"type": "listItem", "content": [_adf_para(t)]} for _, t in payload]})
        elif kind == "code":
            lang, body = payload
            node = {"type": "codeBlock", "content": [{"type": "text", "text": body or " "}]}
            if lang:
                node["attrs"] = {"language": lang}
            content.append(node)
        elif kind == "quote":
            content.append({"type": "blockquote", "content": [_adf_para(payload)]})
        elif kind == "rule":
            content.append({"type": "rule"})
        elif kind == "table":
            # Flattened on purpose - see the module docstring.
            content.append({"type": "bulletList", "content": [
                {"type": "listItem", "content": [_adf_para(" · ".join(row))]}
                for row in payload]})
    return {"version": 1, "type": "doc", "content": content or [_adf_para(" ")]}


# ------------------------------------------------------------------ html/plain

def _esc(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _inline_html(text):
    text = CODE.sub(lambda m: "<code>%s</code>" % _esc(m.group(1)), _esc(text))
    return BOLD.sub(lambda m: "<strong>%s</strong>" % m.group(1), text)


def to_html(md):
    out = []
    for kind, payload in _blocks(md):
        if kind == "heading":
            level, text = payload
            out.append("<h%d>%s</h%d>" % (level, _inline_html(text), level))
        elif kind == "para":
            out.append("<p>%s</p>" % _inline_html(payload))
        elif kind == "bullets":
            out.append("<ul>%s</ul>" % "".join("<li>%s</li>" % _inline_html(t)
                                               for _, t in payload))
        elif kind == "code":
            out.append("<pre><code>%s</code></pre>" % _esc(payload[1]))
        elif kind == "quote":
            out.append("<blockquote>%s</blockquote>" % _inline_html(payload))
        elif kind == "rule":
            out.append("<hr/>")
        elif kind == "table":
            rows = "".join("<tr>%s</tr>" % "".join(
                "<%s>%s</%s>" % ("th" if i == 0 else "td", _inline_html(c),
                                 "th" if i == 0 else "td") for c in row)
                for i, row in enumerate(payload))
            out.append("<table>%s</table>" % rows)
    return "\n".join(out)


def to_plaintext(md):
    out = []
    for kind, payload in _blocks(md):
        strip = lambda t: CODE.sub(r"\1", BOLD.sub(r"\1", t))  # noqa: E731
        if kind == "heading":
            out.append(strip(payload[1]).upper())
        elif kind == "para":
            out.append(strip(payload))
        elif kind == "bullets":
            out += ["  " * d + "- " + strip(t) for d, t in payload]
        elif kind == "code":
            out.append(payload[1])
        elif kind == "quote":
            out.append(strip(payload))
        elif kind == "rule":
            out.append("-" * 40)
        elif kind == "table":
            out += ["  ".join(strip(c) for c in row) for row in payload]
        out.append("")
    return "\n".join(out).strip() + "\n"


def render_markup(md, target):
    return {
        "markdown": lambda t: t,
        "wiki": to_wiki,
        "adf": to_adf,
        "html": to_html,
        "plaintext": to_plaintext,
    }.get(target, lambda t: t)(md)
