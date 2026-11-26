# Research protocol — Phase 1

The research answers one question per proposal section: *what does this domain actually
have here?* Its output is the ledger in `<target>/.ssb/research/` plus `report.md`.

## 1. Explore before searching

Read what already exists — it is cheaper and more specific than the web:

- The user's codebase or docs (if named at intake): modules, existing roles in CODEOWNERS,
  existing processes in CONTRIBUTING, CI, ADRs.
- Any agent setup the user already has (`.claude/agents/`, `.claude/skills/`, a CLAUDE.md,
  team handbooks): roles and rules that already work for them are evidence, and the studio
  should fit them rather than replace them. The *shape* of every layer is already in
  `references/anatomy.md` — do not go looking for another template to copy.
- The domain pack, if one exists — as hypotheses to confirm or refute.

## 2. The ledger

```bash
python3 scripts/ledger.py init <run>/research --query "<domain> studio" --scope "<intake summary>"
```

Three JSONL files, one chain: **claim → evidence (verbatim quote + locator) → source**.

| Tier | What qualifies | Example |
|---|---|---|
| `primary` | The thing itself: statute or regulator text, a standard's own text, a vendor's spec of its own product, an employer's own job posting | an official legislation portal page; a company careers page |
| `standard-body` | Pages and summaries published by the standards body | ISO, IEEE, IIBA (BABOK), OMG (BPMN), W3C (WCAG), OWASP, NIST, AXELOS (ITIL) |
| `vendor-docs` | Official product documentation and guides | a platform's developer docs |
| `practitioner` | Named practitioners: books, conference talks, engineering blogs | a talk by a named engineer about their payroll system |
| `unverified` | Not opened, second-hand, or unattributed | a listicle, a forum answer, a search snippet |

Claim statuses: `supported` (≥1 evidence above `unverified`; a `synthesis` needs ≥2 sources),
`supported-inference` (reasons from named claims), `contested` (both sides cited),
`unverified`, `not-sourceable` (searched for, not found — with the search named).

Rules that keep the ledger honest:

- **Quote, don't paraphrase,** in `--quote`; the locator says where (section, heading,
  page). Paraphrase belongs in `--supports`.
- **Never record a source you did not open** above `unverified`.
- **Wikipedia and search snippets are not sources;** follow them to what they cite.
- **Record the dead ends** with `ledger.py not-sourceable` — a visible gap beats a guess.
- **Correct, never edit.** A wrong quote or claim is replaced with `--supersedes E010` /
  `--supersedes C004` on `add-evidence` / `add-claim`. The old row stays, marked superseded,
  and can no longer be cited — by a claim or by the proposal.
- **Job titles are evidence of roles; job postings are primary for them.** Several postings
  from different employers make a role a supported synthesis.
- **Dates matter.** Regulation changes. Put the version or effective date in the claim.

## 3. Lanes

Spawn the lanes **in one message** (parallel `Agent` calls, `subagent_type` general-purpose
or a research-capable agent). Default lanes — merge or split by domain:

| Lane | Answers | Feeds proposal sections |
|---|---|---|
| `roles` | Which job titles exist; who reports to whom; who decides what; which roles a small team merges | roles (tiers, reports_to, escalation) |
| `process` | Lifecycle and phases; governing standards (e.g. requirements, process modelling, service management); where reviews and sign-offs happen | phases, gates, skills |
| `artifacts` | Documents the domain produces; their standard sections; who owns each | artifacts, templates, catalog globs |
| `regulation` | Obligations that bind the software (privacy, financial controls, sector law, accessibility, retention, audit trail) and what they require of code and process | rules, compliance role, gates, `must_not` |
| `stack` | Common platforms and toolchains; code and test layout; build/test commands; known failure modes and lessons | stacks, rules, standards sections |

### The lane brief (copy, fill the brackets)

```
You are research lane `<lane>` for a Claude Code studio template for <domain>
(<users>; regulation: <regulation>; stacks: <stacks>).

Question: <the lane's questions from the table, made specific to the domain>.

Record everything ONLY through the ledger CLI — never edit its files:
  python3 <skill>/scripts/ledger.py add-source <run>/research --id <slug> --title ... --publisher ...
      --url ... --tier primary|standard-body|vendor-docs|practitioner|unverified --type ... --lane <lane>
  python3 <skill>/scripts/ledger.py add-evidence <run>/research --source <slug> --quote "<verbatim>"
      --locator "<section/page>" --supports "<what it shows>" --lane <lane>
  python3 <skill>/scripts/ledger.py add-claim <run>/research --claim "..." --kind fact|synthesis|recommendation
      --evidence E00x,E00y [--status ...] --lane <lane>
  python3 <skill>/scripts/ledger.py not-sourceable <run>/research --claim "..." --reason "<what you searched>"

Rules: open every source you cite above `unverified`; quote verbatim; never state a legal
requirement, rate or deadline you did not read in a primary source; record dead ends as
not-sourceable. Budget: about <N> sources. Stop when the questions are answered or the
gaps are recorded.

Return (max 300 words): the claim ids you created, one line each, and the gaps.
```

## 4. Integrate

1. `ledger.py check <run>/research` — FAIL means a broken chain: fix it before anything else.
2. Read every `unverified` claim; re-research the ones a proposal item will rest on.
3. Resolve `contested` claims or carry them into `open_questions`.
4. Write `<run>/research/report.md`: Summary · Roles · Process · Artifacts · Regulation ·
   Stacks · Lessons and failure modes · Open questions · Limitations (what was not
   researched and why). Cite claim ids inline.
5. `state.py phase <run> proposal`.

## Stop rules

- **Enough:** every proposal section has supported claims or a recorded gap.
- **Too much:** a lane is re-finding the same sources — stop it.
- **Never** stop because the ledger looks big. Size is not coverage.
