# API Specification — Initial Contract

## Conventions

- Base path: `/api/v1`; JSON request/response bodies; UTC ISO-8601 timestamps; UUIDv7 resource IDs.
- Authentication: `Authorization: Bearer <access_token>`. Browser session refresh uses secure, HttpOnly cookies; state-changing browser requests include CSRF protection.
- Each response includes `X-Request-ID`; asynchronous actions additionally include a workflow run ID and trace ID.
- Pagination uses `cursor` and `limit` (1–100). Filters are explicit query parameters.
- Mutations accept an `Idempotency-Key` header. Reuse with a different body returns `409`.
- Error envelope: `{ "error": { "code": "…", "message": "…", "request_id": "…", "details": [] } }`.

## Initial endpoints

| Method and path | Authorization | Purpose |
| --- | --- | --- |
| `POST /auth/google/start` | Public | Begin Google OAuth flow. |
| `POST /auth/google/callback` | Public callback | Exchange OAuth code and create session. |
| `GET /me` | Authenticated | Current identity and organization memberships. |
| `POST /organizations` | Authenticated | Create organization and owner membership. |
| `GET /organizations/{organization_id}/projects` | Project read | List tenant projects. |
| `POST /organizations/{organization_id}/projects` | Project manage | Create a project. |
| `POST /integrations/{provider}/webhooks` | Provider signature | Receive signed source event; responds after durable acceptance. |
| `GET /workflow-runs` | Workflow read | Filter workflow activity by project/status/time. |
| `GET /workflow-runs/{run_id}` | Workflow read | Graph status, decisions, and redacted evidence. |
| `GET /approvals` | Approval read | List pending approval requests. |
| `POST /approvals/{approval_id}/decision` | Approval decide | Approve or reject a governed action. |
| `GET /actions` | Audit read | List executed actions and verification state. |
| `GET /dashboard/summary` | Dashboard read | Project health, sprint, blockers, and agent activity. |
| `POST /chat/sessions` | Chat use | Start scoped assistant session. |
| `POST /chat/sessions/{session_id}/messages` | Chat use | Submit a message; returns streaming event URL or response. |

## Key request contracts

### Approval decision

`POST /api/v1/approvals/{approval_id}/decision`

```json
{
  "decision": "approve",
  "reason": "The linked PR has merged and the ticket state is correct."
}
```

The server verifies the approver's scope, locks the approval, records the decision in the audit ledger, and resumes the stored graph checkpoint exactly once.

### Dashboard summary response

```json
{
  "organization_id": "018f…",
  "generated_at": "2026-07-12T10:00:00Z",
  "sprint": { "id": "018f…", "name": "Sprint 24", "completion_percent": 63 },
  "project_health": [{ "project_id": "018f…", "status": "at_risk", "open_blockers": 2 }],
  "recent_actions": [],
  "pending_approvals": 1
}
```

## Authorization matrix

| Capability | Owner/Admin | Manager | Member | Viewer |
| --- | --- | --- | --- | --- |
| Manage organization/integrations | Yes | No | No | No |
| Create projects and workflows | Yes | Scoped | No | No |
| Read project/dashboard | Yes | Scoped | Scoped | Scoped read-only |
| Decide approval | Yes | Scoped if policy permits | No | No |
| View audit/logs | Yes | Scoped | Limited own activity | No |

The generated OpenAPI document will become the source for typed frontend clients and connector contract tests in Phase 3.
