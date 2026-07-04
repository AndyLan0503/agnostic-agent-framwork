# Summary
<!-- What changed and why. Link any issue. -->

## How tested
<!-- Commands run and their results. Real evidence, not "should work". -->

## Reviewer checklist
<!-- Tick what applies; explain anything you cannot tick. See AGENTS.md "Guardrails". -->

- [ ] `make test` is green. New or changed behavior has tests, written first.
- [ ] No secrets committed; lockfiles updated alongside any dependency change.
- [ ] No pushes to protected branches; targets the integration branch.
- [ ] Deploy-affecting changes go through the pipeline, nothing applied by hand.
- [ ] Project invariants preserved: <!-- fill in per project, one line each -->
- [ ] ADRs/knowledge cards updated if this PR changes a fact or decision.
