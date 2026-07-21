# Security

This document defines security requirements for the planned ChatGPT App and
game-asset pipeline.

Official reference anchors:

- Apps SDK security and privacy: <https://developers.openai.com/apps-sdk/guides/security-privacy>
- App submission requirements: <https://developers.openai.com/apps-sdk/deploy/submission>
- MCP server setup: <https://developers.openai.com/apps-sdk/build/mcp-server>

## Trust Boundaries

- User files are untrusted.
- Model-generated tool inputs are untrusted.
- Widget messages are untrusted.
- External provider outputs are untrusted until validated.
- Project, job, and artifact identifiers are authorization-sensitive.

## Input Validation

Validate all user-controlled inputs server-side:

- MIME type and file extension mismatch.
- Image decode success, megapixels, aspect ratio, and byte size.
- GLB parse success, scene size, node count, animation count, skin weights, and metadata size.
- Zip package expansion ratio and path traversal.
- JSON schema version, unknown fields, duplicate ids, invalid references, and excessive array sizes.

Reject or quarantine inputs that exceed limits. Do not rely on the model or the
widget to enforce limits.

## Prompt Injection Controls

- Tool descriptions must be specific about allowed behavior.
- Build tools must re-check intent and reference gates before doing work.
- Irreversible external actions are out of scope for R1/R2.
- Natural-language revision requests are converted into structured patches and validated.
- Model-provided file paths are never trusted as direct filesystem paths.

## Authorization

- Every project, job, and artifact lookup checks owner or workspace permission.
- Signed URLs are scoped, short-lived, and bound to artifact ids.
- A user cannot access another project by guessing ids.
- Job retry must reuse idempotency keys and avoid duplicate work or billing.

## Secrets

Never place tokens, API keys, storage credentials, OAuth credentials, signed URL
secrets, or raw authorization headers in:

- structured tool content
- widget state
- job metadata visible to the model
- quality reports
- client-side bundles
- logs

## Runtime Isolation

- Use a constrained working directory per job.
- Prevent path traversal on extraction and export.
- Apply CPU, GPU, memory, storage, and wall-clock quotas.
- Clean temporary files after TTL or explicit project deletion.
- Treat external meshes and textures as data, not executable content.

## Deployment Checks

- Production MCP endpoint uses HTTPS.
- CSP includes only required app, asset, and API origins.
- Health checks cover server, storage, worker queue, and artifact access.
- Logs include trace ids and failure codes but no secrets.
- Submission metadata matches actual tool annotations.

## Security Acceptance

- Unauthorized project and artifact access fails.
- Oversized, malformed, and spoofed files fail with issue codes.
- Job retry does not duplicate jobs.
- Widget failure does not leak internal state.
- Logs are sufficient for incident investigation without exposing secrets.
