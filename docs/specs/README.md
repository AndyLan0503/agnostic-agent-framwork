# Feature specs

The durable handoff artifact between roles (docs/adr/0001). One file per
feature: `docs/specs/<feature-slug>.md`. The business-analyst role writes
`## Analysis`, the product-manager role appends `## Spec`, implementers
read both.

Keep specs small and current. A decision that is expensive to reverse gets
promoted to an ADR.

## File shape

```markdown
# <Feature title>

## Analysis                <- business-analyst
- Problem / motivation
- User stories (one per affected actor)
- Acceptance criteria (Given/When/Then)
- In scope / out of scope
- Constraints and invariants touched (name the Guardrails)
- Open questions

## Spec                    <- product-manager
- Goal and non-goals
- Prioritized requirements (P0 slice drawn explicitly)
- Success metrics
- Rollout and risk (order, migrations, blast radius)
- Decisions needing an ADR
- Sequencing (which implementers, in what order)
```
