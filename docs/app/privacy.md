# Privacy

This document defines data-handling expectations for the planned ChatGPT App.

## Data Categories

| Data | Examples | Handling |
| --- | --- | --- |
| User inputs | images, GLB files, natural-language intent | Store only under the project; apply retention and deletion policy. |
| Derived artifacts | Sense Pack, blueprints, rig, clips, manifests, quality reports | Store as project artifacts with lineage. |
| Operational metadata | job id, stage, duration, issue code, retry count | Keep for observability and abuse prevention. |
| Provider metadata | provider name, model or tool id, license, source reference | Include in manifests when external services are used. |

## Principles

- Do not infer or disclose hidden personal data from reference images.
- Do not send files to external providers unless the selected route explicitly allows that provider.
- Record provider usage, license, and lineage in the package manifest.
- Keep authoritative state on the server, not in the widget.
- Use TTL and deletion policies for temporary files and previews.
- Avoid storing raw prompts longer than needed unless they are part of user-visible project history.

## User-Facing Disclosure

Quality reports must distinguish:

- user-confirmed fields
- defaulted fields
- inferred fields
- unknown fields
- single-view uncertainty
- external provider usage
- generated or inpainted regions

## Retention

R1 policy:

- temporary upload staging: short TTL
- build intermediates: project lifetime or explicit cleanup
- exported packages: project lifetime or explicit deletion
- operational logs: bounded retention with secret scrubbing

Specific retention periods must be configured before public deployment.

## Privacy Acceptance

- A package manifest identifies the lineage of every generated artifact.
- Deleting a project deletes or expires associated artifacts.
- Structured content does not include credentials or private storage paths.
- External provider use is visible to the user before package export.
