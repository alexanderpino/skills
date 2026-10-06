# Network architecture — placement, topology, protocols, segmentation

**Load when** the work designs or changes connectivity (cloud network or hub, hybrid link,
datacenter fabric, WAN); makes a protocol choice with a quality trade-off; places
segmentation, ingress or egress controls; or must meet a latency or transfer `Q.xx` across
distance. A system that only *uses* an existing network states its zones and flows in its
HLD §6 and §8 (see §3 below) and links to the network's own SAD; it does not redesign it.

**Altitude.** Shared networks (hub, fabric, WAN, address plan) are enterprise or solution
altitude: one team owns them and many systems depend on them.

**Grounding rule.** Every rule carries a source `[Sn]`. Quotas, prices and product
behaviour change: look them up when you write and put the URL next to the value.

---

## 1. Derive the network from evidence before asking

| Evidence | What it tells you |
|---|---|
| IaC: VPC/VNet/network, subnets, route tables, peering, transit gateway / virtual WAN, NAT, private endpoints, VPN and dedicated-connection resources | topology, address ranges, hybrid paths |
| Security groups, NSGs, firewall policies, Kubernetes `NetworkPolicy` | the flows actually allowed — the as-is flow matrix |
| Ingress, gateway, load-balancer and service-mesh config | north–south and east–west paths, TLS termination points |
| TLS configuration (minimum version, groups, ciphers) | where cryptography is terminated and how agile it is (§2.6) |
| HTTP/RPC client config: timeouts, retries, connection pools | retry amplification risk (§2.4) |
| DNS zones and resolver forwarding rules | hybrid name resolution, failover TTLs |

Ask only for what evidence cannot give: where users and peer systems are, the latency
budget and its measure, bandwidth and transfer windows, and which zones regulation or
policy requires.

---

## 2. Decide

### 2.1 Placement before protocol — check the latency budget against physics

1. Compute the propagation floor: about 5 µs per km of fibre one way [S1], so about 1 ms
   of round-trip time per 100 km of path. Formulas and a worked example are in
   `quantitative-methods.md` §11.
2. Count the **sequential** round trips per user action: a new HTTPS request over TCP and
   TLS 1.3 costs one RTT for the TCP handshake [S2] and one for TLS [S3] before the
   request; QUIC combines transport and TLS handshakes [S4].
3. If floor × sequential round trips exceeds the budget, change placement or the call
   pattern (co-locate, batch, parallelise, cache). No protocol tuning beats the floor.
4. Record the budget calculation next to the `Q.xx`.

### 2.2 Planes and recovery paths

- Design the **data plane to keep working on last-known-good state when the control plane
  is impaired** (static stability) [S5]. Recovery plans that require control-plane actions
  during the incident (launching capacity, API-driven route changes) depend on the thing
  most likely to be degraded; pre-provision instead [S5].
- Keep an **out-of-band management path**: in the October 2021 Facebook outage the
  backbone disconnection also cut the tools and access engineers needed to recover [S6].
- Record both in HLD/SAD §7 or §10 (operability).

### 2.3 Topology

| Situation | Default | Source | Record |
|---|---|---|---|
| More than a few cloud networks | **hub-and-spoke** with central routing and inspection | [S7][S8] | ADR; hub is a shared fault and cost domain |
| Network-to-network peering | peering is **not transitive** and needs non-overlapping CIDRs | [S9] | address plan |
| Exposing one service across networks | private endpoint / PrivateLink instead of routing whole networks | [S10] | flow matrix |
| Hybrid connectivity with a resilience `Q.xx` | dedicated connections at more than one location on separate devices; a single connection is a single point of failure | [S11] | ADR with the resilience model chosen |
| Datacenter fabric | Clos (spine-leaf); the **oversubscription ratio** is a capacity decision | [S12] | ADR with the ratio |
| Address space | non-overlapping private ranges for the whole estate, planned once [S13][S9]; public IPv4 is metered at AWS since February 2024 [S14] | | IP plan in the network SAD; IPv6 strategy as ADR |

### 2.4 Protocols, load balancing and retries

- **QUIC/HTTP/3:** applications must either accept failure on networks that block UDP or
  fall back to TLS over TCP, and the fallback must not downgrade security [S15].
- **TLS 1.3 0-RTT** data can be replayed; accept it only for idempotent requests [S3].
- **gRPC over HTTP/2** keeps long-lived connections, so connection-level (layer 4)
  balancing pins load; use request-level proxy or client-side balancing [S16].
- **DNS TTL** is the failover knob, but resolvers may serve stale data beyond it [S17];
  do not promise a failover time shorter than the stale window you allow.
- **Retries multiply across layers.** Use timeouts, capped exponential backoff with
  jitter, and retry at one layer [S18][S19]. Check every client config found in §1.
- **Health checks** that test shared dependencies can remove a whole fleet at once; prefer
  local checks and fail open when all targets look unhealthy [S20].
- **Service mesh:** it adds a control plane and a data-plane proxy per pod or node [S21].
  Adopt it when a driver (uniform mTLS, traffic policy, telemetry) spans many services and
  the team can operate that control plane; otherwise use platform identity and a plain
  ingress (`enterprise-architecture-bingo.md`).

### 2.5 Segmentation, ingress and egress

- **Proven vs current** (SKILL.md §1). The perimeter model — a trusted internal network
  behind a firewall — has decades of use. NIST's zero-trust architecture explains why it no
  longer holds for remote users, cloud services and lateral movement inside the perimeter
  [S22]. In an existing estate, record the gap and choose per zone: keep (with a recorded
  reason), work around (identity-based access per request in front of the existing
  network), or replace.
- **Zero trust and segmentation are complements.** Grant access per request on identity,
  not network location [S22]; segment into zones with controlled conduits to limit how far
  a compromise spreads [S23].
- **Egress:** filter outbound traffic, not only inbound [S24]. Default-deny egress with an
  allow-list breaks SSRF-to-metadata and exfiltration paths; on AWS also require IMDSv2
  [S25].
- **Flow matrix:** one row per allowed flow across a zone boundary (source, destination,
  protocol/port, authentication, encryption, justifying `F.xx`). Every row is a trust
  boundary crossing and gets a STRIDE entry [S26][S23]. A flow without a justification is a
  finding.

### 2.6 Post-quantum readiness

1. **Prioritise by confidentiality lifetime.** If data must stay secret for *x* years and
   migration takes *y* years, you are exposed when *x + y* exceeds the time until a
   cryptographically relevant quantum computer exists (Mosca) [S27]. Traffic recorded now
   can be decrypted later.
2. **Inventory** cryptographic use and TLS termination points (a cryptographic bill of
   materials) [S28].
3. **Plan against the published timeline:** ML-KEM, ML-DSA and SLH-DSA are standardised
   [S29]; NIST's draft transition plan deprecates quantum-vulnerable public-key algorithms
   after 2030 and disallows them after 2035 [S30].
4. **Write crypto-agility as a `Q.xx`** (modifiability: algorithms change by configuration
   at every termination point you own) and test larger handshakes on constrained links
   before switching signatures [S31].

---

## 3. Record

| Where | What |
|---|---|
| PRD | latency/transfer `Q.xx` with the physics calculation; zone and residency `C.xx` |
| HLD §6 | the zone each container runs in; the network & trust-zone view (`mermaid-guide.md`) |
| HLD/SAD §8 | flow matrix; STRIDE row per zone crossing; egress controls; PQC exposure |
| HLD §7 / SAD §10 | static-stability and out-of-band recovery assumptions |
| Network SAD | topology, IP plan, hybrid model, oversubscription |
| ADRs | hub design, hybrid resilience model, IPv6 strategy, mesh adoption, PQC migration order |
| Fitness functions | configuration and reachability verification before network changes [S32]; synthetic latency probes against the budget |

---

## 4. Flag in review

- a latency `Q.xx` that is below the physics floor for the chosen placement [S1];
- access granted by network location alone, or a flat network justified by "zero trust"
  [S22][S23];
- no egress filtering; IMDSv1 reachable from workloads [S24][S25];
- a zone crossing without a flow-matrix row or a STRIDE entry [S26];
- retries at several layers, or retries without backoff and jitter [S18];
- QUIC without TCP fallback, or 0-RTT accepted for non-idempotent requests [S15][S3];
- recovery that needs the control plane, or no out-of-band access [S5][S6];
- overlapping address ranges between networks that must connect [S9];
- long-lived confidential data on key exchange with no PQC plan [S27][S30].

---

## Sources

| ID | Source |
|---|---|
| S1 | ITU-T Recommendation G.114, *One-way transmission time* (2003) — planning value 5 µs/km for optical fibre |
| S2 | RFC 9293, *Transmission Control Protocol* (2022) |
| S3 | RFC 8446, *TLS 1.3* (2018) — §2 handshake; §8 and Appendix E.5 0-RTT replay |
| S4 | RFC 9000, *QUIC* (2021); RFC 9001, *Using TLS to Secure QUIC* |
| S5 | AWS Builders' Library, *Static stability using Availability Zones* |
| S6 | Meta Engineering, *More details about the October 4 outage* (2021) |
| S7 | Microsoft Azure Architecture Center, *Hub-spoke network topology in Azure* |
| S8 | AWS whitepaper, *Building a Scalable and Secure Multi-VPC AWS Network Infrastructure* |
| S9 | AWS documentation, *VPC peering* (limitations: no transitive peering, no overlapping CIDRs) |
| S10 | AWS documentation, *AWS PrivateLink*; Azure documentation, *Private Endpoint* |
| S11 | AWS, *Direct Connect Resiliency Recommendations* |
| S12 | M. Al-Fares, A. Loukissas, A. Vahdat, *A Scalable, Commodity Data Center Network Architecture*, SIGCOMM 2008 |
| S13 | RFC 1918, *Address Allocation for Private Internets* (1996) |
| S14 | AWS News Blog, *New – AWS Public IPv4 Address Charge + Public IP Insights* (2023) |
| S15 | RFC 9308, *Applicability of the QUIC Transport Protocol* (2022) |
| S16 | gRPC blog, *gRPC Load Balancing* (2017), https://grpc.io/blog/grpc-load-balancing/ |
| S17 | RFC 8767, *Serving Stale Data to Improve DNS Resiliency* (2020) |
| S18 | AWS Builders' Library, *Timeouts, retries, and backoff with jitter* |
| S19 | B. Beyer et al. (eds.), *Site Reliability Engineering*, O'Reilly 2016, ch. 22 *Addressing Cascading Failures* |
| S20 | AWS Builders' Library, *Implementing health checks* |
| S21 | Istio documentation, *Architecture* |
| S22 | NIST SP 800-207, *Zero Trust Architecture* (2020) |
| S23 | IEC 62443-3-2, *Security risk assessment for system design* (zones and conduits) |
| S24 | NIST SP 800-41 Rev. 1, *Guidelines on Firewalls and Firewall Policy* (2009) |
| S25 | AWS Security Blog, *Add defense in depth against open firewalls, reverse proxies, and SSRF vulnerabilities with enhancements to the EC2 Instance Metadata Service* (2019) |
| S26 | A. Shostack, *Threat Modeling: Designing for Security*, Wiley 2014 |
| S27 | M. Mosca, *Cybersecurity in an Era with Quantum Computers: Will We Be Ready?*, IEEE Security & Privacy 16(5), 2018 |
| S28 | CycloneDX, *Cryptography Bill of Materials (CBOM)* |
| S29 | NIST FIPS 203, 204 and 205 (August 2024) |
| S30 | NIST IR 8547 (initial public draft), *Transition to Post-Quantum Cryptography Standards* (2024) |
| S31 | NIST SP 1800-38, *Migration to Post-Quantum Cryptography* (NCCoE practice guide) |
| S32 | A. Fogel et al., *A General Approach to Network Configuration Analysis* (Batfish), NSDI 2015 |
