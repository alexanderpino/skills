# Agent Coordination Rules

Directors: `product-director`, `technical-director`, `delivery-director`. The full tree is `.claude/docs/agent-roster.md`.

1. **Vertical Delegation**: Directors delegate to leads, leads to specialists. Never skip a
   tier for a complex decision.
2. **Horizontal Consultation**: Agents at the same tier may consult each other but must not
   make binding decisions outside their domain.
3. **Conflict Resolution**: When two agents disagree, escalate to the shared parent. With no
   shared parent, escalate to `product-director` for product and business-rule conflicts and to `technical-director`
   for technical conflicts. A conflict between directors goes to the user.
4. **Change Propagation**: When a change affects several domains, `delivery-director` coordinates the
   propagation and names every affected document.
5. **No Unilateral Cross-Domain Changes**: An agent never modifies files outside its own
   paths (its **What This Agent Must NOT Do** section) without explicit delegation.
6. **Read Documents by Section**: A brief names the sections an agent needs by heading.
   Grep for `^#`, then Read that range with offset and limit.
7. **Nothing Goes Upstream**: Never file or comment on an issue in a vendor or third-party
   repository. Draft it; the user submits it.

## Parallel Task Protocol

When a skill spawns several independent agents:

1. Issue every independent `Agent` call before waiting for any result.
2. Collect all results before a phase that depends on them.
3. A BLOCKED agent is surfaced at once — never silently skipped.
4. Always produce a partial report when some agents finish and others block.
