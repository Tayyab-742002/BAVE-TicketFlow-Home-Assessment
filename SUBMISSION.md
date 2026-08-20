# Submission Notes

## Stretch goals attempted

The brief asks for up to two; three were attempted.

1. **n8n workflow automation**  `docker-compose.yml` runs n8n alongside the API; `automation/n8n-workflow.json` is an importable workflow (Webhook → Switch → HTTP Request, all built-in nodes, no Code node) that auto-escalates high-priority `ticket.created` events and notifies on `resolved` status changes. Registered as a normal webhook subscriber  n8n doesn't get special treatment in the API, it just consumes the same signed webhook events any other integration would.
2. **Webhook reliability**  `app/services/webhook_service.py` retries failed deliveries up to 4 times with exponential backoff (1s/2s/4s), retrying only 5xx/network failures (not 4xx, which won't succeed by resending). Every attempt shares one `Idempotency-Key` header per logical event across all registrations and retries, and is individually logged (`GET /webhooks/{id}/deliveries`).
3. **Rate limiting**  Redis-backed fixed-window limiter (`app/api/deps.py`) on `POST /auth/register` (10/min/IP), `POST /auth/login` (20/min/IP), and `POST /tickets` (30/min/account). IP-keyed for the two pre-auth endpoints (no user identity exists yet); account-keyed for ticket creation (fairer than IP — doesn't throttle every customer behind one shared office IP together).

Not attempted: automated tests / CI, cloud deployment.

## AI tool disclosure

AI (Claude Code) was used as an assistant throughout the build  generating documentation, helping debug issues, and producing boilerplate/scaffolding (project structure, repetitive endpoint/schema patterns, Docker and config setup).

Every piece of AI-assisted code was reviewed and its logic tested by me before being accepted  nothing was merged blindly. Migrations in particular were checked line-by-line before being applied, which caught real issues (an enum case-sensitivity bug, a recurring missing import in generated migration files) before they reached the database. Architecture decisions, the tech stack, which stretch goals to build, and how to resolve ambiguous requirements were mine.

