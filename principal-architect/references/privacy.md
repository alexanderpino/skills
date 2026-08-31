# Privacy & compliance — DPIA and regulatory fit

Security (the threat model) protects the system; **privacy** protects the *people whose data
the system holds*, and **compliance** keeps it lawful. For any system that processes personal
or otherwise regulated data, this is a first-class architectural concern — as mandatory as the
threat model, and carried in the **same HLD/SAD §8** (the "Privacy & data protection (DPIA)"
subsection) with a `privacy-reviewed` sign-off flag. If no personal/regulated data is
processed, say so explicitly and set `privacy-reviewed: n/a` — don't leave it silent.

## When it applies
Trigger a DPIA whenever the system does any of: store/process personal data (names, emails,
IDs, location, device IDs, biometrics), profile or make automated decisions about people,
handle **special-category** data (health, biometric, financial, children's), or move personal
data **across borders**. When in doubt, do the lightweight assessment — it's cheap.

## The lightweight DPIA (Data Protection Impact Assessment)
A proportionate assessment, grounded in **ISO/IEC 29134** (PIA guidance) and **GDPR Art. 35**.
For each personal-data category answer:

1. **What** — the data category and its **sensitivity** (PII / special-category / pseudonymised).
2. **Why** — the **purpose** and the **lawful basis** (consent, contract, legitimate interest,
   legal obligation, …). Purpose limitation: data collected for X isn't reused for Y silently.
3. **Where** — the data flow and where it **lives** (residency/region), including every third
   party / SaaS processor it reaches. Cross-border transfers need a transfer mechanism (SCCs,
   adequacy).
4. **How long** — **retention** period and the deletion/erasure mechanism (right to erasure).
5. **Safeguards** — encryption at rest/in transit, access control + audit logging,
   pseudonymisation/anonymisation, minimisation (collect the least that works).
6. **Rights** — how the design supports data-subject rights: access, rectification, erasure,
   portability, objection.

Output is the §8 DPIA table plus any significant **residual privacy risk recorded as an ADR**.

## Architecture moves that satisfy privacy by design
GDPR Art. 25 ("data protection by design and by default") is an architecture mandate, not a
policy poster. Concretely:
- **Data minimisation** as a constraint (`C.xx`) — fewer fields, shorter retention, tokenise.
- **Pseudonymisation / anonymisation** at the boundary so downstream stores hold less.
- **Purpose-scoped stores** and access paths; **audit logging** of access to personal data.
- **Residency-aware deployment** (region-pinned stores, no incidental copies in logs/backups).
- **Crypto-shredding** (delete the key to honour erasure on immutable stores).

## Map to the regime(s) that apply
Name the frameworks in scope and map obligations to design decisions:

| Regime | Domain | Architectural obligations it drives |
|---|---|---|
| **GDPR / UK-GDPR** | EU/UK personal data | lawful basis, DPIA, residency/transfers, erasure, breach notification |
| **CCPA/CPRA** | California consumers | opt-out of sale, access/delete, data inventory |
| **HIPAA** | US health (PHI) | encryption, access audit, BAAs with processors |
| **PCI-DSS** | cardholder data | network segmentation, tokenisation, no PAN at rest in the clear |
| **EU AI Act** (Reg. (EU) 2024/1689) | AI systems placed on / used in the EU market | risk-tier classification; for high-risk: risk management, data governance, technical documentation, logging, human oversight, accuracy/robustness (see below) |
| **SOC 2 / ISO 27001 / ISO/IEC 42001** | security / AI management controls (org-wide) | control mapping; complements, not replaces, the above (42001 = the AI-management counterpart of 27001) |

> Supply-chain note: third-party/SaaS processors that touch personal data are part of the
> privacy surface (and OWASP **A03 Software Supply Chain Failures**). Record the processor, the
> data it sees, and the data-processing agreement (DPA) in the §8 table.

## AI-bearing systems — the same artifacts carry the obligations

When the system contains an ML/LLM component, no new documentation formalism is needed —
the existing artifacts carry the AI obligations, and the skill's job is to make sure they do:

1. **Classify the risk tier first** (EU AI Act: prohibited / high-risk per Annex III /
   transparency-only / minimal). The tier is a constraint (`C.xx`) and decides how much of
   the rest applies. The ISO/IEC backbone: **22989:2022** (concepts & terminology — use its
   vocabulary in the docs), **23894:2023** (AI risk management guidance), **42001:2023**
   (the certifiable AI management system — the 27001 of AI), and **42005:2025** (AI system
   impact assessment — the AI counterpart of the DPIA above; where both apply, run them
   together as one §8 assessment). Outside the EU, **NIST AI RMF 1.0**
   (govern·map·measure·manage) is the voluntary counterpart.
2. **Model quality targets are ordinary `Q.xx` scenarios** — accuracy, groundedness,
   refusal behaviour, latency; response measure = the eval threshold, means of verification
   = the eval suite (run in CI as a fitness function, `automation.md`).
3. **The high-risk obligations map onto artifacts that already exist**: technical
   documentation → the AD/HLD/SD set itself; record-keeping/logging → the observability
   design (`operability.md`); human oversight → a design constraint on the flow (`C.xx`);
   data governance for training/eval data → `data-architecture.md` ownership + the DPIA
   table (training data containing personal data is *processing* — the DPIA above applies).
4. **A model card** (Mitchell et al. 2019) or the vendor's system card is the model's
   interface contract — link it from the SD like an `api-spec:`. Model/prompt/eval-set
   versions are part of the SD's design, and a significant model or provider choice is an
   ADR (it's a build-vs-buy decision with quality, cost, and lock-in consequences).
5. **The threat model switches lens**: in HLD/SAD §8, LLM components map STRIDE findings
   to the **OWASP Top 10 for LLM Applications:2025** (prompt injection, insecure output
   handling, training-data poisoning, excessive agency) — the web Top 10 doesn't name
   these classes. Untrusted text reaching the model is a trust boundary like any other.

## Linkage
- **PRD**: data-protection limits are quality/constraint drivers (`Q.xx` security→confidentiality,
  or `C.xx` constraints).
- **HLD/SAD §8**: the DPIA table + `privacy-reviewed` flag (enforced by `arch_lint.py`).
- **ADR**: each significant privacy trade-off (e.g. residency vs. latency, retention vs. analytics),
  and each significant model/provider choice in an AI-bearing system.
- **Conformance**: privacy obligations are concerns in `AD.md` §3, framed by the quality viewpoint.
