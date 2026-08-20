API_DESCRIPTION = """
Real-time support-ticketing backend — Bave technical assessment.

**Auth** — JWT access + refresh tokens. Click **Authorize** (top right) after
`POST /auth/login`; it uses the OAuth2 password flow, so put your email in the
`username` field. The button then attaches your access token to every
"Try it out" call automatically.

**Roles** — `customer` (sees/manages only their own tickets) and `agent` (sees
and acts on all tickets). One agent account is seeded at startup — credentials
are in the README, not here.

**WebSockets** — browsers can't set custom headers on a WebSocket handshake, so
the access token travels as a query param instead:
`ws://.../ws/tickets/{ticket_id}?token=<access_token>`.

**Webhooks** — registered endpoints receive an HMAC-SHA256 signature in the
`X-TicketFlow-Signature` header (`sha256=<hex>`), computed over the exact raw
JSON body with that registration's own secret. Failed deliveries retry with
exponential backoff; every attempt (success or failure) is logged.
"""

TAGS_METADATA = [
    {
        "name": "auth",
        "description": "Registration, login, and token refresh. Registration always creates a Customer — the Agent account is seeded, not self-served.",
    },
    {
        "name": "tickets",
        "description": "Ticket CRUD, filtering/search/pagination, and the Agent-only forward-only status workflow.",
    },
    {
        "name": "comments",
        "description": "Comment thread per ticket, visible to whoever can see the ticket itself.",
    },
    {
        "name": "dashboard",
        "description": "Agent-only aggregate stats, cached in Redis with explicit invalidation on ticket writes.",
    },
    {
        "name": "webhooks",
        "description": "Agent-managed outgoing webhook registrations and their delivery logs.",
    },
    {
        "name": "websocket",
        "description": "Live ticket/dashboard event channels. See the top-level description for how auth works here — it differs from the REST endpoints.",
    },
]
