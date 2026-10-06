# Cloud architecture — account structure, failure domains, compute, tenancy, exit

**Load when** the work sets up or changes a landing zone or account hierarchy; a
reliability, residency or regulatory driver forces a region or provider topology; a
compute model is chosen; a multi-tenant SaaS is designed; or sovereignty or exit is a
driver. FinOps (HLD/SAD §9), cloud design patterns (`structure.md` §3) and on-premises to
cloud migration (`migration.md`) already live elsewhere; this file covers the decisions
those assume.

**Altitude.** Landing zone, guardrails and approved regions are enterprise altitude
(`PR.xx`). A workload's topology, compute model and tenancy model are solution or software
ADRs whose driver is a `Q.xx` or `C.xx`.

**Grounding rule.** Every rule carries a source `[Sn]`. Quotas, prices, service limits and
support windows change: look them up when you write and put the URL next to the value.

---

## 1. Derive the cloud estate from evidence before asking

| Evidence | What it tells you |
|---|---|
| Organisation/account/subscription/project resources, SCPs, Azure Policy, org policies | account structure and guardrails (§2.1) |
| Region and zone arguments on resources; multi-AZ flags on databases; replication and backup config | the topology actually deployed (§2.2) |
| Compute resources (instances, container services, clusters, functions) | compute model in use (§2.4) |
| `tenant_id` columns, row-level-security policies, per-tenant stacks or accounts | tenancy model (§2.5) |
| Key resources (provider-managed vs customer-managed vs external keys) | key control (§2.7) |
| Tags on resources | whether cost allocation is possible |

Ask only for what evidence cannot give: **RTO and RPO**, the failure the business must
survive, applicable regulation (DORA, Data Act, residency), and tenant contract terms.

---

## 2. Decide

### 2.1 Account structure

- **Proven vs current** (SKILL.md §1). Many estates run for years in one shared account or
  subscription; current provider guidance is separate accounts per workload and
  environment [S1]. Record the gap and its blast-radius consequence, then move workloads
  out incrementally rather than leaving the gap undocumented.
- Use **separate accounts per workload and environment**, grouped in an organisational
  hierarchy that reflects how policy differs [S1]. The account is the boundary for IAM,
  quotas and billing [S1].
- Start from the provider's landing-zone reference and record deviations as ADRs [S2][S3].
- Central log and security accounts that workload teams cannot alter carry the
  repudiation control in `threat_modeling.md` [S1].

### 2.2 Topology from RTO/RPO

1. Name the failure to survive as a `Q.xx` stimulus: host, zone, region, or provider.
2. Pick the cheapest strategy that meets the RTO/RPO. AWS characterises the four
   strategies as: backup and restore (hours), pilot light (tens of minutes), warm standby
   (minutes), multi-site active/active (near real-time), each more complex and costly than
   the last [S4].
3. Prove it with a recovery drill against the stated RTO/RPO before claiming it [S4]
   (`operability.md`), and price it in §9.
4. **Multi-cloud** needs a driver whose stimulus is the provider itself or a regulation:
   DORA requires financial entities to have documented, tested exit strategies for ICT
   services supporting critical or important functions (Art. 28(8))
   and to assess ICT concentration risk (Art. 29) [S5]. Record what it costs in services,
   skills and egress.

### 2.3 Blast radius beyond zones

Zones protect against infrastructure failure; deployments, configuration and poison
requests hit every zone at once [S6]. When a `Q.xx` requires bounded impact:

| Pattern | What it bounds | Source |
|---|---|---|
| **Cells** — independent copies of the workload, each serving a subset of customers, behind a thin router | impact of a bad deployment or request to one cell | [S6] |
| **Shuffle sharding** — each customer on a random small subset of workers | overlap between a noisy or failing customer and others | [S7] |
| **Static stability** — keep serving on last-known-good state; pre-provision for zone loss | dependence on control planes during failure | [S8] |
| **Constant work** — same work in healthy and failed states | untested bimodal behaviour | [S9] |
| **Staged deployment** — per cell/zone/region with bake time and automatic rollback | change-induced outages | [S10] |

Check quotas and limits for the failover case, when the surviving zone or cell takes the
load; record them as `C.xx` with their URL.

### 2.4 Compute model

| Model | Decide with |
|---|---|
| Virtual machines | you own OS patching and scaling; needed for OS-level control, licensing, legacy |
| Managed containers | container packaging without operating a cluster |
| Kubernetes | each minor version has a fixed support window (check its current length [S11]), so plan an upgrade cadence and a team to run it; it is not a tenant isolation boundary (`systems-architecture.md` §2.1) |
| Functions | execution-time, payload and concurrency limits from the provider's quota page; cold starts; state and coordination outside the function [S12][S13] |

**Cost crossover:** average concurrency is arrival rate × duration (Little's Law [S14],
`quantitative-methods.md` §1). Price that concurrency as provisioned capacity and compare it
with the per-request bill in the provider calculator; record the crossover traffic in §9 so
the choice is revisited when traffic passes it.

### 2.5 Tenancy (SaaS)

- Choose silo (dedicated resources per tenant), pool (shared, tenant-scoped at every layer)
  or bridge (mixed per layer) per layer [S15].
- Whatever the model, design and test **tenant isolation enforcement**: in pooled models it
  must be applied on every request and query, which is where broken object-level
  authorisation appears [S16][S17] (`threat_modeling.md` §3).
- Add per-tenant quotas or cells/shuffle sharding against noisy neighbours [S7][S15].

### 2.6 Shared responsibility

The split between provider and customer moves with the service model (IaaS, PaaS, SaaS)
[S18][S19]. For each managed service, write who owns patching, configuration, identity and
data into the threat model; the gaps sit at that boundary. Treat lock-in as a cost: put the
estimated switching cost in the ADR next to what the service saves.

### 2.7 Sovereignty, residency and exit

- **Residency is not jurisdiction.** US providers can be compelled to disclose data they
  control regardless of where it is stored (CLOUD Act) [S20]. If jurisdiction is a driver,
  name it as a `C.xx` and decide between provider options and key control.
- **Key control:** customer-managed keys in the provider's key service give you control of
  key policy, rotation and revocation, but the provider still operates that service; only
  keys held outside the provider (an external key store, client-side encryption) withhold
  plaintext from it [S24]. Confidential computing extends protection to data in use
  (`systems-architecture.md` §2.1).
- **Exit:** the EU Data Act's switching rules apply since 12 September 2025, and from
  12 January 2027 providers may not charge switching charges (Art. 29), except for
  custom-built services and non-production versions (Art. 31) [S21]; check for later
  amendments to Chapter VI before relying on it. Write the exit
  plan into the SAD: portable data formats, IaC, the list of proprietary dependencies, and a
  tested export of core data. Financial entities must test it for ICT services supporting critical or important
  functions (DORA Art. 28(8)) [S5].

### 2.8 Platform team and carbon

- Build an internal platform when several stream-aligned teams repeat the same
  infrastructure work; treat it as a product with paved paths [S22].
- When the organisation has carbon targets, write them as a `Q.xx` measured in Software
  Carbon Intensity [S23].

---

## 3. Record

| Where | What |
|---|---|
| Enterprise architecture | account hierarchy, guardrails, approved regions, exit strategy for critical providers |
| PRD | RTO/RPO and the failure to survive; residency/jurisdiction `C.xx`; quotas `C.xx` |
| SAD / HLD | DR strategy and topology; compute model; tenancy model; shared-responsibility split in §8; crossover and egress in §9 |
| ADRs | DR strategy, multi-region or multi-cloud, cells, compute model, tenancy model, key-control model, managed services with lock-in |
| Fitness functions | policy-as-code on IaC; scheduled recovery drills against RTO/RPO; quota headroom alarms; Infracost gate (`automation.md`) |

---

## 4. Flag in review

- a multi-region or multi-cloud design with no `Q.xx` naming the region or provider failure
  it survives [S4];
- an RTO/RPO claim with no recovery drill [S4];
- one shared account for several workloads or environments [S1];
- pooled tenancy without tested tenant isolation on every request [S16];
- a Kubernetes cluster with no upgrade plan inside the support window [S11];
- functions at sustained load with no crossover calculation [S14];
- residency stated as if it settled jurisdiction [S20];
- no exit plan where DORA or a critical-provider driver applies [S5][S21].

---

## Sources

| ID | Source |
|---|---|
| S1 | AWS whitepaper, *Organizing Your AWS Environment Using Multiple Accounts* |
| S2 | Microsoft Cloud Adoption Framework, *Azure landing zones* |
| S3 | AWS Control Tower / Landing Zone Accelerator documentation; Google Cloud, *Enterprise foundations blueprint* |
| S4 | AWS whitepaper, *Disaster Recovery of Workloads on AWS*, "Disaster recovery options in the cloud" |
| S5 | Regulation (EU) 2022/2554 (DORA), Art. 28(8) exit strategies, Art. 29 concentration risk |
| S6 | AWS Well-Architected, *Reducing the Scope of Impact with Cell-Based Architecture* (2023) |
| S7 | AWS Builders' Library, *Workload isolation using shuffle-sharding* |
| S8 | AWS Builders' Library, *Static stability using Availability Zones* |
| S9 | AWS Builders' Library, *Reliability, constant work, and a good cup of coffee* |
| S10 | AWS Builders' Library, *Automating safe, hands-off deployments* |
| S11 | Kubernetes, *Releases* (version skew and support period), https://kubernetes.io/releases/ |
| S12 | E. Jonas et al., *Cloud Programming Simplified: A Berkeley View on Serverless Computing*, UC Berkeley EECS-2019-3 |
| S13 | J. Hellerstein et al., *Serverless Computing: One Step Forward, Two Steps Back*, CIDR 2019 |
| S14 | J. D. C. Little, *A Proof for the Queuing Formula L = λW*, Operations Research 9(3), 1961 |
| S15 | AWS Well-Architected, *SaaS Lens*; AWS whitepaper, *SaaS Tenant Isolation Strategies* |
| S16 | OWASP, *API Security Top 10 2023*, API1 Broken Object Level Authorization |
| S17 | OWASP, *Top 10:2025*, A01 Broken Access Control |
| S18 | NIST SP 800-145, *The NIST Definition of Cloud Computing* (2011) |
| S19 | AWS, *Shared Responsibility Model*; Microsoft, *Shared responsibility in the cloud* |
| S20 | 18 U.S.C. § 2713 (CLOUD Act) |
| S21 | Regulation (EU) 2023/2854 (Data Act), Chapter VI, Art. 29 and Art. 31 |
| S22 | M. Skelton, M. Pais, *Team Topologies*, IT Revolution 2019 |
| S23 | ISO/IEC 21031:2024, *Software Carbon Intensity (SCI) specification* |
| S24 | AWS documentation, *External key stores* (AWS KMS XKS), https://docs.aws.amazon.com/kms/latest/developerguide/keystore-external.html |
