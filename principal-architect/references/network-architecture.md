# Network architecture — planes, topology, protocols, segmentation

`threat_modeling.md` already insists that the network is not a trust boundary, and
`anti_over_engineering.md` reminds you that the network is neither reliable nor free. Both
treat the network as something an application *crosses*. This file is for when the network
is the thing being designed. Read it when:

- the work **designs or changes connectivity**: a datacenter fabric, a cloud network or
  landing-zone hub, hybrid connectivity, a WAN, a site;
- a **protocol or transport choice** carries a quality trade-off (QUIC vs TCP, gRPC
  streaming vs request/response, DNS-based failover, multicast);
- you must place **segmentation, ingress and egress controls** — where the firewalls, WAF,
  DDoS protection, gateways and private endpoints go, and which flows are allowed;
- a `Q.xx` is bound by **physics or bandwidth**: a latency budget across regions, a bulk
  transfer window, an edge placement question;
- a **network lifecycle** decision is due: MPLS to SD-WAN, IPv4 exhaustion, VPN to zero
  trust network access, the move to post-quantum TLS.

**Altitude.** Shared network infrastructure (a fabric, a WAN, a landing-zone hub, the IP
plan) is **enterprise or solution** altitude: many systems depend on it and one team owns it.
A single system's HLD does not redesign that network. It states which zones its containers
live in, which flows it needs, and what it assumes about the network, and links to the
network's own SAD or ADRs.

---

## 1. Three planes — the decomposition behind everything else

Every network, and most distributed platforms, separate into three planes:

- the **data plane** forwards packets or requests (switch ASICs, routers, load balancers,
  Envoy proxies, eBPF programs);
- the **control plane** computes where traffic should go (BGP, OSPF/IS-IS, an SDN
  controller, a service-mesh control plane such as `istiod`, the Kubernetes API, the cloud
  provider's API);
- the **management plane** configures and observes (IaC, NETCONF/gNMI, telemetry, the
  console).

The design rule that follows is **static stability**: the data plane must keep forwarding on
its last known good state when the control plane is impaired (AWS Builders' Library,
*Static stability using Availability Zones*). Envoy keeps serving its cached configuration
when the mesh control plane is down. Running instances keep running when the cloud API is
degraded. DNS answers survive in caches for their TTL. A recovery plan that needs control
plane operations during the incident, such as launching instances, changing routes through
an API or issuing new certificates, is fragile, because the incident often impairs exactly
those APIs. Pre-provision instead.

The October 2021 Facebook outage is the reference failure. A command during backbone
maintenance disconnected the datacenters. The DNS servers, unable to reach the datacenters,
withdrew their BGP announcements as designed, which made Facebook unreachable. The tools and
access engineers needed to fix it depended on the same network. Two lessons: keep an
**out-of-band management network with break-glass access**, and check that recovery paths do
not depend on the thing that failed.

---

## 2. Topology

| Context | Legacy shape | Current shape | Why it changed / when to use | Cost / watch out |
|---|---|---|---|---|
| **Datacenter fabric** | three-tier (access, aggregation, core) with spanning tree | **spine-leaf Clos**: every leaf connects to every spine, layer 3 to the rack, ECMP across spines; **EVPN-VXLAN** overlay where layer 2 segments are still needed | traffic became mostly east–west; Clos gives a predictable hop count and scales by adding spines | the **oversubscription ratio** (leaf downlink : uplink capacity, e.g. 48×25G down vs 6×100G up = 2:1) is a capacity decision; record it |
| **WAN** | MPLS L3VPN on leased lines, hub-and-spoke to HQ | **SD-WAN** over several transports with central policy; cloud backbones for inter-region traffic | cost, agility, cloud-first traffic patterns | internet transports have weaker SLAs; policy lives in a vendor controller |
| **Cloud** | one large flat VPC/VNet; full-mesh peering | **hub-and-spoke**: VPC/VNet per workload and environment, a hub via Transit Gateway, Azure Virtual WAN or a hub VNet, central inspection and egress | peering is not transitive and *n* networks need *n(n−1)/2* peerings; a hub keeps routing and inspection central | the hub is a shared fault and cost domain (per-GB processing charges); quotas on routes and attachments |
| **Service exposure** | route whole networks to each other | **private endpoints** (PrivateLink, Private Endpoint, Private Service Connect) expose one service, not a network | overlapping address spaces stop mattering; least privilege at network level | per-endpoint and per-GB cost; DNS integration work |
| **Hybrid** | site-to-site IPsec VPN | **dedicated connections** (Direct Connect, ExpressRoute, Cloud Interconnect), VPN as backup | predictable bandwidth and latency, provider SLA | real resilience needs connections at two locations on separate devices; one connection is a single point of failure |

**Plan the address space once, for the whole estate.** Assign non-overlapping RFC 1918 ranges
across every site, VPC, cluster and likely acquisition before the first network goes live.
Overlap forces NAT between networks forever and breaks hybrid DNS and routing. Kubernetes pod
ranges exhaust address space faster than teams expect. Keep the plan in an IPAM source of
truth (NetBox or the cloud's IPAM), not a spreadsheet.

**IPv6 is now a cost and capacity question, not only a principle.** Public IPv4 addresses
are scarce and metered (AWS has charged for every public IPv4 address since February 2024).
Options are dual-stack (simplest, doubles the policy surface), or IPv6-only inside with
NAT64/DNS64 (RFC 6146, RFC 6147) at the edge for IPv4-only destinations. Pick per estate and
record it as an ADR.

---

## 3. Protocols and transports as architecture choices

**Count round trips before you count milliseconds.** Physics sets the floor
(`quantitative-methods.md` §11): light in fibre travels about 200,000 km/s, so every
100 km of fibre adds about 1 ms of round-trip time before any processing. Then the protocol
multiplies it.

| Choice | Buys | Costs / fails when |
|---|---|---|
| **TCP + TLS 1.3** (RFC 8446) | universal; hardware offloads; one round trip for the TLS handshake after the TCP handshake | head-of-line blocking; the connection breaks when the client changes network |
| **QUIC / HTTP/3** (RFC 9000, RFC 9114) | transport and TLS handshake combined in one round trip; independent streams without head-of-line blocking; connection migration across networks | some middleboxes block or throttle UDP, so a TCP fallback is mandatory; more CPU per byte than offloaded kernel TCP |
| **0-RTT resumption** (TLS 1.3 and QUIC) | no handshake round trip on resumed connections | early data can be **replayed**; only allow it for idempotent requests |
| **HTTP/2 and gRPC** (RFC 9113) | multiplexing, typed contracts, streaming | long-lived connections defeat layer 4 load balancing; gRPC needs **layer 7** balancing or client-side balancing, or one backend takes all the load |
| **WebSockets, SSE** (RFC 6455) | server push to browsers | stateful connections complicate scaling, draining and deployments |
| **MQTT 5.0, AMQP 1.0** (OASIS; ISO/IEC 19464) | constrained devices, store-and-forward, intermittent links | a broker to operate; delivery semantics to choose deliberately |
| **UDP multicast** | one-to-many at line rate (market data, media) | rarely available in public cloud; needs a network that supports it |
| **Time-Sensitive Networking** (IEEE 802.1 TSN) and **PTP** (IEEE 1588) | bounded latency and sub-microsecond time sync on Ethernet for industrial and vehicle networks | specialised switches; the schedule is a design artifact (see `systems-architecture.md` §4) |

**DNS is part of the architecture.** The TTL is the failover knob: a low TTL fails over
faster but raises query volume, and some resolvers and clients ignore it. DNS is also a
shared dependency, as the 2016 Mirai attack on Dyn showed when it took many large sites
offline at once. Hybrid estates need a deliberate design for private zones and conditional
forwarding between on-premises and cloud resolvers. This is a common source of integration
delays.

**Time is infrastructure.** TLS certificate validation, token expiry, distributed tracing,
leases and log correlation all depend on synchronised clocks. Name the time source (NTP
hierarchy, PTP, or the cloud's time service) in the HLD when correctness depends on it.

---

## 4. Traffic management and load balancing

- **Layer 4 vs layer 7.** Layer 4 balancing works on connections: it is fast and
  protocol-agnostic. Layer 7 balancing works on requests: it can route by path or header,
  retry, terminate TLS and apply a WAF, at the price of CPU, and it becomes a trust boundary
  because it sees plaintext.
- **Global traffic.** DNS-based global load balancing is simple but bound by TTLs. **Anycast**
  announces one IP address from many sites and lets BGP pick the nearest; it is how CDNs and
  public DNS absorb load and DDoS. Cloud global layer 7 load balancers combine both.
- **Affinity.** Consistent hashing keeps a key on the same backend as the pool changes
  (Karger et al. 1997; Google's Maglev, NSDI 2016).
- **Health checks can cause the outage they are meant to prevent.** A deep health check that
  tests a shared dependency marks every node unhealthy when that dependency blips, and the
  load balancer removes the whole fleet. Prefer shallow liveness checks plus fail-open
  behaviour when all targets look unhealthy (AWS Builders' Library, *Implementing health
  checks*).
- **Retries multiply.** Three layers that each retry three times turn one failure into up to
  27 requests on the bottom layer, exactly when it is least able to take them. Use timeouts,
  exponential backoff with jitter, retry budgets, and retry at one layer only (AWS Builders'
  Library, *Timeouts, retries, and backoff with jitter*).
- **North–south vs east–west.** An API gateway or ingress handles traffic entering the
  system. A **service mesh** handles service-to-service traffic: uniform mTLS, retries,
  traffic shifting and telemetry, moved out of application code. Sidecar meshes (Istio
  classic, Linkerd) put a proxy in every pod. Sidecarless meshes put layer 4 work in a shared
  per-node proxy and layer 7 only where needed (Istio ambient mode, GA since Istio 1.24 in
  November 2024) or in eBPF (Cilium). A mesh adds a control plane, a hop and operational
  load. Below a few dozen services, cloud-managed identity plus a plain ingress usually wins
  (`enterprise-architecture-bingo.md`).

---

## 5. Network security architecture

`threat_modeling.md` demands identity on every hop. This section covers where the network
controls go, because **zero trust and segmentation complement each other**. Identity decides
whether a call is allowed. Segmentation limits how far an attacker gets when an identity or a
host is compromised.

- **Zero trust** (NIST SP 800-207, 2020): no implicit trust from network location; every
  request is authenticated and authorised by a policy decision point and enforced by a policy
  enforcement point. Google's BeyondCorp (Ward and Beyer, 2014) is the origin case for user
  access. Workload identity comes from SPIFFE/SPIRE or the cloud's workload identity, not
  from IP addresses.
- **Zones and conduits** (IEC 62443): group assets with the same security requirements into
  zones, and allow traffic only through defined, controlled conduits. In operational
  technology, the Purdue reference model gives the classic levels, and the IT/OT boundary is
  a zone boundary with a DMZ.
- **Layered internet ingress:** DDoS absorption (anycast scrubbing) → CDN and WAF → layer 7
  load balancer or API gateway (authentication, rate limits) → service. Each layer is a
  separate failure and cost domain. Document which layer owns which control.
- **Egress control is the forgotten half.** Default-deny egress through an egress proxy or
  firewall with FQDN allow-lists stops data exfiltration, command-and-control callbacks,
  and SSRF pivots, and it forces software supply chain traffic through mirrors you control.
  The 2019 Capital One breach went from SSRF to the instance metadata service to bulk data
  exfiltration. IMDSv2 and egress control each break that chain.
- **Private access to managed services.** Use private endpoints instead of public endpoints
  with IP allow-lists.
- **User access.** ZTNA replaces broad network-level VPN access. **SASE/SSE** (Gartner, 2019)
  converges SD-WAN, secure web gateway, CASB, ZTNA and firewall as a service into one
  cloud-delivered policy layer. Adopt it as a product choice with an ADR, not as a buzzword.
- **Routing and naming security.** For organisations with their own address space and ASN,
  publish ROAs and filter with RPKI route-origin validation (RFC 6480, RFC 6811) against
  hijacks and leaks. Sign zones with DNSSEC where the registry supports it, and use encrypted
  DNS (DoT, DoH) on resolvers you control.
- **Encrypt every link, including east–west.** mTLS between services; WireGuard or IPsec
  between sites; MACsec (IEEE 802.1AE) on physical links you do not fully control.

**Post-quantum cryptography starts in the network.** Encrypted traffic recorded today can be
decrypted once a capable quantum computer exists ("harvest now, decrypt later"), so key
exchange is the most urgent surface. NIST published ML-KEM (FIPS 203), ML-DSA (FIPS 204) and
SLH-DSA (FIPS 205) in August 2024. NIST IR 8547 (draft) proposes deprecating RSA and
elliptic-curve public-key algorithms after 2030 and disallowing them after 2035. Hybrid key
exchange (X25519 combined with ML-KEM-768) is already the default in current Chrome, Firefox
and Edge and across major CDNs. The architectural requirements are:

1. **Crypto-agility as a `Q.xx`** (maintainability/modifiability): algorithms can change
   through configuration at every TLS termination point you own.
2. **An inventory** of where cryptography is used (a cryptographic bill of materials), ranked
   by how long the protected data must stay confidential.
3. **Size budgets.** Post-quantum keys and signatures are much larger. Check handshake size,
   MTU and fragmentation, and latency on constrained links before switching signatures.

**Flow matrix.** For any HLD or SAD with more than one zone, add a flow table to §8: source
zone and component, destination, protocol and port, authentication, encryption, and the
driver or `F.xx` that justifies the flow. Every arrow that crosses a zone boundary gets a
STRIDE row. A flow without a justification is a finding.

---

## 6. Edge, CDN and placement

Where compute runs (device, edge point of presence, region, central) follows from four
drivers: the **latency budget** (physics, §3), **bandwidth and backhaul cost**, **data
residency**, and **tolerance for disconnection**.

- **CDN caching** for static content and cacheable API responses is the cheapest latency win
  there is. Design cache keys and invalidation deliberately.
- **Edge compute** (V8 isolates, Wasm) suits authentication, routing, personalisation and
  request shaping. Keep authoritative state in a region: edge runtimes are constrained and
  strong consistency across points of presence is expensive.
- **Disconnected or intermittent sites** (factories, vessels, stores, vehicles) need local
  autonomy, store-and-forward and conflict handling as explicit design elements, not as
  exception paths.
- **5G and multi-access edge computing** place compute in the operator's network for very
  low latency. They are worth it only for a measured latency driver that a nearby cloud
  region cannot meet.

---

## 7. Operating the network as code

- **Declarative intent, versioned.** Terraform or the provider's IaC for cloud networking;
  Ansible or Nornir for devices; OpenConfig YANG models with gNMI for configuration and
  streaming telemetry instead of SNMP polling.
- **Verify before you push.** Most network outages are caused by changes. Analyse
  configurations and reachability before deployment (Batfish), stage rollouts per site or
  region, and use automatic rollback (confirmed commits). A reachability check is a natural
  **fitness function** (`automation.md`).
- **One source of truth** for addresses, devices and circuits (NetBox or equivalent) that the
  automation reads from.
- **Network SLIs** are loss, latency, jitter and availability per path, measured by
  synthetic probes and flow logs (VPC Flow Logs, eBPF-based tools such as Cilium Hubble), and
  tied to SLOs like any other operational `Q.xx` (`operability.md`).
- **Out-of-band access and break-glass procedures** are part of the design (§1).

---

## 8. Legacy, modern, future

| Area | Legacy | Modern | Next |
|---|---|---|---|
| Datacenter fabric | three-tier + spanning tree | spine-leaf Clos + EVPN-VXLAN | optical circuit switching (Google Jupiter); AI training fabrics on RDMA (InfiniBand, RoCEv2) and Ultra Ethernet (UEC 1.0, June 2025) |
| WAN | MPLS leased lines | SD-WAN + cloud backbones | SASE; network as a service |
| Network functions | hardware appliances | virtual appliances (ETSI NFV) → cloud-native network functions | DPU/SmartNIC offload; eBPF/XDP data planes |
| Addressing | IPv4 + NAT | dual-stack | IPv6-only inside, NAT64 at the edge |
| Access | perimeter firewall + VPN | zero trust, ZTNA | continuous, identity- and posture-based policy everywhere |
| Operations | CLI + SNMP | IaC + streaming telemetry | intent-based, verified, closed-loop automation |
| Mobile core | 4G EPC | 5G core service-based architecture (3GPP Release 15+), network slicing | 5G-Advanced (Release 18+); 6G research (IMT-2030) |
| Transport crypto | TLS 1.2 with RSA key exchange | TLS 1.3 with ECDHE | hybrid post-quantum key exchange now; post-quantum signatures next |
| Application transport | HTTP/1.1 over TCP | HTTP/2, gRPC | HTTP/3 over QUIC; MASQUE proxying |

**AI clusters change the priorities.** In a large training cluster the network determines
how much of the GPU time is used. Collective operations are synchronous, so the slowest link
sets the pace, and tail latency and congestion control matter more than average bandwidth.
Rail-optimised topologies, lossless or near-lossless transport, and job-aware placement are
architectural decisions there, with their own ADRs.

---

## 9. Documenting the network

The C4 model has no network view. Add one when a system spans more than one zone, uses hybrid
connectivity, or has a non-trivial ingress or egress path:

1. a **network and trust-zone view** — zones as subgraphs, containers placed in them, edges
   labelled with protocol, port, authentication and encryption (snippet in
   `mermaid-guide.md`, "Network & trust-zone view");
2. the **flow matrix** (§5) in HLD/SAD §8;
3. for shared networks only, an **IP plan** table (range, zone, owner, purpose) in the
   network's own SAD.

The HLD links to the shared network's SAD or ADRs instead of copying it.

---

## 10. Over-engineering traps, network edition

- **A service mesh for a handful of services.** Cloud-managed identity, mTLS in the client
  library and a plain ingress cover it.
- **Multi-region active-active networking without an RTO or latency driver.** The global
  load balancing, data replication and failover testing cost far more than the outage they
  insure against.
- **Dedicated interconnects without a bandwidth, latency or compliance driver.** A VPN pair
  is often enough at first.
- **A custom SDN or overlay** where the cloud's native networking does the job.
- **Per-team networks without a hub plan.** It ends in a peering mesh and overlapping
  address ranges.
- **The opposite mistake:** a flat network "because we have zero trust". Identity without
  segmentation turns one stolen credential into a reachable estate.

---

## 11. Sources

| Topic | Source |
|---|---|
| Datacenter Clos fabrics | C. Clos (Bell System Technical Journal 1953); M. Al-Fares et al., *A Scalable, Commodity Data Center Network Architecture* (SIGCOMM 2008); A. Singh et al., *Jupiter Rising* (SIGCOMM 2015); L. Poutievski et al., *Jupiter Evolving* (SIGCOMM 2022) |
| Overlay, VPN | RFC 7348 (VXLAN), RFC 7432 and RFC 8365 (EVPN), RFC 4364 (BGP/MPLS IP VPNs) |
| Transport and web protocols | RFC 9000 (QUIC), RFC 9114 (HTTP/3), RFC 9113 (HTTP/2), RFC 8446 (TLS 1.3), RFC 6455 (WebSocket) |
| IPv6 transition | RFC 8200 (IPv6), RFC 6146 (NAT64), RFC 6147 (DNS64) |
| Routing security | RFC 6480 (RPKI), RFC 6811 (origin validation) |
| Load balancing | D. Karger et al., *Consistent Hashing* (STOC 1997); D. Eisenbud et al., *Maglev* (NSDI 2016) |
| Static stability, health checks, retries | AWS Builders' Library |
| Zero trust | NIST SP 800-207 (2020); R. Ward, B. Beyer, *BeyondCorp* (;login: 2014); SPIFFE |
| Zones and conduits | IEC 62443; Purdue Enterprise Reference Architecture |
| Post-quantum | NIST FIPS 203, 204, 205 (2024); NIST IR 8547 (draft, 2024) |
| Network functions virtualisation | ETSI NFV ISG |
| AI and HPC Ethernet | Ultra Ethernet Consortium, *UEC Specification 1.0* (June 2025) |
| Outage case studies | Facebook Engineering, *More details about the October 4 outage* (2021) |
| Orientation | J. Kurose, K. Ross, *Computer Networking: A Top-Down Approach*; L. Peterson, B. Davie, *Computer Networks: A Systems Approach* |

Cross-references: physics and TCP maths — `quantitative-methods.md` §11; identity and
STRIDE — `threat_modeling.md`; cloud landing zones and failure domains —
`cloud-architecture.md`; the kernel side of the data plane (eBPF, XDP, kernel bypass) —
`systems-architecture.md` §2.
