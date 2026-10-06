# Systems architecture — kernel, OS, isolation, real-time

**Load when** the work builds system software (kernel, hypervisor, driver, firmware,
container runtime, storage/I/O layer); chooses the isolation boundary between workloads;
chooses an OS or RTOS base; must meet a `Q.xx` only the substrate can meet (jitter,
worst-case response time, boot time, density); or hits a platform end-of-support date.
Otherwise the OS stays a label in HLD §6 and you do not load this file.

**Grounding rule.** Every rule below carries a source `[Sn]` (table at the end). Do not add
claims to architecture documents that you cannot cite the same way. Version numbers,
support dates, quotas and prices change: look them up in the vendor's current
documentation when you write, put the URL next to the value, and never quote them from
memory.

---

## 1. Derive the substrate from evidence before asking

Read these before you ask anyone anything (`methods.md` §10):

| Evidence | What it tells you |
|---|---|
| `FROM` lines in Dockerfiles; `/etc/os-release` in images; AMI/image IDs in IaC | OS distribution and version → support horizon (§4) |
| Kubernetes manifests: `runtimeClassName`, `securityContext.privileged`, `hostNetwork`, `hostPID`, `hostPath`, added capabilities, seccomp profile, `resources.limits.cpu` | the actual isolation boundary and CPU-throttling exposure (§2.1, §2.3) |
| IaC instance and node-pool types, confidential-VM flags, dedicated hosts | CPU architecture, isolation, co-tenancy |
| Kernel boot args (`isolcpus`, `nohz_full`), `sysctl` files, kernel `.config` | real-time or performance tuning already in place |
| Source: `epoll`/`kqueue`/IOCP/`io_uring` calls, DPDK/SPDK/AF_XDP libraries, `.ko` modules, eBPF programs | I/O model, kernel bypass, kernel-mode code (§2.3) |
| RTOS config (`FreeRTOSConfig.h`, Zephyr `prj.conf`, Kconfig), linker scripts, safety plan, MISRA deviations | embedded base, task model, integrity level (§2.2) |

Ask only for what evidence cannot give: **who supplies the code that runs here** (the trust
model), the **integrity level** if any, the **timing requirement with its response
measure**, and the **field life** of the product.

---

## 2. Decide

### 2.1 Isolation boundary

1. **Classify the code** that will share the host: one owner and trusted, or several
   tenants / untrusted code.
2. **Containers share the host kernel**, so a kernel compromise reaches every container on
   it [S1]. For one trusted owner that is acceptable; group containers on hosts by
   sensitivity [S1].
3. **For untrusted or multi-tenant code, require more than namespaces.** Kubernetes itself
   states that namespaces are not a hard isolation boundary and points to sandboxed
   runtimes or separate nodes/VMs for strong isolation [S2][S3]. Hardware virtualisation
   with a minimal VMM is the boundary AWS chose for multi-tenant serverless; the published
   figures are under 125 ms to guest init and under 5 MiB VMM overhead [S4].
4. **Shared hardware leaks across software boundaries** (Spectre, Meltdown) [S5][S6]. When a
   tenant's threat model includes side channels, require no co-residency on SMT siblings
   (Linux core scheduling exists for this [S7]) or dedicated hosts.
5. **Confidential computing** protects data in use from the host operator through a
   hardware TEE with attestation [S8]. It only works if secrets are released after the
   attestation is verified [S9]: make that a step in the deployment flow, not a slide.
6. **Record** an ADR whose driver is the trust model, the option chosen, and the density or
   cost given up (HLD §9).

### 2.2 OS or RTOS base

- **General-purpose servers:** default to the distribution the organisation already
  operates (the boring-technology rule, `anti_over_engineering.md`). The decision that
  matters is the support horizon (§4).
- **A small trusted base or fault containment is a driver** (certification, security
  kernel, drivers of unknown quality): consider a microkernel or separation kernel. Drivers
  have measured error rates three to seven times higher than the rest of a monolithic
  kernel [S10] and caused most crashes in Windows XP [S11]; a small kernel is what made a
  full functional-correctness proof possible (seL4) [S12].
- **Hard real-time:** the response measure is a **worst-case bound**, never a percentile
  [S13]. Prove it with schedulability analysis (`quantitative-methods.md` §12). A Linux
  latency test reports the maximum *observed*, which is evidence, not a bound — label it so.
- **Shared resources across priorities:** name the locking protocol (priority inheritance
  or priority ceiling) [S14]. Unbounded priority inversion reset Mars Pathfinder until
  priority inheritance was enabled [S15].
- **Mixed criticality on one chip:** partition in space and time (ARINC 653) so one
  partition cannot change another's timing [S16][S17].
- **Integrity level applies (SIL/ASIL/DAL/class):** identify the standard (§2.4) and ask the
  OS vendor for the evidence it requires for pre-existing software, such as a safety manual
  or certificate [S18]. Record the level as `C.xx`.

### 2.3 Kernel-level changes that need an ADR and an evidence gate

| Change | Gate before deciding | Why it is significant |
|---|---|---|
| I/O model (blocking → readiness → completion → kernel bypass) | a profile showing the kernel I/O path is the bottleneck [S19] | rewrites the program's structure; bypass gives up the kernel's security and management functions [S20] |
| Adopt `io_uring` | threat model row for it | 60% of exploits submitted to Google's kernel bounty in 2022 used it; Google disabled it on ChromeOS and production servers [S21] |
| CPU limits on latency-critical workloads | load test with the limits in place | bandwidth control throttles a group for the rest of the period once its quota is spent, which shows up as tail latency, not in average CPU [S22] |
| Third-party kernel-mode component (agent, driver) | staged rollout and rollback for its updates, including content updates | a faulty update to one kernel-mode security driver crashed about 8.5 million Windows devices in July 2024 [S23] |
| Kernel extension | prefer eBPF over a loadable module where the use case fits | eBPF programs pass a verifier before loading; modules run unchecked with full privilege [S24] |
| Language for new system components | none; record it | memory-safety bugs are about 70% of Microsoft's CVEs [S25]; CISA/NSA ask vendors for memory-safe roadmaps [S26] |
| Boot or update chain | — | platform firmware must be protected, detect corruption and recover [S27] |

### 2.4 Which safety or product-security standard applies

Each cell names the governing standard itself; use the edition the project is bound to.

| Domain | Safety | Security |
|---|---|---|
| Generic / industrial | IEC 61508 | IEC 62443 |
| Automotive | ISO 26262 | ISO/SAE 21434; UN R155, R156 |
| Avionics | DO-178C (+ DO-330, DO-297) | DO-326A / ED-202A |
| Medical | IEC 62304 | IEC 81001-5-1 |
| Railway | EN 50716:2023 (replaced EN 50128 and EN 50657) [S28] | CLC/TS 50701 |
| Any product with digital elements on the EU market | — | Cyber Resilience Act, Reg. (EU) 2024/2847: reporting obligations from 11 Sep 2026, other obligations from 11 Dec 2027 [S29] |

Hazards become `Q.xx` against the ISO/IEC 25010:2023 **Safety** characteristic
(`standards.md`). Link the safety case from `AD.md`; do not retype it.

### 2.5 Proven is not the same as current — separate the two questions

Linux reimplements the Unix design: the core abstractions (processes created with `fork`,
everything as a file, users and a superuser, synchronous system calls) were published in
1974 [S33], the POSIX interface was standardised in 1988 [S34], and Linux itself dates from
1991 [S49]. That design is **proven**: its track record, drivers, tooling and skills are real
evidence and the reason it is the default. Some of its assumptions are **no longer how the
research community would build an OS from scratch** [S35][S36]. Treat these as two separate
questions in every substrate decision, and never let one answer the other.

1. **Name the inherited assumption** behind the mechanism the decision touches:

| Mechanism | Assumption of its era | What has changed (source) | Clean-sheet direction | Inside Linux today |
|---|---|---|---|---|
| `fork` + `exec` | copying a small address space is cheap | fork is slow for large address spaces, unsafe with threads, and constrains OS design; the authors argue it should be deprecated [S37] | spawn-style creation | `posix_spawn` [S34], `vfork`/`clone3` |
| Synchronous, one-at-a-time system calls; kernel on every I/O | devices are slow relative to a mode switch | at microsecond-scale devices, mode switches and cache pollution dominate [S38]; dataplane designs put the kernel in the control plane only [S39][S40] | asynchronous, batched submission; kernel as control plane | `io_uring` (with its attack-surface caveat, §2.3), AF_XDP [S51] |
| Monolithic kernel in C, one privileged address space | one trusted team, few drivers, no hostile network | 40% of critical Linux CVEs would be eliminated, and almost all others reduced below critical, by a verified-microkernel design [S41]; memory-safety bugs dominate CVEs [S25] | microkernel with user-mode servers; memory-safe languages | Rust for new drivers [S50]; eBPF instead of modules [S24] |
| Ambient authority: user IDs, a superuser, global namespaces | a shared time-sharing machine with trusted users | programs act with authority they did not intend to use (the confused deputy) [S42] | capabilities: a program holds only the handles it was given | Capsicum on FreeBSD [S43]; Landlock, seccomp, namespaces on Linux [S44] |
| File durability through `write`/`fsync`/`rename` conventions | simple disks, single writer | applications routinely get crash consistency wrong on POSIX file systems [S45], and `fsync` failure handling is unreliable [S46] | explicit, ordered or transactional storage interfaces | delegate durability to a storage engine that has been tested for it; do not hand-roll |
| The OS controls one homogeneous machine | the CPU is the computer | modern platforms are many cores, accelerators and firmware-controlled processors the OS does not govern [S36][S47] | the platform as a distributed system | treat firmware, BMC and device processors as TCB and threat-model them (§2.3, [S27]) |

2. **Decide per mechanism**, and record which of the three the ADR chose:
   - **Work with it** — the default when building *on* Linux: the proven design plus its
     ecosystem beats an untested alternative, the "worse is better" effect [S48], and
     `anti_over_engineering.md` (Chesterton's fence, boring technology) applies.
   - **Work around it** — use the modern mechanism *inside* the proven OS (column 5), when a
     measured `Q.xx` hits the inherited assumption.
   - **Replace it** — choose or build a clean-sheet design (microkernel, separation kernel,
     unikernel, capability OS) only when a driver is **structurally** unreachable with the
     inherited design: a TCB small enough to verify or certify, untrusted multi-tenancy with
     a small attack surface, or a hard real-time bound. Name that driver in the ADR.
3. **Do not copy an inherited idiom into an interface you design.** A new platform API,
   plug-in model, agent runtime or device OS starts from the clean-sheet column: explicit
   capabilities instead of ambient authority, asynchronous submission, explicit durability.
   Copying the legacy idiom is acceptable only with a recorded compatibility driver.

---

## 3. Record

| Where | What |
|---|---|
| PRD | `Q.xx` for jitter, worst-case response, boot time, density; `C.xx` for integrity level, support horizon (with URL), CPU architecture, minimum kernel |
| HLD §6 | per container: OS + kernel line, runtime, isolation boundary, CPU architecture, node pool |
| HLD §7 | I/O and concurrency model, scheduling policy, update and rollback mechanism |
| ADR | for every substrate decision: the inherited assumption it touches and whether it works with, around, or replaces it (§2.5) |
| HLD §8 | threat rows from §5 below |
| SD | task set, priorities, locking protocol, schedulability result (real-time only) |
| Fitness functions (`automation.md`) | latency test under load as a gate; seccomp-profile drift; image CVE scan; kernel hardening config check; boot-time budget |

---

## 4. Lifecycle — dates come from the vendor, not from memory

1. List every platform component found in §1 (OS, kernel line, RTOS, hypervisor, runtime).
2. For each, look up the vendor's published end of standard and extended support; record
   it as a `C.xx` with the date **and the URL**.
3. Running unsupported software in critical systems is on CISA's list of bad practices
   [S30]: an entry past its date is a threat-model finding; an entry inside the planning
   horizon is a roadmap work package (`migration.md` §7).
4. If the product's field life exceeds the support horizon, record the gap as a risk with a
   plan (vendor extended support, or a long-term maintained kernel such as the Civil
   Infrastructure Platform's [S31]).
5. A CPU-architecture or OS-family change is an ADR with measured price-performance and the
   components that block it.

---

## 5. Flag in review

Raise each as a finding with its source:

- untrusted or multi-tenant code on shared-kernel containers without a sandbox or VM [S1][S2];
- privileged containers, host namespaces or `hostPath` mounts without a recorded reason [S32];
- a hard real-time requirement stated as a percentile, or a "bound" that is a test maximum [S13];
- shared resources across priorities with no named locking protocol [S14];
- kernel-mode third-party code without staged update rollout [S23];
- kernel bypass, custom modules or real-time tuning without the profile or `Q.xx` that
  justifies them (`anti_over_engineering.md`, Metrics First) [S19];
- a platform component past end of support, or with no recorded support date [S30].
- a substrate ADR that answers "is it proven?" but not "would we build it this way now?",
  or the reverse: rejecting Linux because its design is old, with no driver it
  structurally cannot meet (§2.5) [S41][S48];
- a new interface that copies `fork`-style creation, ambient authority or implicit
  durability without a compatibility driver (§2.5) [S37][S42][S45].

---

## Sources

| ID | Source |
|---|---|
| S1 | NIST SP 800-190, *Application Container Security Guide* (2017), https://doi.org/10.6028/NIST.SP.800-190 |
| S2 | Kubernetes documentation, *Multi-tenancy*, https://kubernetes.io/docs/concepts/security/multi-tenancy/ |
| S3 | Kubernetes documentation, *Runtime Class*, https://kubernetes.io/docs/concepts/containers/runtime-class/ |
| S4 | A. Agache et al., *Firecracker: Lightweight Virtualization for Serverless Applications*, NSDI 2020 |
| S5 | P. Kocher et al., *Spectre Attacks: Exploiting Speculative Execution*, IEEE S&P 2019 |
| S6 | M. Lipp et al., *Meltdown: Reading Kernel Memory from User Space*, USENIX Security 2018 |
| S7 | Linux kernel documentation, *Core Scheduling*, https://docs.kernel.org/admin-guide/hw-vuln/core-scheduling.html |
| S8 | Confidential Computing Consortium, *Confidential Computing: Hardware-Based Trusted Execution for Applications and Data* (white paper) |
| S9 | RFC 9334, *Remote ATtestation procedureS (RATS) Architecture* (2023) |
| S10 | A. Chou et al., *An Empirical Study of Operating Systems Errors*, SOSP 2001 |
| S11 | M. Swift, B. Bershad, H. Levy, *Improving the Reliability of Commodity Operating Systems*, SOSP 2003 |
| S12 | G. Klein et al., *seL4: Formal Verification of an OS Kernel*, SOSP 2009 |
| S13 | G. Buttazzo, *Hard Real-Time Computing Systems*, 3rd ed., Springer 2011 |
| S14 | L. Sha, R. Rajkumar, J. Lehoczky, *Priority Inheritance Protocols*, IEEE Trans. Computers 39(9), 1990 |
| S15 | G. Reeves (JPL), *What really happened on Mars?*, account of the Mars Pathfinder resets, 1997 |
| S16 | ARINC Specification 653, *Avionics Application Software Standard Interface* |
| S17 | RTCA DO-297, *Integrated Modular Avionics Development Guidance* |
| S18 | IEC 61508-3:2010 (pre-existing software elements); IEC TS 61508-3-1:2016 (proven-in-use) |
| S19 | B. Gregg, *Systems Performance*, 2nd ed., Addison-Wesley 2020 |
| S20 | T. Høiland-Jørgensen et al., *The eXpress Data Path*, CoNEXT 2018 |
| S21 | Google Security Blog, *Learnings from kCTF VRP's 42 Linux kernel exploits submissions*, June 2023 |
| S22 | Linux kernel documentation, *CFS Bandwidth Control*, https://docs.kernel.org/scheduler/sched-bwc.html |
| S23 | Microsoft, *Helping our customers through the CrowdStrike outage*, 20 July 2024 |
| S24 | Linux kernel documentation, *eBPF verifier*, https://docs.kernel.org/bpf/verifier.html |
| S25 | Microsoft Security Response Center, *A proactive approach to more secure code*, July 2019 |
| S26 | CISA, NSA et al., *The Case for Memory Safe Roadmaps*, December 2023 |
| S27 | NIST SP 800-193, *Platform Firmware Resiliency Guidelines* (2018) |
| S28 | CENELEC EN 50716:2023, *Railway applications — Requirements for software development* |
| S29 | Regulation (EU) 2024/2847 (Cyber Resilience Act), Art. 14 and Art. 71 |
| S30 | CISA, *Bad Practices* (use of unsupported or end-of-life software) |
| S31 | Civil Infrastructure Platform, super long-term support kernels, https://www.cip-project.org |
| S32 | NSA and CISA, *Kubernetes Hardening Guide* (2022) |
| S33 | D. Ritchie, K. Thompson, *The UNIX Time-Sharing System*, CACM 17(7), 1974 |
| S34 | IEEE Std 1003.1 (POSIX.1), first edition 1988; current edition defines `posix_spawn` |
| S35 | A. Baumann et al., *The Multikernel: A New OS Architecture for Scalable Multicore Systems*, SOSP 2009 |
| S36 | T. Roscoe, *It's Time for Operating Systems to Rediscover Hardware*, keynote, USENIX OSDI/ATC 2021 |
| S37 | A. Baumann, J. Appavoo, O. Krieger, T. Roscoe, *A fork() in the road*, HotOS 2019 |
| S38 | L. Soares, M. Stumm, *FlexSC: Flexible System Call Scheduling with Exception-Less System Calls*, OSDI 2010 |
| S39 | S. Peter et al., *Arrakis: The Operating System is the Control Plane*, OSDI 2014 |
| S40 | A. Belay et al., *IX: A Protected Dataplane Operating System for High Throughput and Low Latency*, OSDI 2014 |
| S41 | S. Biggs, D. Lee, G. Heiser, *The Jury Is In: Monolithic OS Design Is Flawed*, APSys 2018 |
| S42 | N. Hardy, *The Confused Deputy (or why capabilities might have been invented)*, ACM SIGOPS OSR 22(4), 1988 |
| S43 | R. Watson, J. Anderson, B. Laurie, K. Kennaway, *Capsicum: Practical Capabilities for UNIX*, USENIX Security 2010 |
| S44 | Linux kernel documentation, *Landlock: unprivileged access control*, https://docs.kernel.org/userspace-api/landlock.html |
| S45 | T. S. Pillai et al., *All File Systems Are Not Created Equal: On the Complexity of Crafting Crash-Consistent Applications*, OSDI 2014 |
| S46 | A. Rebello et al., *Can Applications Recover from fsync Failures?*, USENIX ATC 2020 |
| S47 | A. Baumann, *Hardware is the new software*, HotOS 2017 |
| S48 | R. Gabriel, *Lisp: Good News, Bad News, How to Win Big* ("worse is better"), 1991 |
| S49 | L. Torvalds, announcement of Linux on comp.os.minix, 25 August 1991 |
| S50 | Linux kernel documentation, *Rust*, https://docs.kernel.org/rust/index.html |
| S51 | Linux kernel documentation, *AF_XDP*, https://docs.kernel.org/networking/af_xdp.html |
