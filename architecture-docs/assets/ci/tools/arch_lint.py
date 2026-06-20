#!/usr/bin/env python3
"""
arch_lint.py — Architecture-as-Code validator for the architecture-docs skill.

Pure standard library (Python 3.8+). No third-party dependencies required;
uses PyYAML for front-matter parsing if available, otherwise a built-in parser.

Checks (run a subset or `all`):
  frontmatter  - required fields, allowed status/level values, ADR/RFC id format,
                 supersession links, mandatory Threat-model + FinOps sections in HLD/SAD.
  conformance  - ISO/IEC/IEEE 42010: every concern framed by a known viewpoint,
                 every view governed by exactly one known viewpoint, ≥1 stakeholder/
                 concern/viewpoint/view, ≥1 ADR; conformance-checklist has no ❌.
  drift        - every `ARCH-REF: ADR-NNNN` in --src points to an existing, non-
                 superseded ADR; warns on accepted ADRs that no code references.
  links        - relative markdown links inside the docs root resolve.
  all          - run everything; exit non-zero if any ERROR (or WARNING with --strict).

Usage:
  python arch_lint.py all --root docs/architecture --src src
  python arch_lint.py frontmatter --root docs/architecture --strict
  python arch_lint.py all --emit-frontmatter build/frontmatter.yaml   # for Spectral
"""
from __future__ import annotations
import argparse, glob, os, re, sys

# ---------- result collection ----------
ERROR, WARN, INFO = "ERROR", "WARN", "INFO"
findings = []  # (level, path, msg)
def add(level, path, msg): findings.append((level, os.path.relpath(path), msg))

ALLOWED_STATUS = {"draft", "in-review", "current", "accepted", "proposed",
                  "rejected", "deprecated", "superseded", "withdrawn",
                  "ready", "in-progress", "done"}  # last row: user-story lifecycle
ADR_STATUS = {"proposed", "accepted", "rejected", "deprecated", "superseded"}
ALLOWED_LEVEL = {"enterprise", "solution", "software", "all"}
PLACEHOLDER = re.compile(r"<[^>]+>")

# ---------- house profile (detected conventions; overrides defaults) ----------
def load_house(path):
    if not path or not os.path.exists(path):
        return {}
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(open(path, encoding="utf-8").read()) or {}
        return data.get("types", {}) if isinstance(data, dict) else {}
    except ImportError:
        add(INFO, path, "house profile found but PyYAML not installed; skipping house enforcement")
        return {}
    except Exception as e:
        add(WARN, path, f"could not parse house profile: {e}")
        return {}

def _norm_heading(h):
    h = re.sub(r"^\s*\d+(\.\d+)*[.)]?\s*", "", h).strip()
    h = re.sub(r"\s*\(.*?\)\s*$", "", h).strip()
    return h.lower()

def _body_headings(body):
    out = set()
    for ln in body.splitlines():
        m = re.match(r"^#{2,3}\s+(.*\S)\s*$", ln)
        if m:
            out.add(_norm_heading(m.group(1)))
    return out

# ---------- front-matter parsing ----------
def split_frontmatter(text):
    """Return (frontmatter_dict, body). Tolerates a leading comment block."""
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines[:15]):
        if ln.strip() == "---":
            start = i
            break
    if start is None:
        return {}, text
    end = None
    for j in range(start + 1, len(lines)):
        if lines[j].strip() == "---":
            end = j
            break
    if end is None:
        return {}, text
    fm_raw = "\n".join(lines[start + 1:end])
    body = "\n".join(lines[end + 1:])
    return parse_yaml(fm_raw), body

def parse_yaml(raw):
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return _mini_yaml(raw)

def _strip_comment(v):
    # remove trailing ' # ...' comment when not inside quotes
    out, q = [], None
    i = 0
    while i < len(v):
        c = v[i]
        if q:
            out.append(c)
            if c == q: q = None
        elif c in "\"'":
            q = c; out.append(c)
        elif c == "#" and (i == 0 or v[i-1] == " "):
            break
        else:
            out.append(c)
        i += 1
    return "".join(out).strip()

def _coerce(v):
    v = v.strip()
    if v in ("true", "True"): return True
    if v in ("false", "False"): return False
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        return [x.strip().strip("'\"") for x in inner.split(",")] if inner else []
    return v.strip("'\"")

def _mini_yaml(raw):
    data, lines, i = {}, raw.splitlines(), 0
    key_re = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")
    while i < len(lines):
        ln = lines[i]
        if not ln.strip() or ln.lstrip().startswith("#"):
            i += 1; continue
        if not ln.startswith(" "):  # top-level key
            m = key_re.match(ln)
            if m:
                key, val = m.group(1), _strip_comment(m.group(2))
                if val == "":  # maybe a block list / map follows
                    items, j = [], i + 1
                    while j < len(lines) and (lines[j].startswith(" ") or not lines[j].strip()):
                        s = lines[j].strip()
                        if s.startswith("- "): items.append(s[2:].strip())
                        j += 1
                    data[key] = items if items else ""
                    i = j; continue
                data[key] = _coerce(val)
        i += 1
    return data

# ---------- helpers ----------
def md_files(root):
    return sorted(glob.glob(os.path.join(root, "**", "*.md"), recursive=True))

def doc_kind(path, fm):
    name = os.path.basename(path)
    if name.startswith("ADR-"): return "ADR"
    if name.startswith("RFC-"): return "RFC"
    if name.startswith("US-"): return "US"
    if name.startswith("EP-"): return "EP"
    fid = str(fm.get("id", ""))
    if fid in ("architecture-index", "decision-log"): return "INDEX"
    if fid: return fid.split("-")[0].upper() if fid.startswith(("SD",)) else fid.upper()
    if name.lower() == "readme.md": return "INDEX"
    return name.replace(".md", "").upper()

# ---------- check: frontmatter ----------
def check_frontmatter(root, strict, house=None):
    house = house or {}
    files = md_files(root)
    adr_ids, adr_status, adr_links = {}, {}, {}
    for path in files:
        text = open(path, encoding="utf-8").read()
        fm, body = split_frontmatter(text)
        if not fm:
            # decisions log / plain index without front-matter is tolerated
            add(INFO, path, "no YAML front-matter found")
            continue
        kind = doc_kind(path, fm)
        # required-always (INDEX/manifest docs carry no status)
        required = ("id", "title") if kind == "INDEX" else ("id", "title", "status")
        for req in required:
            if not fm.get(req):
                add(ERROR, path, f"missing required front-matter field: {req}")
        status = str(fm.get("status", "")).strip()
        if status and status not in ALLOWED_STATUS:
            add(ERROR, path, f"invalid status '{status}' (allowed: {sorted(ALLOWED_STATUS)})")
        lvl = str(fm.get("level", "")).strip()
        if kind not in ("INDEX",) and not lvl:
            add(WARN, path, "missing 'level' (enterprise|solution|software)")
        if lvl and lvl not in ALLOWED_LEVEL:
            add(ERROR, path, f"invalid level '{lvl}'")
        if kind not in ("INDEX",) and not (fm.get("updated") or fm.get("date")):
            add(WARN, path, "missing a date field ('updated' or 'date')")
        # unfilled template placeholders
        for k, v in fm.items():
            if isinstance(v, str) and PLACEHOLDER.search(v):
                add(WARN if not strict else ERROR, path, f"unfilled placeholder in '{k}': {v}")
        # house-profile enforcement (detected conventions override built-in defaults)
        hp = house.get(kind)
        if hp:
            for f in hp.get("required_frontmatter", []) or []:
                if f not in fm:
                    add(ERROR, path, f"house style: {kind} requires front-matter field '{f}'")
            present = _body_headings(body)
            for sec in hp.get("mandatory_sections", []) or []:
                if _norm_heading(sec) not in present:
                    add(ERROR, path, f"house style: {kind} must contain section '{sec}'")
        # ADR-specific
        if kind == "ADR":
            m = re.match(r"ADR-(\d{4})-", os.path.basename(path))
            if not m:
                add(ERROR, path, "ADR filename must be ADR-NNNN-slug.md (4-digit)")
            fid = str(fm.get("id", ""))
            if not re.match(r"^ADR-\d{4}$", fid):
                add(ERROR, path, f"ADR id must match ADR-NNNN, got '{fid}'")
            if m and fid and not fid.endswith(m.group(1)):
                add(ERROR, path, f"ADR id {fid} does not match filename number {m.group(1)}")
            if status and status not in ADR_STATUS:
                add(ERROR, path, f"ADR status '{status}' not in {sorted(ADR_STATUS)}")
            if status == "superseded" and not fm.get("superseded-by"):
                add(ERROR, path, "superseded ADR must set 'superseded-by'")
            if fid:
                adr_ids[fid] = path
                adr_status[fid] = status
                if fm.get("supersedes"): adr_links.setdefault(fid, {})["supersedes"] = str(fm["supersedes"])
                if fm.get("superseded-by"): adr_links.setdefault(fid, {})["superseded-by"] = str(fm["superseded-by"])
        if kind == "RFC" and not re.match(r"^RFC-\d{4}$", str(fm.get("id", ""))):
            add(ERROR, path, f"RFC id must match RFC-NNNN, got '{fm.get('id')}'")
        # user story should carry acceptance criteria (house heading may vary → warn)
        if kind == "US":
            low = body.lower()
            if "acceptance criteria" not in low and "scenario:" not in low and "given " not in low:
                add(WARN, path, "user story has no visible acceptance criteria (Gherkin or checklist)")
        # mandatory sections in HLD / SAD
        if kind in ("HLD", "SAD"):
            low = body.lower()
            if "threat model" not in low and "threat-model" not in low:
                add(ERROR, path, f"{kind} must contain a mandatory Threat model section (STRIDE/OWASP)")
            if "finops" not in low and "cost estimate" not in low:
                add(ERROR, path, f"{kind} must contain a mandatory FinOps cost-estimate section")
            for flag in ("security-reviewed", "cost-reviewed", "privacy-reviewed"):
                if flag not in fm:
                    add(WARN, path, f"{kind} should declare '{flag}: true|false'")
    # reciprocal supersession links
    for fid, links in adr_links.items():
        tgt = links.get("superseded-by")
        if tgt and tgt in adr_ids:
            back = adr_links.get(tgt, {}).get("supersedes")
            if back != fid:
                add(ERROR, adr_ids[fid], f"{fid} superseded-by {tgt}, but {tgt} does not 'supersedes: {fid}'")
        if tgt and tgt not in adr_ids:
            add(ERROR, adr_ids[fid], f"superseded-by points to missing {tgt}")
        sup = links.get("supersedes")
        if sup and sup not in adr_ids:
            add(WARN, adr_ids[fid], f"supersedes points to missing {sup}")
    return adr_ids, adr_status

# ---------- check: ISO 42010 conformance ----------
def _section_text(body, *keywords):
    """Return text of the heading-section whose title contains any keyword."""
    blocks = re.split(r"(?m)^#{1,6}\s+", body)
    for b in blocks:
        head = b.splitlines()[0].lower() if b.strip() else ""
        if any(k in head for k in keywords):
            return b
    return ""

def check_conformance(root):
    ad = os.path.join(root, "AD.md")
    if not os.path.exists(ad):
        add(INFO, root, "no AD.md found; skipping ISO 42010 conformance check")
        return
    body = split_frontmatter(open(ad, encoding="utf-8").read())[1]
    catalogue = _section_text(body, "viewpoint catalogue", "viewpoint") or body
    vps = set(re.findall(r"VP-[A-Z0-9-]+", catalogue))
    if not vps:
        add(ERROR, ad, "no viewpoints (VP-*) defined in AD.md viewpoint catalogue")
    for token, label in ((r"SH\.\d+", "stakeholder"), (r"CN\.\d+", "concern")):
        if not re.search(token, body):
            add(ERROR, ad, f"no {label}s defined in AD.md")
    # concern rows must reference a known viewpoint
    for ln in body.splitlines():
        if re.match(r"\s*\|\s*CN\.\d+", ln):
            row_vps = set(re.findall(r"VP-[A-Z0-9-]+", ln))
            if not row_vps:
                add(ERROR, ad, f"concern not framed by any viewpoint: {ln.strip()[:60]}")
            for vp in row_vps:
                if vp not in vps:
                    add(ERROR, ad, f"concern references unknown viewpoint {vp}")
        # view rows: governed by exactly one known viewpoint
        if re.match(r"\s*\|\s*V-(?!P)", ln):
            row_vps = re.findall(r"VP-[A-Z0-9-]+", ln)
            if len(row_vps) != 1:
                add(ERROR, ad, f"view must be governed by exactly one viewpoint: {ln.strip()[:60]}")
            elif row_vps[0] not in vps:
                add(ERROR, ad, f"view references unknown viewpoint {row_vps[0]}")
    # at least one ADR
    adrs = glob.glob(os.path.join(root, "**", "ADR-*.md"), recursive=True)
    if not adrs:
        add(WARN, root, "no ADRs found; 42010 expects key decisions to be recorded")
    # conformance checklist: no unresolved ❌
    chk = os.path.join(root, "conformance-checklist.md")
    if os.path.exists(chk):
        ctext = open(chk, encoding="utf-8").read()
        if "\u274c" in ctext:
            add(ERROR, chk, "conformance checklist still has ❌ (unsatisfied) items")
        if "\u26a0" in ctext:
            add(WARN, chk, "conformance checklist has ⚠️ (partial) items")
    else:
        add(WARN, root, "no conformance-checklist.md found")

# ---------- check: drift (ARCH-REF) ----------
def check_drift(root, src, adr_ids, adr_status):
    if not src or not os.path.isdir(src):
        add(INFO, src or ".", "no --src dir; skipping ARCH-REF drift check")
        referenced = set()
    else:
        referenced = set()
        pat = re.compile(r"ARCH-REF:\s*(ADR-\d{4})")
        for dp, _, files in os.walk(src):
            if any(s in dp for s in (os.sep + ".git", "node_modules", os.sep + ".venv")):
                continue
            for fn in files:
                fp = os.path.join(dp, fn)
                try:
                    txt = open(fp, encoding="utf-8", errors="ignore").read()
                except Exception:
                    continue
                for adr in pat.findall(txt):
                    referenced.add(adr)
                    if adr not in adr_ids:
                        add(ERROR, fp, f"ARCH-REF points to missing {adr}")
                    elif adr_status.get(adr) in ("superseded", "deprecated"):
                        add(WARN, fp, f"ARCH-REF points to {adr_status[adr]} {adr}")
    for adr, st in adr_status.items():
        if st == "accepted" and adr not in referenced:
            add(INFO, adr_ids[adr], f"accepted {adr} is not referenced by any ARCH-REF (possible drift)")

# ---------- check: links ----------
def check_links(root):
    link_re = re.compile(r"\]\((\.{1,2}/[^)\s#]+)")
    for path in md_files(root):
        base = os.path.dirname(path)
        for target in link_re.findall(open(path, encoding="utf-8").read()):
            if not os.path.exists(os.path.normpath(os.path.join(base, target))):
                add(WARN, path, f"broken relative link: {target}")

# ---------- emit front-matter bundle (for Spectral) ----------
def emit_frontmatter(root, out):
    docs = []
    for path in md_files(root):
        fm = split_frontmatter(open(path, encoding="utf-8").read())[0]
        if fm:
            fm = dict(fm); fm["_path"] = os.path.relpath(path, root)
            docs.append(fm)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    try:
        import yaml  # type: ignore
        open(out, "w", encoding="utf-8").write(yaml.safe_dump(docs, sort_keys=False))
    except Exception:
        # minimal JSON is valid YAML
        import json
        open(out, "w", encoding="utf-8").write(json.dumps(docs, indent=2, default=str))
    print(f"wrote {len(docs)} front-matter records to {out}")

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(description="Architecture-as-Code validator")
    ap.add_argument("check", choices=["frontmatter", "conformance", "drift", "links", "all"])
    ap.add_argument("--root", default="docs/architecture")
    ap.add_argument("--src", default="src")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--house", metavar="PATH", help="house-profile.yaml to enforce (auto-detected if present)")
    ap.add_argument("--emit-frontmatter", metavar="PATH", help="dump front-matter to YAML for Spectral")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        print(f"::error:: docs root not found: {args.root}"); sys.exit(2)

    house_path = args.house
    if not house_path:
        for cand in (os.path.join(args.root, "house-profile.yaml"), "house-profile.yaml"):
            if os.path.exists(cand):
                house_path = cand; break
    house = load_house(house_path)
    if house:
        add(INFO, house_path, f"enforcing house profile for types: {', '.join(sorted(house))}")

    adr_ids, adr_status = {}, {}
    if args.check in ("frontmatter", "all"):
        adr_ids, adr_status = check_frontmatter(args.root, args.strict, house)
    if args.check in ("conformance", "all"):
        check_conformance(args.root)
    if args.check in ("drift", "all"):
        if not adr_ids:
            adr_ids, adr_status = check_frontmatter(args.root, args.strict, house)  # need ADR map
        check_drift(args.root, args.src, adr_ids, adr_status)
    if args.check in ("links", "all"):
        check_links(args.root)
    if args.emit_frontmatter:
        emit_frontmatter(args.root, args.emit_frontmatter)

    errors = [f for f in findings if f[0] == ERROR]
    warns = [f for f in findings if f[0] == WARN]
    for level, path, msg in findings:
        marker = {"ERROR": "::error::", "WARN": "::warning::", "INFO": "  info:"}[level]
        print(f"{marker} {path}: {msg}")
    print(f"\nSummary: {len(errors)} error(s), {len(warns)} warning(s), "
          f"{len(findings) - len(errors) - len(warns)} info.")
    fail = bool(errors) or (args.strict and bool(warns))
    sys.exit(1 if fail else 0)

if __name__ == "__main__":
    main()
