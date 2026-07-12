# Phase 9 — Tool Integrations

## Objective

Securely ingest Slack and GitHub events, and prepare governed Jira mutations.

## Design

- Slack uses `v0` HMAC signatures with a five-minute replay window; GitHub uses `sha256` HMAC signatures.
- Events are canonicalized and deduplicated by the existing tenant/provider/event unique constraint before workflow dispatch.
- Jira mutation contracts require an idempotency key; execution and external verification remain Phase 10 responsibilities.
- OAuth credentials remain encrypted through the Phase 5 cipher and are never exposed to agents.

## Implementation

Added provider-neutral ingress/mutation contracts and shared Slack/GitHub verification helpers. The existing `source_events`, outbox, and `executed_actions` schema supplies durable deduplication and idempotency boundaries.

## Testing

Webhook verification tests cover valid signatures and Slack replay rejection. Connector HTTP contract tests run against provider sandboxes or mocks in deployment CI.

## Next steps

Phase 10 introduces policy evaluation, approvals, action execution, verification, notifications, and recovery workflows.
