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
| **SOC 2 / ISO 27001** | security controls (org-wide) | control mapping; complements, not replaces, the above |

> Supply-chain note: third-party/SaaS processors that touch personal data are part of the
> privacy surface (and OWASP **A03 Software Supply Chain Failures**). Record the processor, the
> data it sees, and the data-processing agreement (DPA) in the §8 table.

## Linkage
- **PRD**: data-protection limits are quality/constraint drivers (`Q.xx` security→confidentiality,
  or `C.xx` constraints).
- **HLD/SAD §8**: the DPIA table + `privacy-reviewed` flag (enforced by `arch_lint.py`).
- **ADR**: each significant privacy trade-off (e.g. residency vs. latency, retention vs. analytics).
- **Conformance**: privacy obligations are concerns in `AD.md` §3, framed by the quality viewpoint.
