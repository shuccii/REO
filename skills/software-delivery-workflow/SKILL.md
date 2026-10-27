---
name: software-delivery-workflow
description: Deliver web or app changes through scoped planning, isolated implementation, testing, security-aware review, and an approval gate before release.
---

# Software Delivery Workflow

Use this skill for Web, iOS, Android, backend, or full-stack work with multiple independent workstreams.

## Task graph

1. **Planner**: maps the request to acceptance criteria, affected modules, data boundaries, and a test plan.
2. **Explorer or researcher**: reads the codebase, official documentation, and existing tests; it does not edit production files.
3. **Implementer**: owns an isolated branch or worktree and a clearly bounded set of files.
4. **Tester**: runs targeted automated tests and checks the stated acceptance criteria using the implementation artefacts.
5. **Reviewer**: first checks requirements/scope against the actual artifacts and diff, then regressions, security, accessibility, error handling, and documentation impact. Mandatory integrity checks still run when requirements fail.
6. **Release coordinator**: creates a verified handoff for deployment, release, store submission, or publication; it never performs those actions without explicit approval.

Only parallelise implementation tasks with non-overlapping file ownership. Prefer one integrator to resolve all merge conflicts. If an issue crosses ownership boundaries, stop parallel editing and revise the plan.

Use [execution, review and recovery](../orchestrate-work/references/execution-control.md) for worker-status routing, bounded repairs, repeat review and evidence before completion. Review a new lead-authored repair independently. If an error or unexpected behavior occurs, use [root-cause-debugging](../root-cause-debugging/SKILL.md) before changing code or configuration. Keep the existing v0.3 JSON result statuses; legacy `STATUS` labels do not replace the contract.

## Completion requirements

- Run the smallest relevant automated checks first, then broader checks proportional to risk.
- Report tests that could not run and why.
- Validate user-visible behavior at the relevant viewport or target device when the request is UI-sensitive.
- Keep secrets, signing assets, production credentials, and user data out of generated outputs and version control.
- Treat deploy, publish, submit, delete, payment, and production data changes as approval-required.

Classify code changes as `implementation_change` and require semantic review of the diff and intent. Reserve `unit_test_execution` for running and collecting an already specified test suite. Follow `orchestrate-work` for manifests, results, and approval boundaries.
