# ChatGPT App Contract

This document defines the planned ChatGPT App surface for gpthreejs. It is a
contract document, not a claim that the app is already implemented.

Official reference anchors:

- Apps SDK overview: <https://developers.openai.com/apps-sdk>
- MCP server setup and file handling: <https://developers.openai.com/apps-sdk/build/mcp-server>
- ChatGPT UI and widget bridge: <https://developers.openai.com/apps-sdk/build/chatgpt-ui>
- State management: <https://developers.openai.com/apps-sdk/build/state-management>
- MCP Apps compatibility: <https://developers.openai.com/apps-sdk/mcp-apps-in-chatgpt>
- Submission readiness: <https://developers.openai.com/apps-sdk/deploy/submission>

## Architecture

```text
ChatGPT conversation
  -> MCP tools
  -> Apps SDK / MCP Apps widget
  -> gpthreejs application server
  -> Python engine adapter
  -> job and artifact storage
```

The MCP server owns tools, validation, authentication, project state, job state,
and artifact references. The widget owns only ephemeral UI state such as current
clip, playback time, selected overlay, camera pose, and panel expansion.

## Tools

| Tool | Side effect | Purpose |
| --- | --- | --- |
| `assess_project_intent` | read-only | Evaluate `UseContextBrief` completeness and return the next question. |
| `submit_project_intent` | non-destructive write | Apply user answers, update route, and identify stale artifacts. |
| `analyze_reference` | read-only | Analyze image suitability, reference sufficiency, likely domain, and possible rig mode. |
| `start_character_build` | non-destructive write | Start a resumable form and rig build job. |
| `get_character_build` | read-only | Return stage, progress, previews, issues, and artifact links. |
| `revise_character_build` | non-destructive write | Create a new revision from user feedback and selected widget context. |
| `generate_animation_set` | non-destructive write | Generate requested clip packs and action events. |
| `export_character_package` | non-destructive write | Produce package artifacts and final quality report references. |

Tool annotations must match actual behavior. Read-only tools must not mutate
project, job, artifact, billing, or cache state beyond ordinary logging.

## File Handling

- Image, GLB, and package inputs use top-level file parameters.
- Server-side validation checks MIME type, byte size, megapixels, decode result, and extension mismatch.
- Large outputs return file references or MCP resource links, not base64 blobs.
- Temporary files have TTL, project ownership, and deletion policy.

## Widget

Required views:

- purpose intake and brief review
- build progress
- Three.js asset viewport
- front, side, back, and free orbit views
- wireframe, normal, skeleton, socket, collider, and hitbox overlays
- clip browser
- action timeline
- quality report
- fallback text report when WebGL or GLB loading fails

For portability, prefer MCP Apps standard bridge behavior where available. Use
`window.openai` extensions only for ChatGPT-specific file, widget, or fullscreen
capabilities.

## State Ownership

| State | Owner | Examples |
| --- | --- | --- |
| Business state | server | projects, jobs, artifacts, schemas, accepted briefs |
| Widget state | widget | playback position, selected clip, overlays, camera |
| Cross-session state | backend | saved project settings, profile defaults |

The widget must never be the authoritative source for build state or artifact
state.

## Build Gate

Before any production build tool starts:

1. `UseContextBrief.intentVerdict` is `pass` or approved `conditional`.
2. The route hash matches the latest confirmed purpose fields.
3. Required deliverables and performance profile are known.
4. Reference sufficiency does not require `abort`.

If the intent verdict is `ask`, tools return `nextQuestion` instead of starting
a job.

## Acceptance

- Complete requests route without duplicate questions.
- Incomplete requests ask one high-impact question and do not start a build.
- Repeated idempotency keys do not create duplicate jobs or duplicate charges.
- Server restart restores project, job, and artifact state.
- Structured tool results are useful even when the widget fails.
