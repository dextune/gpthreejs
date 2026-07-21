# Multi-Agent Execution Prompt

Use this prompt as the top-level instruction for the upgrade described in
[ChatGPT App Game Animation Upgrade](./chatgpt-app-game-animation-upgrade.md).

```text
You are a multi-agent team upgrading the gpthreejs repository into a ChatGPT App
that can create game-oriented character assets from reference images.

Authoritative documents:
- docs/planning/chatgpt-app-game-animation-upgrade.md
- SKILL.md
- playbook/*.md
- docs/design.md
- docs/detail-research.md

Model assignment:
- Coding implementation: tera medium.
- Documentation, runbooks, user-facing docs, and playbooks: luna high.
- Code review, design analysis, architecture challenge, and acceptance evidence: sol high.

Roles:
1. Lead Orchestrator: sol high
   Own sequencing, dependency gates, blocker decisions, integration, and final evidence.

2. Architecture Analyst: sol high
   Convert the plan into an implementation dependency graph, review boundaries, and maintain ADRs.

3. Contract Executor: tera medium
   Implement UseContextBrief, game schemas, migration, validation, intent sufficiency, routing, and dependency invalidation.

4. Static Pipeline Executor: tera medium
   Preserve existing static behavior, clarify cast terminology, and block gate bypass.

5. Rig Runtime Executor: tera medium
   Implement rigid rig generation, rig handles, profiles, socket/collider validation, and deterministic node naming.

6. Animation Runtime Executor: tera medium
   Implement procedural clips, CharacterAnimator, ActionTimeline, CharacterStateGraph, and motion metrics.

7. Export and Hybrid Executor: tera medium
   Implement package export, GLB round trip, hybrid inspect/normalize/retarget, and manifest lineage.

8. ChatGPT App Server Executor: tera medium
   Implement MCP tools, file validation, idempotent jobs, artifact state, and schema migrations.

9. ChatGPT Widget Executor: tera medium
   Implement the Three.js inspection widget, overlays, clip browser, action timeline, and fallback report views.

10. Documentation Writer: luna high
    Keep all documentation in English except README localization sections. Update docs under docs/ by type.

11. Test Engineer: sol high
    Convert acceptance criteria into fixtures and unit, integration, e2e, visual, motion, performance, and security tests.

12. Code Reviewer and Verifier: sol high
    Review every patch for gate bypass, silent fallback, compatibility, metadata leakage, idempotency, cleanup, and performance drift.

Execution order:
1. Complete Slice 0 and Slice A first.
2. Do not parallelize rig, runtime, app, or export implementation until schemas and action contracts pass sol high review.
3. After contract approval, parallelize implementation by file ownership.
4. Keep documentation writer and verifier independent from implementation lanes.

Invariants:
- No production build before route confirmation.
- No TypeScript, GLB, or package output when the verdict is `ask` or `abort`.
- Critical fields are never silently defaulted.
- `confirmedFields`, `defaultedFields`, `inferredFields`, and `unknownFields` are always separated.
- A single image never proves hidden sides, organic deformation, exact likeness, or motion.
- External provider use must be disclosed in provider, license, and lineage metadata.
- Animation output must include ActionManifest timing, events, sockets, and hitboxes.
- Budget failure must return measured values and remedies, not silent LOD downgrade.
- Structured content, widget state, and logs must not contain tokens, API keys, or storage credentials.

Agent output format:
- Files changed.
- Requirements implemented.
- Tests or checks run.
- Risks and blockers.
- Handoff notes.

Final report:
1. Completed and remaining release slices.
2. Major changed files.
3. Verification evidence.
4. Acceptance criteria table with pass, conditional, or reject.
5. Remaining risks and ADR follow-ups.
6. Deployment or next-command status.
```

Short launch command:

```text
Start from the multi-agent prompt in docs/planning/multiagent-execution-prompt.md.
Assign coding to tera medium, documentation to luna high, and review/design
analysis to sol high. Complete Slice 0 and Slice A before parallel
implementation. Preserve the no-build-before-route and ask/abort-no-output
invariants.
```
