# gpthreejs Documentation

This directory is the authoritative documentation home for the project. Keep
durable plans, product contracts, app guidance, and playbooks here so
contributors have one stable entry point.

## Architecture

- [Design Notes](./design.md) - product surface, quality thesis, isolation rules, and current roadmap.
- [Detail Fidelity Research](./detail-research.md) - research notes for richer procedural knight detail.

## Planning

- [ChatGPT App Game Animation Upgrade](./planning/chatgpt-app-game-animation-upgrade.md) - product plan, release slices, schemas, risks, and acceptance criteria.
- [Multi-Agent Execution Prompt](./planning/multiagent-execution-prompt.md) - role and model routing prompt for executing the upgrade.
- [Quality Upgrade Execution Plan](./planning/quality-upgrade-execution/readme.md) - Korean topic plans, release gates, and a progress-tracked implementation task list based on the knight quality review.
- [Quality Upgrade Multi-Agent Goal](./planning/quality-upgrade-execution/08-multi-agent-goal-prompt.md) - execution-ready model routing, agent roles, review loops, and milestone gates for the quality upgrade.

## ChatGPT App

- [ChatGPT App](./app/chatgpt-app.md) - MCP tools, widget responsibilities, state ownership, and artifact flow.
- [Security](./app/security.md) - input validation, isolation, prompt-injection controls, secrets, and deployment checks.
- [Privacy](./app/privacy.md) - file retention, lineage, provider disclosure, and user-data boundaries.
- [Runbook](./app/runbook.md) - local development, staging checks, job recovery, and release operations.

## Playbooks

- [Use Context Brief](./playbooks/use-context-brief.md)
- [Intent Questions](./playbooks/intent-questions.md)
- [Game Asset Brief](./playbooks/game-asset-brief.md)
- [Rigging](./playbooks/rigging.md)
- [Animation Blueprint](./playbooks/animation-blueprint.md)
- [Action Timeline](./playbooks/action-timeline.md)
- [Performance Budgets](./playbooks/performance-budgets.md)

Runtime skill rubrics still live in [`../playbook`](../playbook/) because the
current CLI and `SKILL.md` refer to that path. New product and app contracts
belong under this `docs/` tree.
