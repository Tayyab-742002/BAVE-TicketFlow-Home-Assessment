import hashlib
import hmac
import json
import logging
from typing import Any

import httpx
from sqlmodel import select

from app.core.time import utcnow
from app.db.session import async_session_factory
from app.models.webhook import WebhookDelivery, WebhookRegistration

logger = logging.getLogger("ticketflow")

WEBHOOK_TIMEOUT_SECONDS = 5.0


def sign_payload(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


async def dispatch_event(event_type: str, data: dict[str, Any]) -> None:
    """Signs and POSTs `event_type` to every active registration subscribed to it,
    logging one WebhookDelivery row per attempt. Opens its own DB session rather
    than reusing a request-scoped one, since this runs as a background task after
    the triggering request has already returned its response."""
    envelope = {"event": event_type, "data": data, "timestamp": utcnow().isoformat()}
    body = json.dumps(envelope, sort_keys=True).encode()

    async with async_session_factory() as session:
        result = await session.exec(
            select(WebhookRegistration).where(WebhookRegistration.is_active)
        )
        registrations = [reg for reg in result.all() if event_type in reg.event_types]
        if not registrations:
            return

        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
            for registration in registrations:
                status_code: int | None = None
                success = False
                try:
                    response = await client.post(
                        registration.url,
                        content=body,
                        headers={
                            "Content-Type": "application/json",
                            "X-TicketFlow-Signature": sign_payload(registration.secret, body),
                            "X-TicketFlow-Event": event_type,
                        },
                    )
                    status_code = response.status_code
                    success = response.is_success
                except httpx.HTTPError:
                    logger.exception("Webhook delivery failed for %s", registration.url)

                session.add(
                    WebhookDelivery(
                        webhook_registration_id=registration.id,
                        event_type=event_type,
                        payload=envelope,
                        response_status_code=status_code,
                        success=success,
                    )
                )

        await session.commit()
