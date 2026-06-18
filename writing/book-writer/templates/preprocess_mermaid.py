#!/usr/bin/env python3
"""
Vervang mermaid blocks in markdown door graphviz-gegenereerde SVG-images.

Beperkt tot de subset van mermaid die in deze test voorkomt:
- graph LR (left-to-right)
- graph TB (top-to-bottom)
- Nodes met labels
- Edges met of zonder labels
- Solid en dotted edges
- Style declaraties (fill, stroke-dasharray) — best-effort vertaald

Voor productie zou een vollediger mermaid → dot translator nodig zijn,
of een echte mermaid CLI met Chromium. Dit dekt onze testcase.
"""

import re
import sys
import json
from pathlib import Path
import graphviz


def parse_mermaid_block(content: str):
    """Parse een mermaid graph block en return een graphviz Digraph."""
    lines = [ln.strip() for ln in content.strip().splitlines() if ln.strip()]
    if not lines:
        return None

    direction_line = lines[0]
    if direction_line.startswith('graph LR'):
        rankdir = 'LR'
    elif direction_line.startswith('graph TB') or direction_line.startswith('graph TD'):
        rankdir = 'TB'
    else:
        return None  # ander type diagram, niet ondersteund in deze test

    g = graphviz.Digraph()
    g.attr(rankdir=rankdir)
    g.attr('node', shape='box', style='rounded,filled', fillcolor='white',
           fontname='Helvetica', fontsize='10')
    g.attr('edge', fontname='Helvetica', fontsize='9')

    # Houd node-styles bij
    node_styles = {}

    # Patterns
    # Node met label: A1["label"] of Q[label]
    node_re = re.compile(r'^(\w+)\["?([^"\]]*?)"?\]$')
    # Edge met label: A -->|label| B  of  A -. label .-> B
    edge_solid_label_re = re.compile(r'^(\w+)\s*-->\|\s*([^|]+?)\s*\|\s*(\w+)$')
    edge_dotted_label_re = re.compile(r'^(\w+)\s*-\.\s*([^.]+?)\s*\.->\s*(\w+)$')
    edge_solid_re = re.compile(r'^(\w+)\s*-->\s*(\w+)$')
    edge_dotted_re = re.compile(r'^(\w+)\s*-\.->\s*(\w+)$')
    # Style: style A1 fill:#a8e6a3
    style_re = re.compile(r'^style\s+(\w+)\s+(.+)$')

    seen_nodes = set()
    edges = []  # buffer; nodes komen voor edges in de output

    for line in lines[1:]:
        m = node_re.match(line)
        if m:
            node_id, label = m.group(1), m.group(2)
            # Vervang mermaid HTML entities
            label = (label.replace('&lt;', '<').replace('&gt;', '>')
                          .replace('<br/>', r'\n').replace('<br>', r'\n'))
            node_styles.setdefault(node_id, {})['label'] = label
            seen_nodes.add(node_id)
            continue

        m = style_re.match(line)
        if m:
            node_id, style_str = m.group(1), m.group(2)
            ns = node_styles.setdefault(node_id, {})
            for part in style_str.split(','):
                part = part.strip()
                if part.startswith('fill:'):
                    ns['fillcolor'] = part.split(':', 1)[1].strip()
                elif 'stroke-dasharray' in part:
                    ns['style'] = 'dashed,filled'
            continue

        m = edge_solid_label_re.match(line)
        if m:
            edges.append((m.group(1), m.group(3), m.group(2), 'solid'))
            seen_nodes.update([m.group(1), m.group(3)])
            continue

        m = edge_dotted_label_re.match(line)
        if m:
            edges.append((m.group(1), m.group(3), m.group(2), 'dashed'))
            seen_nodes.update([m.group(1), m.group(3)])
            continue

        m = edge_solid_re.match(line)
        if m:
            edges.append((m.group(1), m.group(2), '', 'solid'))
            seen_nodes.update([m.group(1), m.group(2)])
            continue

        m = edge_dotted_re.match(line)
        if m:
            edges.append((m.group(1), m.group(2), '', 'dashed'))
            seen_nodes.update([m.group(1), m.group(2)])
            continue

    # Render nodes
    for nid in seen_nodes:
        s = node_styles.get(nid, {})
        kwargs = {}
        if 'label' in s:
            kwargs['label'] = s['label']
        else:
            kwargs['label'] = nid
        if 'fillcolor' in s:
            kwargs['fillcolor'] = s['fillcolor']
        if 'style' in s:
            kwargs['style'] = s['style']
        else:
            kwargs['style'] = 'rounded,filled'
        g.node(nid, **kwargs)

    # Render edges
    for src, dst, label, style in edges:
        kwargs = {}
        if label:
            kwargs['label'] = label
        if style == 'dashed':
            kwargs['style'] = 'dashed'
        g.edge(src, dst, **kwargs)

    return g


def preprocess_markdown(md_text: str, output_dir: Path,
                        bindings: list[dict] | None = None,
                        prefix: str = 'fig') -> str:
    """Vervang mermaid blocks in markdown door image references.

    If bindings is provided, each successive mermaid block is paired with
    the next entry in bindings — the entry's label and caption are placed
    under the image (typeset together as a unit so they don't separate
    across page breaks).

    If bindings is None or runs out, mermaid blocks are rendered as plain
    centred images without captions.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    bindings = bindings or []

    pattern = re.compile(r'```mermaid\n(.*?)\n```', re.DOTALL)
    counter = [0]
    binding_idx = [0]

    def replace(match):
        counter[0] += 1
        block = match.group(1)
        g = parse_mermaid_block(block)
        if g is None:
            print(f"  warn: kon mermaid block #{counter[0]} niet parsen, "
                  f"laat als-is", file=sys.stderr)
            return match.group(0)

        out_base = output_dir / f"{prefix}-{counter[0]:02d}"
        try:
            g.render(str(out_base), format='svg', cleanup=True)
            svg_path = out_base.with_suffix('.svg')
            print(f"  rendered {svg_path}", file=sys.stderr)
        except Exception as e:
            print(f"  err: render mislukt voor block #{counter[0]}: {e}",
                  file=sys.stderr)
            return match.group(0)

        # Look up the next binding (if any) for caption.
        binding = None
        if binding_idx[0] < len(bindings):
            binding = bindings[binding_idx[0]]
            binding_idx[0] += 1

        if binding:
            caption_text = (
                f"**{binding['label']}**: {binding['caption']}"
                if binding.get('caption')
                else f"**{binding['label']}**"
            )
            # Wrap image and caption in a centred minipage so they stay
            # together across page breaks. Vspace before and after for
            # breathing room from surrounding prose.
            return (
                f"\n\n```{{=latex}}\n"
                f"\\vspace{{1.4em}}\n"
                f"\\begin{{minipage}}{{\\linewidth}}\n"
                f"\\centering\n"
                f"```\n"
                f"![]({svg_path})\n\n"
                f"{caption_text}\n"
                f"```{{=latex}}\n"
                f"\\end{{minipage}}\n"
                f"\\vspace{{1.4em}}\n"
                f"```\n\n"
            )
        else:
            # No binding — plain centred image with breathing room.
            return (
                f"\n\n```{{=latex}}\n"
                f"\\vspace{{1.4em}}\\begin{{center}}\n"
                f"```\n"
                f"![]({svg_path})\n"
                f"```{{=latex}}\n"
                f"\\end{{center}}\\vspace{{1.4em}}\n"
                f"```\n\n"
            )

    return pattern.sub(replace, md_text)


def main():
    if len(sys.argv) < 3:
        print("usage: preprocess_mermaid.py <input.md> <output.md> "
              "[<figures-dir>] [<bindings.json>]")
        sys.exit(1)

    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    fig_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else out_path.parent / 'figures'
    bindings_path = Path(sys.argv[4]) if len(sys.argv) > 4 else None

    bindings = []
    if bindings_path is None:
        # Try sidecar from resolve_placeholders.py
        candidate = in_path.parent / (in_path.stem + '.bindings.json')
        if candidate.exists():
            bindings_path = candidate

    if bindings_path and bindings_path.exists():
        all_bindings = json.loads(bindings_path.read_text())
        # Only mermaid-type bindings are paired with mermaid blocks.
        # Other figure types (ascii, image, table) handle their own captions.
        bindings = [b for b in all_bindings if b.get('type') == 'mermaid']
        print(f"Loaded {len(bindings)} mermaid bindings from "
              f"{bindings_path}", file=sys.stderr)

    md = in_path.read_text(encoding='utf-8')
    processed = preprocess_markdown(md, fig_dir, bindings)
    out_path.write_text(processed, encoding='utf-8')
    print(f"Wrote {out_path}", file=sys.stderr)


if __name__ == '__main__':
    main()
