# Runbook

This runbook covers the planned ChatGPT App deployment path. It is operational
guidance for maintainers and release operators.

Official reference anchors:

- Build the MCP server: <https://developers.openai.com/apps-sdk/build/mcp-server>
- Build the ChatGPT UI: <https://developers.openai.com/apps-sdk/build/chatgpt-ui>
- Test integration: <https://developers.openai.com/apps-sdk/deploy/testing>
- Troubleshooting: <https://developers.openai.com/apps-sdk/deploy/troubleshooting>
- Submission: <https://developers.openai.com/apps-sdk/deploy/submission>

## Local Checks

```bash
python3 -m pytest
cd demo && npm run build
```

For app work, add server and widget package checks once those packages exist:

```bash
cd app/server && python3 -m pytest
cd app/web && npm run lint && npm run typecheck && npm run build
```

## Development Flow

1. Validate the reference image and project intent.
2. Run analysis tools in read-only mode.
3. Start jobs only after intent and reference gates pass.
4. Poll job state rather than holding one long tool call.
5. Inspect widget output and structured content fallback.
6. Export package only after quality gates pass or approved conditional status is recorded.

## Job Recovery

| Symptom | Action |
| --- | --- |
| Worker crash | Mark stage failed or resume from last checkpoint. |
| Duplicate request | Reuse idempotency key result. |
| Artifact missing | Mark dependent stages stale and rerun from the nearest valid checkpoint. |
| Gate failure | Stop production output and return issue code plus remedy. |
| Widget load failure | Keep structured content and file references usable. |

## Release Checklist

- MCP endpoint uses HTTPS.
- Tool annotations match real side effects.
- CSP includes only required domains.
- File upload, file reference, and download flows work.
- Project/job/artifact state survives server restart.
- Unauthorized artifact access is denied.
- Logs contain trace id, project id, tool name, stage, duration, and failure code.
- Logs do not contain secrets.
- README localization is current.
- Docs under `docs/` are English except README localization sections.

## Submission Readiness

Before public submission:

- Verify organization and app management permissions.
- Confirm the MCP server is publicly reachable.
- Provide privacy policy and test prompts.
- Scan tools after deploying metadata changes.
- Treat published metadata as a versioned contract.

## Incident Response

1. Disable new build starts if file validation, authorization, or storage integrity is affected.
2. Preserve logs and trace ids without exposing secrets.
3. Revoke affected signed URLs.
4. Mark impacted jobs failed or blocked with user-visible remedies.
5. Patch and redeploy.
6. Re-run security, job lifecycle, and artifact access tests.
