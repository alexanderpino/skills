# Systems architecture — kernels, operating systems, isolation, real-time

The rest of this skill stops at the container boundary. Below it, the HLD deployment view
holds one label, `"<OS / runtime>"`, and for most work that is correct: the operating system
is a commodity and the interesting decisions live above it. This file is for the cases where
the label is the decision. Read it when:

- you are **building system software** — a kernel, hypervisor, driver, firmware, container
  runtime, or the storage/I/O layer of a database or broker;
- you are **choosing the isolation boundary** between workloads (process, container,
  sandbox, microVM, VM, confidential VM, dedicated host), above all for multi-tenant or
  untrusted code;
- you are **choosing the OS base for a product** (RTOS vs embedded Linux vs a separation
  kernel) or a fleet (distribution, kernel line, CPU architecture);
- a `Q.xx` scenario **can only be met below the application** — tail latency, jitter, boot
  time, density, determinism, a worst-case execution bound;
- a **platform lifecycle** event forces a decision — an OS reaching end of support, a kernel
  upgrade, a move from x86 to Arm, a mainframe exit.

**Altitude.** An operating system or hypervisor *as the product* is **software** altitude
with an unusual entity of interest: its users are programs, and its published interface is
the system-call ABI and the driver model. Choosing an isolation boundary or OS base *for an
application* is an ADR at **software** or **solution** altitude. A fleet-wide OS, kernel or
CPU-architecture standard is an **enterprise** technology building block (TOGAF Phase D) and
usually a principle (`PR.xx`).

The stance from `anti_over_engineering.md` holds here too, and is easier to violate: kernel
bypass, custom kernel modules and real-time tuning are expensive to build and expensive to
operate. Every mechanism below is justified by a measured driver or not at all.

---

## 1. Kernel structure — the styles and what they buy

The structural question for any operating system is **what runs in privileged mode**,
because everything there shares one fault domain and one trusted computing base (TCB).

| Style | Idea | Examples | Buys | Costs |
|---|---|---|---|---|
| **Monolithic** (with loadable modules) | file systems, network stack, drivers all in one privileged address space | Linux, FreeBSD, OpenBSD | fastest in-kernel paths; the largest driver and tooling ecosystem | one buggy driver can take the machine down; TCB of millions of lines |
| **Microkernel** | kernel keeps only address spaces, threads, IPC and scheduling; drivers, file systems and network stacks run as user-mode servers | seL4, QNX Neutrino, the L4 family, MINIX 3, Zircon (Fuchsia) | fault isolation, restartable drivers, small TCB, formal verification becomes feasible | a service call becomes IPC; smaller ecosystem; performance depends on IPC design |
| **Hybrid** | microkernel-derived structure, but most services run in kernel mode for speed | Windows NT, XNU (macOS/iOS: Mach + BSD) | compatibility and performance with a modular internal design | the TCB of a monolith; most isolation benefits are given back |
| **Exokernel / library OS** | kernel only multiplexes hardware securely; abstractions live in user-space libraries | MIT Exokernel, Demikernel; DPDK/SPDK as the pragmatic cousin | application-specific abstractions, lowest latency | each application inherits hard problems the OS used to solve |
| **Unikernel** | application + only the OS library code it needs, linked into one single-address-space image on a hypervisor | MirageOS, Unikraft | tiny image, fast boot, small attack surface | no shell, no standard debugging or observability; the hypervisor carries all isolation |
| **Multikernel** | the OS as a distributed system: one kernel per core, communicating by messages | Barrelfish | scales across many-core and heterogeneous hardware | research; little production use |

Three pieces of history keep this table honest:

- **"Microkernels are slow" is a claim about Mach, not a law.** First-generation
  microkernels paid heavily for IPC. Liedtke's L4 showed IPC could be made an order of
  magnitude cheaper by designing the kernel around it, and stated the design rule still used
  today: a concept is tolerated inside the microkernel only if moving it outside would
  prevent the system's required functionality (Liedtke, *On µ-Kernel Construction*, SOSP
  1995).
- **A small TCB is what makes proof possible.** seL4 was the first general-purpose OS kernel
  with a machine-checked proof of functional correctness (Klein et al., SOSP 2009), later
  extended to integrity, confidentiality and binary correctness. That only works because the
  kernel is around ten thousand lines of C. You cannot prove a monolith.
- **Drivers are where kernels break.** Device drivers showed error rates three to seven
  times higher than the rest of the kernel (Chou et al., SOSP 2001), and drivers caused
  most Windows XP crashes (Swift et al., *Nooks*, SOSP 2003). The July 2024 CrowdStrike
  incident, a faulty content update read by a kernel-mode security driver that crashed about
  8.5 million Windows machines (Microsoft's estimate), is the same lesson at fleet scale:
  **third-party code in kernel mode has a whole-machine blast radius.** Microsoft's response
  was to start moving security vendors out of the kernel.

**How to decide.** The architectural question is *how large the trusted base may be, and
what must survive a failed component*. For general-purpose servers and desktops the
monolithic kernel wins on ecosystem and the choice is really a distribution and lifecycle
choice (§5). Reach for a microkernel or separation kernel when an assurance driver
dominates: certification (§4), a small verifiable TCB, mixed-criticality on one chip, or
fault containment that must not depend on driver quality. The same idea at application level
is the **microkernel (plug-in) architecture style** in `structure.md` §2.

---

## 2. The kernel mechanisms that are architecture

Most kernel behaviour is implementation detail. These mechanisms are not, because they fix
a quality ceiling, a security surface or a compatibility contract that is expensive to change
later. Each one is ADR-worthy when it is chosen or changed.

| Mechanism | Options | What it decides |
|---|---|---|
| **Kernel/user boundary (ABI)** | the system-call ABI; vDSO; Windows' stable Win32 API over unstable syscall numbers | a published contract (`interfaces.md`); Linux's rule is that changes must not break user space |
| **I/O model** | thread per connection (blocking) · readiness (`epoll`, `kqueue`) · completion (IOCP, `io_uring`) · kernel bypass (DPDK, SPDK, RDMA, AF_XDP) | throughput per core, tail latency, how much of the kernel's tooling and security you keep |
| **Scheduling** | fair share (Linux EEVDF since 6.6, replacing CFS) · real-time classes (`SCHED_FIFO`, `SCHED_DEADLINE`) · `PREEMPT_RT` (mainline since 6.12) · BPF-defined schedulers (`sched_ext`, 6.12) · CPU isolation and pinning | latency distribution and jitter under contention |
| **Memory** | overcommit and OOM policy · NUMA placement · huge pages · page cache vs direct I/O · cgroup memory limits | predictability under pressure; which process dies first |
| **Drivers** | in-kernel · user-mode (VFIO/UIO, Windows UMDF, Fuchsia driver components) | fault isolation vs performance (§1) |
| **Extensibility** | loadable kernel modules · eBPF (verifier-checked, bounded programs for networking, tracing, security and scheduling) | whether extension code can crash or compromise the kernel |
| **Boot and update chain** | UEFI Secure Boot · measured boot (TPM 2.0) · verified boot (dm-verity, Android Verified Boot) · image-based, A/B-updated OS (Bottlerocket, Flatcar, Talos, ChromeOS) | integrity of what runs, and whether a bad update can be rolled back |

Some forces in this table are worth spelling out, because teams get them wrong repeatedly.

**The I/O model is a one-way-ish door.** Thread-per-connection is the simplest model and is
fine until memory per thread and context switches dominate (the C10K problem, Kegel 1999).
Readiness models scale to very large connection counts. Completion models cut system calls
further. Kernel bypass gives the lowest latency, but you then own the driver, give up the
kernel's firewall, tracing and accounting, and burn cores on busy-polling. Each step changes
how the whole program is written, so moving between them is a rewrite rather than a
refactor. Newer is also not automatically safer: Google reported that 60% of the exploits
submitted to its kernel bug bounty in 2022 targeted `io_uring`, and disabled it on ChromeOS
and its production servers and blocked it for Android apps (Google Security Blog, June 2023).
Choosing an I/O interface means choosing an attack surface as well.

**CPU limits are a latency decision, not just a cost one.** Under cgroup CPU bandwidth
control, a container that exhausts its quota early in a scheduling period is throttled for
the rest of it, even if its *average* use is far below the limit. The result is tail-latency
spikes that do not show in average CPU graphs. Whether a platform sets CPU limits, only
requests, or pins latency-critical work to isolated cores is a platform-wide decision worth
an ADR.

**Memory safety is a kernel-architecture concern now.** Around 70% of the vulnerabilities
Microsoft assigns CVEs to are memory-safety bugs (MSRC, 2019), and Chromium reports a similar
share. That is the driver behind Rust support in Linux (since 6.1), Rust components in the
Windows kernel, and memory-safe Android system code. Picking the language of a new driver or
system component is a security decision with a measurable base rate.

**Measure before you change any of this.** Profile with `perf`, eBPF tooling (`bpftrace`,
BCC), `ftrace`, and for real-time work `cyclictest` under a load generator such as
`stress-ng`. A mechanism change without a profile that shows the kernel is the bottleneck is
the systems version of Resume Driven Development.

---

## 3. Isolation and virtualisation — choosing the boundary

The question is not "containers or VMs". It is **what an attacker must break to get from one
workload to another, and what that boundary costs in density, startup time and
compatibility.** Start from the trust model, then choose the cheapest boundary that meets it.

| Boundary | Mechanism | What the attacker must break | Startup | Density | Fits |
|---|---|---|---|---|---|
| **Process** | address spaces, users, seccomp, LSM | the kernel or its permission model | ms | highest | trusted code of one owner |
| **Container** | namespaces + cgroups + capabilities + seccomp + SELinux/AppArmor; **shared host kernel** | one kernel privilege-escalation bug | ms–1 s | very high | trusted workloads of one tenant; packaging and scheduling |
| **Sandboxed container** | gVisor (a user-space kernel intercepting syscalls) · Kata Containers (a lightweight VM per pod) | the sandbox kernel plus a narrow host interface, or a hypervisor | fast; syscall-heavy work pays | high | semi-trusted or multi-tenant workloads on Kubernetes |
| **MicroVM** | Firecracker or Cloud Hypervisor on KVM with a minimal device model | hardware virtualisation plus a minimal VMM | ~125 ms to guest init | VMM overhead < 5 MiB per VM | serverless; untrusted multi-tenant code |
| **Virtual machine** | KVM/QEMU, Hyper-V, ESXi, Xen | the hypervisor and its device emulation | seconds | lower | arbitrary guest OS, legacy, licensing boundaries |
| **Confidential VM** | AMD SEV-SNP, Intel TDX, Arm CCA, with remote attestation | the CPU's memory encryption; **the host and cloud operator are outside the TCB** | VM + attestation | VM, small overhead | data in use that must be protected from the operator |
| **Wasm sandbox** | Wasmtime, WAMR; WASI capabilities | the runtime's bounds checks and capability model | µs–ms | very high | plugins, edge functions, untrusted extension code in-process |
| **Dedicated hardware** | dedicated host, bare metal, air gap | physical access | — | lowest | side-channel-sensitive, regulated or licensing-bound workloads |

Four rules follow from the table.

1. **Untrusted multi-tenant code needs a hardware virtualisation boundary at minimum.**
   With a shared kernel, every kernel privilege-escalation bug is a tenant escape. This is the
   reason AWS built Firecracker for Lambda rather than packing tenants into containers on a
   shared kernel (Agache et al., NSDI 2020). Single-tenant trusted code does not need that
   boundary, and paying for it is over-engineering.
2. **Kubernetes is a scheduler, not an isolation boundary.** A namespace is an
   administrative scope. Hard multi-tenancy on Kubernetes needs node isolation, sandboxed
   runtimes (`RuntimeClass` with gVisor or Kata), or a cluster per tenant.
3. **Shared hardware leaks across every software boundary.** Spectre and Meltdown (2018)
   showed that caches, branch predictors and SMT siblings leak data across processes, VMs
   and enclaves. Mitigations cost performance. For the highest-assurance tenants the honest
   answer is no co-tenancy: dedicated hosts, or core scheduling that never shares SMT
   siblings across trust domains.
4. **Confidential computing changes who you trust, not whether you need to.** It removes the
   operator from the TCB but adds the CPU vendor's firmware and the attestation service. It
   only delivers value if the deployment pipeline actually verifies attestation before
   releasing secrets.

**Where virtualisation came from, and where it is going.** Popek and Goldberg (1974) set
out the formal requirements for a virtualisable architecture. IBM met them on the mainframe
in the early 1970s (CP-67, then VM/370), and LPARs still partition mainframes today. x86 did
not meet them until hardware assists arrived in 2005–2006 (Intel VT-x, AMD-V). Before that,
VMware used binary translation and Xen used paravirtualisation. The current direction moves
the hypervisor's I/O, networking and storage work onto dedicated hardware (AWS Nitro,
DPUs/IPUs such as NVIDIA BlueField), which makes VM overhead close to bare metal and removes
most of the host from the tenant's attack surface.

---

## 4. Embedded, real-time and safety-critical systems

**Real-time means predictable, not fast.** A *hard* real-time task fails the system when it
misses a deadline. A *firm* one produces a worthless result if late. A *soft* one degrades.
The response measure of a hard real-time `Q.xx` is a **bound on the worst case**
(worst-case execution time and worst-case response time), never a percentile. A p99.99
latency figure is not a real-time guarantee, however good it looks.

**Choosing the base.**

| Base | Use when | Costs |
|---|---|---|
| **Bare metal** (super-loop, interrupts) | tiny MCU, one job, hard timing | no isolation; everything is hand-built |
| **RTOS** (FreeRTOS, Zephyr, Eclipse ThreadX, VxWorks, QNX, INTEGRITY, PikeOS) | hard deadlines, small footprint, certification evidence available | smaller ecosystem; you build the services Linux gives for free |
| **Linux + `PREEMPT_RT`** | firm or soft deadlines with a rich ecosystem (robotics, industrial PCs, audio) | measured, not proven, latency bounds; hard to certify at the highest integrity levels |
| **Separation kernel / hypervisor with partitions** | mixed criticality on one SoC: a certified RTOS partition next to a Linux partition | integration complexity; the partition schedule becomes a first-class design artifact |

**Partitioning is the architecture.** ARINC 653 defines spatial partitioning (each partition
has its own memory) and temporal partitioning (each partition has fixed time windows), so
that a fault or overrun in one partition cannot change the timing of another. This is the
basis of Integrated Modular Avionics (DO-297) and the model to borrow for any
mixed-criticality system.

**Schedulability is maths, not hope.** For periodic tasks under fixed-priority scheduling
with rate-monotonic priority assignment, the Liu and Layland utilisation bound and exact
response-time analysis tell you before you build whether the task set meets its deadlines.
EDF can schedule up to 100% utilisation under its assumptions. The formulas and their
assumptions are in `quantitative-methods.md` §12.

**Priority inversion is the classic failure.** In 1997 Mars Pathfinder kept resetting because
a low-priority task held a mutex needed by a high-priority task while medium-priority tasks
ran. The fix was to enable priority inheritance on that mutex in VxWorks. The protocols
(priority inheritance, priority ceiling) are in Sha, Rajkumar and Lehoczky (1990). Any design
with shared resources across priorities must name its protocol.

**The standards set the process and the evidence.**

| Domain | Safety | Security |
|---|---|---|
| Generic / industrial | **IEC 61508** (SIL 1–4) | **IEC 62443** (zones and conduits, security levels) |
| Automotive | **ISO 26262** (ASIL A–D); AUTOSAR Classic and Adaptive | **ISO/SAE 21434**; UN R155 (cybersecurity) and R156 (software updates) |
| Avionics | **DO-178C** (DAL A–E), DO-330 (tools), DO-297 (IMA), ARINC 653 | DO-326A / ED-202A (airworthiness security) |
| Medical | **IEC 62304** (software safety classes A–C) | IEC 81001-5-1 |
| Railway | **EN 50716:2023** (replaces EN 50128 and EN 50657) | CLC/TS 50701 |
| All products with digital elements sold in the EU | — | **Cyber Resilience Act** (Reg. (EU) 2024/2847): vulnerability and incident reporting since 11 Sept 2026, full obligations from 11 Dec 2027 |

Coding standards (MISRA C:2023, MISRA C++:2023) and hazard-analysis techniques (HARA in
ISO 26262, FMEA, FTA, STPA) are inputs to the architecture, not part of it. Cite them; do not
expand them in the architecture description.

**How it lands in the artifacts.** Safety is a top-level characteristic in ISO/IEC
25010:2023 (operational constraint, risk identification, fail safe, hazard warning, safe
integration), so hazards become `Q.xx` scenarios against that characteristic. The integrity
level (SIL, ASIL, DAL, class) is a `C.xx` constraint that drives process and tooling. The
partition and schedule are a view in the HLD. The safety case (often in GSN notation) is
linked from `AD.md` as a separate artifact, never retyped into it.

---

## 5. Platform lifecycle — legacy, modern, future

**Legacy is not the same as obsolete.** A platform is a liability when its skills, cost
model, vendor support or security posture no longer meet the drivers, not because it is old.
The mainframe is the standing example: z/OS still runs core transaction processing at banks,
insurers and governments because it is extremely reliable at high throughput. The pressure to
leave comes from skills scarcity, the capacity-based cost model and delivery speed, not from
the technology failing. Treat a platform exit as a migration with its own blueprint
(`migration.md` §2, scenario D), not as a clean-up task.

| Area | Then | Now | Next |
|---|---|---|---|
| **Kernels** | proprietary Unix (AIX, HP-UX, Solaris), mainframe OS | Linux everywhere on servers; NT on Windows; microkernels in safety and automotive | memory-safe languages in kernels (Rust); verified components (seL4); BPF-defined policy (`sched_ext`) |
| **Isolation** | physical servers, LPARs | VMs and containers | microVMs and sandboxes by default for untrusted code; confidential computing as a default; hypervisor work on DPUs/IPUs |
| **Extension model** | loadable modules and kernel-mode agents | eBPF on Linux (and eBPF for Windows) | security and observability vendors out of kernel mode |
| **I/O** | blocking threads, `select` | `epoll`/`kqueue`, `io_uring` where its attack surface is acceptable | user-space data planes for specialised work; CXL-attached and tiered memory |
| **CPU architecture** | x86 monoculture | Arm in cloud (Graviton, Axion, Cobalt) and client | RISC-V in embedded; capability hardware (CHERI, Arm Morello, CHERIoT) |
| **Portable sandboxes** | JVM/CLR | Wasm in browsers and at the edge | the WASI component model as a portable, capability-secured unit of deployment |
| **Embedded / vehicle** | ECU per function on an OSEK RTOS | AUTOSAR Classic + Adaptive, domain controllers | zonal, software-defined vehicles: few powerful computers with mixed-criticality partitioning and over-the-air updates |

**Support lifecycles are constraints, and end-of-support dates are roadmap items.** Record
the support horizon of every platform component as a `C.xx` with the date. Since 2023 the
upstream Linux project commits to about two years of support for new LTS kernels, with some
lines extended case by case (check kernel.org for current dates). Products that need ten
years or more rely on the Civil Infrastructure Platform's super-long-term kernels or a vendor
or distribution lifecycle. Windows 10 reaching end of support in October 2025 is a recent
example of a date that forced fleet-wide work. A product with a fifteen-year field life and
no kernel-maintenance plan has an unrecorded risk. How to keep a technology radar and an
end-of-support register is in `migration.md` §7.

**A CPU-architecture move is a portability decision.** Moving to Arm for price-performance is
usually a rebuild, not a rewrite, if the code avoids architecture-specific intrinsics and the
build produces multi-architecture images. Record it as an ADR with the measured
price-performance and the components that block it.

---

## 6. How it lands in the artifacts

| Artifact | What goes in |
|---|---|
| **PRD** | `Q.xx` for tail latency, jitter, boot time, density, WCET; `C.xx` for integrity level, OS support horizon, CPU architecture, minimum kernel version |
| **HLD §6 Deployment** | per container: OS and kernel line, runtime, **isolation boundary**, CPU architecture, and the node pool it runs on |
| **HLD §7 Cross-cutting** | I/O and concurrency model, scheduling policy, update and rollback mechanism |
| **HLD §8 Threat model** | rows for the shared kernel, privileged containers, kernel-mode agents and drivers, the boot chain, side channels, and the cloud metadata service |
| **ADRs** | kernel or RTOS choice, isolation boundary, I/O model change, any third-party kernel-mode component, real-time policy, CPU-architecture switch, OS lifecycle strategy |
| **Fitness functions** (`automation.md`) | `cyclictest` worst-case latency gate under load; seccomp profile drift check; image CVE scan; kernel hardening config check (for example `kernel-hardening-checker` against KSPP settings); boot-time budget |

---

## 7. Over-engineering traps, systems edition

- **Kernel bypass before proof.** DPDK, RDMA or a user-space network stack without a profile
  that shows the kernel stack is the bottleneck. You inherit a driver and lose your tooling.
- **A kernel module where eBPF or user space would do.** A module runs with full privilege
  and no verifier. Its failure mode is the whole machine.
- **A microkernel or RTOS without a real-time or assurance driver.** You pay in ecosystem and
  skills for a guarantee nobody asked for.
- **Unikernels for services that need debugging in production.** The tooling you rely on at
  3 a.m. is not there.
- **Real-time tuning without a jitter requirement.** `isolcpus`, `nohz_full` and IRQ pinning
  make the platform harder to operate. Do it only for a measured `Q.xx`.
- **The opposite mistake:** shared-kernel containers for untrusted multi-tenant code. That is
  under-engineering, and the threat model must flag it.

---

## 8. Sources

| Topic | Source |
|---|---|
| Microkernel minimality, fast IPC | J. Liedtke, *Improving IPC by Kernel Design* (SOSP 1993); *On µ-Kernel Construction* (SOSP 1995) |
| Formally verified kernel | G. Klein et al., *seL4: Formal Verification of an OS Kernel* (SOSP 2009); seL4 Foundation |
| Exokernel, multikernel | D. Engler, F. Kaashoek, J. O'Toole, *Exokernel* (SOSP 1995); A. Baumann et al., *The Multikernel* (SOSP 2009) |
| Driver fault rates | A. Chou et al., *An Empirical Study of Operating Systems Errors* (SOSP 2001); M. Swift et al., *Improving the Reliability of Commodity Operating Systems* (SOSP 2003) |
| Virtualisation requirements | G. Popek, R. Goldberg, *Formal Requirements for Virtualizable Third Generation Architectures* (CACM 1974) |
| MicroVMs | A. Agache et al., *Firecracker: Lightweight Virtualization for Serverless Applications* (NSDI 2020) |
| `io_uring` exploit share | Google Security Blog, *Learnings from kCTF VRP's 42 Linux kernel exploits submissions* (June 2023) |
| Memory-safety share of CVEs | Microsoft Security Response Center (2019); Chromium security team |
| Real-time scheduling | C. L. Liu, J. Layland (JACM 1973); M. Joseph, P. Pandya (1986); N. Audsley et al. (1993); L. Sha, R. Rajkumar, J. Lehoczky, *Priority Inheritance Protocols* (IEEE TC 1990) |
| Partitioning | ARINC 653; RTCA DO-297 |
| OS textbooks for orientation | A. Tanenbaum, H. Bos, *Modern Operating Systems*; R. Arpaci-Dusseau, A. Arpaci-Dusseau, *Operating Systems: Three Easy Pieces* |
| POSIX | IEEE Std 1003.1 / ISO/IEC 9945 |
| Safety and security standards | IEC 61508, ISO 26262, DO-178C, IEC 62304, EN 50716:2023, IEC 62443, ISO/SAE 21434, Regulation (EU) 2024/2847 (CRA) |

Cross-references: style catalogue (microkernel/plug-in) — `structure.md` §2; schedulability
and latency maths — `quantitative-methods.md` §§11–12; network and cloud substrate —
`network-architecture.md`, `cloud-architecture.md`; platform exits and lifecycle —
`migration.md` §§2, 7; threat model — `threat_modeling.md`.
