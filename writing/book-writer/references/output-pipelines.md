# Output pipelines — markdown to docx and PDF

The book is drafted in markdown. For most projects markdown is also the deliverable. But many projects need to produce docx (for editors, publishers, Word users) or PDF (for review copies, print-on-demand, beta distribution). This file gives concrete, runnable scripts for both.

Read at Phase 6 (Assembly) when the user has specified docx or PDF as an output format.

**Templates and scripts.** The skill ships with three working files in its `templates/` directory:
- `templates/book-template.tex` — pandoc LaTeX template for book-style PDF output (7×10 trim, running headers, deep section numbering, code-listing styling)
- `templates/resolve_placeholders.py` — replaces `[fig:slug]` and `[tbl:slug]` markers with numbered captions
- `templates/preprocess_mermaid.py` — renders mermaid diagrams via graphviz when the official mermaid-filter isn't available

Copy these into your book project at intake when output formatting matters; modify the LaTeX template per book if needed.

---

## The three routes

| Route | docx | PDF | Setup cost | Output quality |
|---|---|---|---|---|
| A — Pandoc | excellent | good (via LaTeX backend) | medium (needs LaTeX for PDF) | very good |
| B — Pure Python | good (python-docx) | poor-medium (reportlab) | low | docx good, PDF inferior |
| C — Pandoc + custom LaTeX template | excellent | excellent | high (LaTeX template work) | publication-grade |

For most projects: **Route A**. For projects with demanding typography (textbooks, technical treatises with many figures, anything with strong format requirements): **Route C**. Route B is the fallback when LaTeX isn't available and docx is acceptable but PDF quality can be lower.

---

## Route A — Pandoc

Pandoc (https://pandoc.org) is the lingua franca of document conversion. One command takes a markdown file (or many) and produces docx, PDF, EPUB, HTML, LaTeX, and more.

### Prerequisites

```bash
# pandoc itself
sudo apt install pandoc          # Debian/Ubuntu
brew install pandoc              # macOS

# For PDF output (LaTeX backend):
sudo apt install texlive-xetex texlive-fonts-recommended texlive-latex-extra
brew install --cask mactex       # macOS

# For mermaid diagrams in PDF/docx, install mermaid-filter:
npm install -g mermaid-filter
```

### Markdown to docx

The simplest case:

```bash
pandoc -o book.docx \
  --toc --toc-depth=2 \
  --number-sections \
  --reference-doc=template.docx \
  -F mermaid-filter \
  preface.md chapter-01.md chapter-02.md ...
```

What each flag does:
- `-o book.docx` — output file
- `--toc --toc-depth=2` — generate a table of contents using H1 and H2 headings
- `--number-sections` — auto-number sections
- `--reference-doc=template.docx` — use a template Word document for styles (heading styles, body text, code blocks). Generate one with `pandoc -o template.docx --print-default-data-file reference.docx` and customise it in Word.
- `-F mermaid-filter` — convert mermaid code blocks to images
- The chapter files are passed in order; pandoc concatenates them.

A Python wrapper that picks up files automatically:

```python
# Listing — assemble_docx.py
import subprocess
from pathlib import Path

def assemble_docx(book_dir: Path, output_path: Path,
                  template: Path | None = None) -> None:
    """Assemble all chapters into a single docx file."""
    chapter_files = sorted(book_dir.glob("chapters/*.md"))

    cmd = [
        "pandoc",
        "-o", str(output_path),
        "--toc", "--toc-depth=2",
        "--number-sections",
        "-F", "mermaid-filter",
    ]
    if template and template.exists():
        cmd.extend(["--reference-doc", str(template)])

    # Frontmatter (preface, foreword) before chapters; appendices after.
    front = sorted(book_dir.glob("front/*.md"))
    back = sorted(book_dir.glob("back/*.md"))
    cmd.extend(str(p) for p in (*front, *chapter_files, *back))

    subprocess.run(cmd, check=True)
    print(f"Wrote {output_path}")

if __name__ == "__main__":
    import sys
    book = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else book / "book.docx"
    template = book / "template.docx"
    assemble_docx(book, out, template if template.exists() else None)
```

Usage:

```bash
python assemble_docx.py /path/to/book book.docx
```

### Markdown to PDF

Same pandoc tool, different output flag plus a PDF engine. For book-style output, `xelatex` with a serious LaTeX template gives the best results:

```bash
pandoc -o book.pdf \
  --toc --toc-depth=2 \
  --number-sections \
  --pdf-engine=xelatex \
  -V documentclass=book \
  -V papersize=a4 \
  -V mainfont="EB Garamond" \
  -V monofont="JetBrains Mono" \
  -V fontsize=11pt \
  -V geometry:margin=2.5cm \
  -F mermaid-filter \
  preface.md chapter-01.md chapter-02.md ...
```

What's different from the docx call:
- `--pdf-engine=xelatex` — use XeLaTeX (handles modern fonts and Unicode properly)
- `-V documentclass=book` — pass the LaTeX `book` document class (gives chapters real chapter starts, recto/verso awareness, etc.)
- `-V mainfont` and `-V monofont` — specify fonts (EB Garamond is a free serif suitable for book bodies; JetBrains Mono is a free monospace good for code)
- `-V geometry:margin=2.5cm` — set page margins

A Python wrapper for PDF assembly:

```python
# Listing — assemble_pdf.py
import subprocess
from pathlib import Path
from dataclasses import dataclass

@dataclass
class PDFConfig:
    document_class: str = "book"          # book | report | article
    paper_size: str = "a4"                # a4 | letter | b5
    main_font: str = "EB Garamond"
    mono_font: str = "JetBrains Mono"
    font_size: str = "11pt"
    margin: str = "2.5cm"
    toc: bool = True
    number_sections: bool = True

def assemble_pdf(book_dir: Path, output_path: Path,
                 config: PDFConfig = PDFConfig()) -> None:
    """Assemble all chapters into a single PDF via pandoc + xelatex."""
    chapter_files = sorted(book_dir.glob("chapters/*.md"))
    front = sorted(book_dir.glob("front/*.md"))
    back = sorted(book_dir.glob("back/*.md"))

    cmd = [
        "pandoc",
        "-o", str(output_path),
        "--pdf-engine=xelatex",
        "-F", "mermaid-filter",
        "-V", f"documentclass={config.document_class}",
        "-V", f"papersize={config.paper_size}",
        "-V", f"mainfont={config.main_font}",
        "-V", f"monofont={config.mono_font}",
        "-V", f"fontsize={config.font_size}",
        "-V", f"geometry:margin={config.margin}",
    ]
    if config.toc:
        cmd.extend(["--toc", "--toc-depth=2"])
    if config.number_sections:
        cmd.append("--number-sections")

    cmd.extend(str(p) for p in (*front, *chapter_files, *back))

    subprocess.run(cmd, check=True)
    print(f"Wrote {output_path}")

if __name__ == "__main__":
    import sys
    book = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else book / "book.pdf"
    assemble_pdf(book, out)
```

Usage:

```bash
python assemble_pdf.py /path/to/book book.pdf
```

### Customising via metadata

Pandoc reads YAML metadata from a `metadata.yaml` file (or from frontmatter in the first markdown file). For a book project, a `metadata.yaml` at the book root:

```yaml
---
title: "Building an Engine"
subtitle: "A Practitioner's Architectural Treatise"
author:
  - Saskia Vermeer
  - Alexander Pino
date: 2026
publisher: ""
rights: "© 2026 Saskia Vermeer & Alexander Pino"
abstract: |
  This volume covers the design and implementation of a near-AAA-grade
  game engine in C++23, from int main() through to a working frame
  pipeline. ...
toc-title: "Contents"
links-as-notes: true
documentclass: book
classoption:
  - openright
  - twoside
---
```

Pass with `--metadata-file=metadata.yaml`. Pandoc weaves these into the title page and document settings.

---

## Route B — Pure Python (when LaTeX isn't available)

If LaTeX can't be installed (locked-down environment, want a self-contained pipeline), python-docx handles docx well. For PDF, the route is markdown → docx → libreoffice convert.

### Markdown to docx via python-docx

For complex book layouts (custom heading styles, captions on figures, footnotes), python-docx gives full control. The docx skill (`/mnt/skills/public/docx/SKILL.md`) is the reference for usage. A book-assembly script combines that with a chapter-walker:

```python
# Listing — pure_python_docx_assembly.py
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_BREAK
import re
from pathlib import Path

def md_to_docx(book_dir: Path, output_path: Path) -> None:
    """Pure-Python markdown to docx assembly. Limited markdown support;
    suitable when chapters are mostly prose with code blocks and headings."""
    doc = Document()

    # Style up the body text and headings (see docx skill for details)
    body = doc.styles['Normal']
    body.font.name = 'Garamond'
    body.font.size = Pt(11)

    chapter_files = sorted(book_dir.glob("chapters/*.md"))

    for i, chap_file in enumerate(chapter_files):
        if i > 0:
            doc.add_page_break()

        text = chap_file.read_text(encoding='utf-8')
        # Strip YAML frontmatter
        text = re.sub(r'^---\n.*?\n---\n', '', text, count=1, flags=re.DOTALL)

        for line in text.splitlines():
            if line.startswith('# '):
                doc.add_heading(line[2:], level=1)
            elif line.startswith('## '):
                doc.add_heading(line[3:], level=2)
            elif line.startswith('### '):
                doc.add_heading(line[4:], level=3)
            elif line.startswith('```'):
                # Skip code block fences; collect lines until closing fence.
                # (Real implementation should preserve as styled paragraphs.)
                continue
            elif line.strip():
                doc.add_paragraph(line)
            else:
                doc.add_paragraph()

    doc.save(str(output_path))
    print(f"Wrote {output_path}")
```

This is a sketch — production-quality docx assembly via python-docx requires more work, especially for code blocks (need a monospace style and shading), captions, and the table of contents (which docx supports via field codes).

For most projects pandoc is the better answer; this route is the fallback.

### Markdown to PDF via docx + libreoffice

If you have LibreOffice installed (most Linux servers do, headless), you can convert docx to PDF without LaTeX:

```python
# Listing — docx_to_pdf_via_libreoffice.py
import subprocess
from pathlib import Path

def docx_to_pdf(docx_path: Path, output_dir: Path | None = None) -> Path:
    """Convert docx to PDF using LibreOffice headless mode."""
    if output_dir is None:
        output_dir = docx_path.parent

    subprocess.run([
        'libreoffice', '--headless',
        '--convert-to', 'pdf',
        '--outdir', str(output_dir),
        str(docx_path)
    ], check=True)

    pdf_path = output_dir / docx_path.with_suffix('.pdf').name
    return pdf_path
```

Quality is decent for most uses. Code blocks render correctly; figures render. Typography is not as good as LaTeX, kerning is rougher, hyphenation is weaker. For review copies and beta distribution, fine. For a printed book, route A or C.

---

## Route C — Pandoc with custom LaTeX template

For projects that need publication-grade typography, write a LaTeX template that pandoc uses as the body of the document. This is the route used for serious technical books where typography matters.

### Generating a starter template

```bash
pandoc -D latex > book-template.tex
```

This writes pandoc's default LaTeX template, which is a starting point. Edit it to:
- Customise the chapter-opening style
- Set font choices and sizes throughout
- Add running headers and footers
- Set up code-listing styling (using `listings` or `minted` packages)
- Configure figure and table captioning style
- Add custom front matter (title page, copyright page, dedication)

Once you have a template, point pandoc at it:

```bash
pandoc -o book.pdf \
  --pdf-engine=xelatex \
  --template=book-template.tex \
  --metadata-file=metadata.yaml \
  -F mermaid-filter \
  preface.md chapter-*.md
```

Custom templates are real work — typically a day or two of LaTeX time for a book — but they're reusable across projects and the typography quality is what publishers expect.

### Useful LaTeX packages for technical books

In the template's preamble, these packages help:

```latex
\usepackage{microtype}      % Better justification, kerning
\usepackage{listings}        % Code listings with syntax highlighting
\usepackage{tikz}            % Vector diagrams (alternative to mermaid)
\usepackage{booktabs}        % Better table rules
\usepackage{caption}         % Custom caption styling
\usepackage{fancyhdr}        % Running headers/footers
\usepackage{titlesec}        % Custom chapter and section titles
\usepackage{xurl}            % Better URL line-breaking
```

For mermaid diagrams that pandoc has converted to SVG, you may need `\usepackage{svg}` and the system `inkscape` tool for inclusion in LaTeX.

---

## The complete preprocessing pipeline

Pandoc on its own does not handle three things that a real book needs:

1. **Placeholder resolution.** The skill produces markdown with `[fig:slug]` and `[tbl:slug]` markers during writing. These need to be replaced with numbered captions ("Figure 5.2: …", "Table 5.1: …") before pandoc sees them.
2. **Mermaid diagram rendering.** Mermaid blocks need to be converted to vector images (PDF for xelatex, PNG for docx) before pandoc embeds them.
3. **Citation resolution.** `[src:N]` markers in the prose need to be expanded into the chosen citation style.

The pipeline order matters: placeholder resolution first (so the figure/table numbering reflects appearance order), then mermaid rendering (so figures have actual content), then citation resolution, then pandoc.

A complete shell pipeline:

```bash
# Step 1 — Resolve [fig:slug] and [tbl:slug] placeholders
python3 resolve_placeholders.py chapter.md chapter-step1.md 5 captions.json

# Step 2 — Render mermaid blocks to SVG, convert to PDF for xelatex
python3 preprocess_mermaid.py chapter-step1.md chapter-step2.md figures
python3 -c "
import cairosvg, glob
for svg in glob.glob('figures/*.svg'):
    cairosvg.svg2pdf(url=svg, write_to=svg.replace('.svg', '.pdf'))
"
sed -i 's|\.svg)|\.pdf)|g' chapter-step2.md  # for xelatex; keep .svg for docx

# Step 3 — Resolve citations (when sources_used is non-empty)
# python3 resolve_citations.py chapter-step2.md chapter-step3.md sources.json

# Step 4 — Pandoc with the book template
pandoc -o chapter.pdf \
  --pdf-engine=xelatex \
  --template=book-template.tex \
  --resource-path=. \
  --metadata title="<book title>" \
  --metadata author="<author name>" \
  --metadata chapter-start=<N-1> \
  --top-level-division=chapter \
  --highlight-style=tango \
  chapter-step2.md
```

The three preprocessor scripts (`resolve_placeholders.py`, `preprocess_mermaid.py`, optional `resolve_citations.py`) belong in the book project's tooling directory. They are small (~50–150 lines each).

### resolve_placeholders.py

Reads markdown, finds `[fig:slug]` and `[tbl:slug]` markers, replaces them with `**Figure N.M**: <caption>` and `**Table N.M**: <caption>` based on appearance order and a captions JSON file. The captions file maps slugs to caption text:

```json
{
  "archetype-storage-layout": "Memory layout for an archetype with three component types.",
  "query-iteration": "A query for <Position, Velocity> against four archetypes."
}
```

Numbering is per-chapter. The caller passes the chapter number explicitly.

### preprocess_mermaid.py

Reads markdown, finds ` ```mermaid ` blocks, converts them to graphviz dot, renders to SVG. Replaces the block in the markdown with an image link.

This is a fallback for environments where the official `mermaid-filter` (npm package, requires Chromium via Puppeteer) is not available. The graphviz-based version supports a subset of mermaid: `graph LR`, `graph TB`, basic node/edge syntax, simple styling. For complex mermaid diagrams (sequence, state, gantt) the official mermaid CLI (`mmdc`) with Chromium is needed.

### Captions data — figures.json

The skill already produces `figures.json` during writing (Phase 4 step 3 — figure placeholder registration). Extend this file to include captions:

```json
{
  "archetype-storage-layout": {
    "type": "diagram",
    "caption": "Memory layout for an archetype with three component types.",
    "appears_in_chapter": 5,
    "source": "ascii-art"
  },
  "query-iteration": {
    "type": "diagram",
    "caption": "A query for <Position, Velocity> against four archetypes.",
    "appears_in_chapter": 5,
    "source": "mermaid"
  }
}
```

The placeholder-resolver reads this file and uses the `caption` field.

---

## The book-template.tex — making it look like a book

Pandoc's default LaTeX output produces document-style PDFs: A4, wide margins, single-sided, no running headers. For a book to look like a real book, a custom template is required. The template handles:

- **Trim size and margins.** 7"×10" (crown quarto) is a common book size; 6"×9" (US trade) is smaller. Tighter margins than document defaults; outer wider than inner to leave room for marginalia.
- **Body and code fonts.** A real book serif (TeX Gyre Pagella, EB Garamond, Linux Libertine) for body text; a clean monospace (DejaVu Sans Mono, JetBrains Mono) for code.
- **Running headers and footers.** Verso pages (even): chapter title left, page number left. Recto pages (odd): section title right, page number right.
- **Section numbering depth.** The default `book` class shows three levels (chapter, section, subsection); extending to four (`secnumdepth=4`) allows references like "5.6.4.2".
- **Indented paragraphs.** Books indent paragraphs and remove blank lines between them; documents do the opposite.
- **Code block styling.** Lighter background shading, smaller font, tighter spacing than pandoc default.
- **Chapter counter override.** When rendering a single chapter for review, the chapter number should still match the book's chapter number, not start at 1.

A working `book-template.tex` is included in the skill's templates directory (or copied into the book project at intake). The template uses pandoc's variable substitution, so it integrates cleanly with `pandoc --template=book-template.tex`.

Key features of the template:

```latex
% 7x10 trim, twoside, openright (chapters start on recto)
\documentclass[10pt,twoside,openright]{book}

% Boek-typography geometry
\usepackage[
    paperwidth=7in, paperheight=10in,
    inner=0.85in, outer=1.0in,
    top=0.85in, bottom=0.85in,
    headsep=0.25in, footskip=0.4in
]{geometry}

% Fonts
\usepackage{fontspec}
\setmainfont{TeX Gyre Pagella}
\setmonofont[Scale=0.85]{DejaVu Sans Mono}

% Running headers
\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhead[LE]{\small\nouppercase{\leftmark}}
\fancyfoot[LE]{\thepage}
\fancyhead[RO]{\small\nouppercase{\rightmark}}
\fancyfoot[RO]{\thepage}

% Section numbering depth (8.6.4.2 levels)
\setcounter{secnumdepth}{4}

% Chapter counter override (for single-chapter previews)
$if(chapter-start)$
\setcounter{chapter}{$chapter-start$}
$endif$
```

The template is around 130 lines total. It is reusable across projects — once configured for a book, it applies to every chapter without modification.

### Picking trim size by genre

| Genre | Recommended trim | Notes |
|---|---|---|
| Trade non-fiction | 6"×9" | Standard for popular non-fiction |
| Technical treatise / textbook | 7"×10" | Crown quarto; room for code listings |
| O'Reilly-style programming book | 7"×9.25" | Industry standard for technical |
| Mass-market paperback | 4.25"×7" | For fiction at impulse-purchase price |
| Literary fiction (hardcover) | 6"×9" | Standard for prestige fiction |
| Reference / dictionary | 6"×9" or larger | Two-column layouts possible |

The trim size is a `\usepackage[paperwidth=…,paperheight=…]{geometry}` change in the template. Other typography choices (margins, fonts, header styles) follow from it.

---

## Choosing per-project



When the user reaches Phase 6 (Assembly), pick the route based on:

- **Quick draft, beta readers, internal review**: Route A (pandoc) or Route B (python + libreoffice). Fast, good enough.
- **Final delivery to a publisher accepting docx**: Route A is the default. The publisher's editor will style their own way.
- **Self-published book to a print-on-demand service**: Route C if you have time, Route A if you don't. The PDF quality difference will be visible on a printed page but may not matter for a first edition.
- **Academic monograph or technical treatise**: Route C. The audience expects publication-grade typography, and LaTeX with a custom template delivers it.

Document the choice in `project.json`:

```json
"output": {
  "format": "pdf",
  "pipeline": "pandoc-xelatex",
  "template": "book-template.tex",
  "fonts": {
    "main": "EB Garamond",
    "mono": "JetBrains Mono",
    "sans": "Source Sans Pro"
  }
}
```

The pipeline is then reproducible across sessions.

---

## What lives in the book project

For a project using Route A or C, expected files in the book directory:

```
book-name/
├── chapters/
│   ├── 01-introduction.md
│   ├── 02-foundations.md
│   └── ...
├── front/
│   ├── 00-title.md
│   ├── 01-preface.md
│   └── 02-introduction.md
├── back/
│   ├── 90-glossary.md
│   ├── 91-bibliography.md
│   └── 92-index.md
├── figures/
│   ├── architecture-diagram.svg
│   └── ...
├── metadata.yaml
├── template.docx           # for Route A docx output
├── book-template.tex       # for Route C PDF output
├── assemble_docx.py
├── assemble_pdf.py
└── project.json
```

Run the assembly scripts at the project root. Output goes to a `dist/` directory by convention (or wherever the user specifies).

---

## A note on incremental assembly

For long projects, full assembly takes time (LaTeX especially). During development, build only the chapters being worked on:

```bash
pandoc -o preview.pdf --pdf-engine=xelatex \
  -V documentclass=article \
  chapters/05-building-the-ecs.md
```

Use `documentclass=article` instead of `book` for single-chapter previews. The output is a quick PDF for reviewing layout and typography of the chapter under work.

This is the recommended workflow during writing: full book assembly only at milestone moments (end of part, end of book), single-chapter preview during day-to-day editing.
