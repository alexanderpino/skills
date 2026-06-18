#!/usr/bin/env python3
"""
Resolve [fig:slug] and [tbl:slug] markers in markdown.

Two distinct things happen:

1. Standalone placeholders on their own line (`[fig:slug]\\n`) are anchors
   that the author wrote to mark "the figure goes around here". They have
   no visible role in the output and are *removed*.

2. Inline references in prose ("see [fig:slug]") are replaced with text
   like "Figure 5.2" so the reader knows where to look.

The numbering follows appearance order. The first slug encountered (in any
form) gets number 1, the second gets number 2, and so on.

For the mermaid/image preprocessor, this script also writes a sidecar
file mapping figure-binding info — slug, number, caption — in appearance
order. The preprocessor pairs that with the mermaid blocks it finds.
"""

import re
import sys
import json
from pathlib import Path


def resolve(md_text: str, chapter_num: int,
            captions: dict[str, dict | str]) -> tuple[str, list[dict]]:
    """captions accepts either:
       - {slug: "caption text"}     (legacy flat form)
       - {slug: {"caption": "...", "type": "mermaid|ascii|table|image"}}
                                    (preferred form, lets the figure
                                    preprocessor know what's what)
    """
    fig_counter = 0
    tbl_counter = 0
    fig_seen: dict[str, int] = {}
    tbl_seen: dict[str, int] = {}
    figure_bindings: list[dict] = []

    def get_caption(slug: str) -> str:
        c = captions.get(slug, '')
        return c['caption'] if isinstance(c, dict) else c

    def get_type(slug: str) -> str:
        c = captions.get(slug, '')
        return c.get('type', 'unknown') if isinstance(c, dict) else 'unknown'

    pattern = re.compile(r'\[(fig|tbl):([a-z0-9-]+)\]')

    # Walk in document order to build numbering.
    for m in pattern.finditer(md_text):
        kind, slug = m.group(1), m.group(2)
        if kind == 'fig' and slug not in fig_seen:
            fig_counter += 1
            fig_seen[slug] = fig_counter
            figure_bindings.append({
                "slug": slug,
                "number": fig_counter,
                "caption": get_caption(slug),
                "label": f"Figure {chapter_num}.{fig_counter}",
                "type": get_type(slug),
            })
        elif kind == 'tbl' and slug not in tbl_seen:
            tbl_counter += 1
            tbl_seen[slug] = tbl_counter

    # Strip standalone [fig:slug] placeholders — they're anchors only.
    # Mermaid blocks render their own captions via the bindings sidecar.
    md_text = re.sub(
        r'\n\n\[fig:[a-z0-9-]+\]\n\n', '\n\n', md_text
    )
    md_text = re.sub(r'^\[fig:[a-z0-9-]+\]\n+', '', md_text)

    # Standalone [tbl:slug] placeholders are replaced with the caption
    # printed above the table that follows. (Markdown table caption goes
    # above by convention, opposite to figures.)
    def replace_table_anchor(m):
        slug = m.group(1)
        num = tbl_seen.get(slug, '?')
        caption = get_caption(slug)
        label = f"Table {chapter_num}.{num}"
        # Add LaTeX vspace above to give the table room from the prose.
        spacing = "\n\n```{=latex}\n\\vspace{1em}\n```\n"
        if caption:
            return f"{spacing}**{label}**: {caption}\n"
        return f"{spacing}**{label}**\n"

    md_text = re.sub(
        r'\n\n\[tbl:([a-z0-9-]+)\]\n\n',
        lambda m: '\n\n' + replace_table_anchor(m).lstrip('\n') + '\n',
        md_text
    )

    # Replace remaining (inline) placeholders with text refs.
    def replace_inline(m):
        kind, slug = m.group(1), m.group(2)
        if kind == 'fig':
            num = fig_seen.get(slug, '?')
            return f"Figure {chapter_num}.{num}"
        else:
            num = tbl_seen.get(slug, '?')
            return f"Table {chapter_num}.{num}"
    md_text = pattern.sub(replace_inline, md_text)

    return md_text, figure_bindings


def main():
    if len(sys.argv) < 4:
        print("usage: resolve_placeholders.py <input.md> <output.md> "
              "<chapter_num> [<captions.json>]")
        sys.exit(1)

    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    chapter_num = int(sys.argv[3])
    captions_path = Path(sys.argv[4]) if len(sys.argv) > 4 else None

    captions = {}
    if captions_path and captions_path.exists():
        captions = json.loads(captions_path.read_text())

    md = in_path.read_text(encoding='utf-8')
    resolved, bindings = resolve(md, chapter_num, captions)
    out_path.write_text(resolved, encoding='utf-8')

    # Sidecar binding file consumed by preprocess_mermaid.py.
    bindings_path = out_path.parent / (out_path.stem + '.bindings.json')
    bindings_path.write_text(json.dumps(bindings, indent=2))

    print(f"Wrote {out_path}", file=sys.stderr)
    print(f"Wrote {bindings_path}", file=sys.stderr)
    for b in bindings:
        print(f"  {b['label']}: {b['slug']}", file=sys.stderr)


if __name__ == '__main__':
    main()
