# Intent Questions

Intent questions collect only the information that changes downstream build
decisions.

## Priority

1. Purpose: where the result will be used.
2. Runtime and platform: engine, browser, device, camera.
3. Interaction: static, inspectable, animated, interactive, playable.
4. Deliverables: TypeScript, GLB, manifests, render, video, printable mesh.
5. Constraints: performance, scale, fidelity, deadline, cost, provider policy.
6. Game details: rig mode, movement, attack, skill, physics, sockets, action events.

## Rules

- Ask one question at a time.
- Reuse information already supplied by the user.
- Prefer quick choices when the route is enumerable.
- Preserve free-form answers for custom constraints.
- Stop when all critical fields for the selected profile are known.

## Example Questions

- "Where will this 3D result be used?"
- "Which runtime should consume the character: Three.js, a GLB pipeline, or another target?"
- "Should the character be static, animated, or playable?"
- "Which action set is required for the first package?"
- "Should motion be in-place, root-motion, or mixed?"
