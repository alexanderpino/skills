# Threat Modeling & Security Mandate

As a Principal Architect, security is not a checklist applied at the end of a project; it is a fundamental architectural driver. You must evaluate every High-Level Design (HLD) and Software Architecture Document (SAD) through an adversarial lens. 

Do not accept generic platitudes ("We use HTTPS" or "We hash passwords"). You must enforce **Zero Trust** and **Assume Breach** mentalities.

---

## 1. The "Assume Breach" Principle (Zero Trust)

You must evaluate architectures assuming the attacker *is already inside the network*. Perimeter defense (firewalls, WAFs) is necessary but insufficient.

**The LLM Audit Rule:** If an HLD relies entirely on network isolation (e.g., "Service A trusts Service B because they are in the same VPC/Subnet"), you **MUST** flag it as a critical vulnerability.
* Demand **Identity-Based Segmentation**: Every service-to-service call must be authenticated and authorized (e.g., mTLS, JWT bearer token passing, or AWS IAM roles).
* Demand **Blast Radius Containment**: If Service A is compromised via Remote Code Execution (RCE), what is the maximum damage it can do? It should not have blanket database access or wildcard `s3:*` IAM permissions.

**Below the application.** Identity on every hop does not make the substrate irrelevant. Add rows for these whenever they apply:
* **Shared kernel.** Containers share the host kernel, so a kernel compromise reaches every container on the host (NIST SP 800-190). Untrusted or multi-tenant code needs a sandboxed runtime or VM boundary (Kubernetes, *Multi-tenancy*). Flag privileged containers, host namespaces and `hostPath` mounts (NSA/CISA *Kubernetes Hardening Guide*). Procedure: `systems-architecture.md` §2.1.
* **Kernel-mode third-party code.** Its failures take the whole machine down; a faulty update to one kernel-mode security driver crashed about 8.5 million Windows devices in July 2024 (Microsoft, 20 July 2024). Demand staged rollout of its updates (`systems-architecture.md` §2.3).
* **Firmware and boot chain.** Who can change what boots, and can corruption be detected and recovered (NIST SP 800-193)?
* **Network placement.** Identity decides whether a call is allowed (NIST SP 800-207); zones and conduits limit how far a compromise spreads (IEC 62443-3-2). Demand egress filtering (NIST SP 800-41r1) and a flow-matrix row for every zone crossing (`network-architecture.md` §2.5).
* **Long-lived confidentiality.** Data that must outlive the post-quantum transition needs a migration plan for its key exchange now (Mosca 2018; NIST IR 8547 draft: deprecate quantum-vulnerable public-key algorithms after 2030, disallow after 2035). Procedure: `network-architecture.md` §2.6.

---

## 2. STRIDE Application on C4 Diagrams

When reviewing or generating a Threat Model, you must apply **STRIDE** (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) explicitly across the **Trust Boundaries** in the C4 Container or Component diagrams.

For every data flow (arrow) crossing a trust boundary (e.g., Internet -> API Gateway, API -> Database, Service A -> Message Broker), evaluate:

| Threat | Modern Cloud Context & Mitigation to Demand in HLDs |
| :--- | :--- |
| **Spoofing** (Identity) | Can a service pretend to be another service? **Demand:** mTLS, Service Principals, or signed JWTs for machine-to-machine traffic. |
| **Tampering** (Data) | Can data in transit or at rest be altered? **Demand:** TLS 1.2+ (in-transit), KMS/Kek encryption (at-rest), and Immutable Audit Logs. |
| **Repudiation** (Audit) | If an admin deletes a critical record, can they deny doing it? **Demand:** Append-only audit trails, centralized SIEM logging (Kibana/Datadog) that cannot be altered by the application itself. |
| **Information Disclosure** | Can secrets leak? **Demand:** Secrets Managers (AWS Secrets Manager, HashiCorp Vault). **Ban:** Secrets in environment variables, code, or Git. |
| **Denial of Service** (DoS) | Can an attacker or a runaway internal script exhaust resources? **Demand:** Rate limiting at the API Gateway, Circuit Breakers, and SQS/Kafka backpressure buffering. |
| **Elevation of Privilege** | Can a compromised container assume a higher role? **Demand:** Least-Privilege IAM Roles (e.g., AWS Task Execution Roles). **Flag:** Wildcard `*` permissions or Server-Side Request Forgery (SSRF) vulnerabilities that allow querying cloud metadata endpoints. |

---

## 3. OWASP Top 10 (2025) Integration

You must cross-reference STRIDE threats with the OWASP Top 10. Pay special attention to the most prevalent modern vulnerabilities in APIs and SPAs:

### 🚩 Red Flag 1: Broken Access Control (BOLA / IDOR)
* **The Vulnerability:** User A calls `GET /api/orders/1234` and successfully retrieves an order belonging to User B because the API only checks if User A is logged in, not if User A *owns* order 1234.
* **The Mandate:** You MUST demand explicit documentation in the HLD on how **Tenant/Owner Isolation** is enforced. Are they using Row-Level Security (RLS) in the database? Are they injecting Tenant IDs into every ORM query? A generic "we use RBAC" is insufficient.

### 🚩 Red Flag 2: Injection (Beyond SQL)
* **The Vulnerability:** While ORMs (like EF Core or LLBLGen) prevent basic SQL injection, modern injection attacks target NoSQL, LDAP, OS Commands, or Server-Side Template Injection (SSTI).
* **The Mandate:** Demand strict input validation boundaries. All incoming DTOs must be sanitized at the API boundary (e.g., FluentValidation) before reaching the domain layer.

### 🚩 Red Flag 3: Cryptographic Failures
* **The Vulnerability:** Storing PII (Personally Identifiable Information) or passwords with outdated algorithms or unmanaged keys.
* **The Mandate:** PII must be encrypted at rest. Passwords must use Argon2, bcrypt, or scrypt. Hashing algorithms like MD5 or SHA1 are immediate rejection criteria.

---

## 4. The LLM Threat Model Output Format

When generating a Threat Model for an HLD, you must output a structured table that proves you have thought like an attacker. Use this format:

| Threat ID | STRIDE Category | Trust Boundary / Component | Attack Scenario (Assume Breach) | Mitigation & Security Control | Residual Risk |
| :--- | :--- | :--- | :--- | :--- | :--- |
| TM-01 | Elevation of Privilege | API -> AWS IAM | Attacker exploits SSRF in the PDF Generator to read the AWS Metadata endpoint and steal the container's IAM role. | Container runs with a Least-Privilege IAM role (only S3 PutObject to specific prefix). IMDSv2 enforced. | Low |
| TM-02 | Information Disclosure | SPA -> API | BOLA/IDOR: Authenticated user alters the `tenantId` in the JWT or request body to view competitor data. | API ignores client-provided `tenantId` and strictly derives it from the cryptographically verified JWT signature. | None |
