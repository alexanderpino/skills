---
id: architecture-index
title: LinkShort — architecture docs index
---

# LinkShort architecture docs

Docs root for the **LinkShort** URL-shortener API. Resolved root:
`docs/architecture/` (this directory).

## Map

| Doc | What |
|---|---|
| [AD.md](./AD.md) | ISO/IEC/IEEE 42010 Architecture Description (stakeholders, concerns, viewpoints, views) |
| [PRD.md](./PRD.md) | Drivers — business `B.xx`, functional `F.xx`, quality `Q.xx` |
| [requirements/](./requirements/) | Epics `EP-NNN` and user stories `US-NNN` with acceptance criteria |
| [software/HLD.md](./software/HLD.md) | C4 context/container, threat model, FinOps |
| [software/SD-api-keys.md](./software/SD-api-keys.md) | Component design for API-key management |
| [decisions/](./decisions/README.md) | ADR log |
| [conformance-checklist.md](./conformance-checklist.md) | ISO conformance audit |

## Manifest

```yaml
entity_of_interest: LinkShort URL-shortener API
level: software
standards: [ISO/IEC/IEEE 42010:2022, ISO/IEC 25010:2023, ISO/IEC/IEEE 29148:2018]
traceability: EP-001 → F.01 → US-001 → acceptance-criteria → test
```
