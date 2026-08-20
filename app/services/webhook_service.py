import asyncio
import hashlib
import hmac
import json
import logging
import uuid
from typing import Any

import httpx
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.time import utcnow
from app.db.session import async_session_factory
from app.models.webhook import WebhookDelivery, WebhookRegistration

logger = logging.getLogger("ticketflow")

WEBHOOK_TIMEOUT_SECONDS = 5.0
MAX_ATTEMPTS = 4
BACKOFF_BASE_SECONDS = 1.0  # attempt delays: 1s, 2s, 4s


def sign_payload(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


async def _deliver_with_retries(
    client: httpx.AsyncClient,
    session: AsyncSession,
    registration: WebhookRegistration,
    event_type: str,
    envelope: dict[str, Any],
    body: bytes,
    idempotency_key: str,
) -> None:
    headers = {
        "Content-Type": "application/json",
        "X-TicketFlow-Signature": sign_payload(registration.secret, body),
        "X-TicketFlow-Event": event_type,
        "Idempotency-Key": idempotency_key,
    }

    for attempt in range(1, MAX_ATTEMPTS + 1):
        status_code: int | None = None
        success = False
        retryable = True
        try:
            response = await client.post(registration.url, content=body, headers=headers)
            status_code = response.status_code
            success = response.is_success
            # A 4xx means the receiver rejected the request itself (bad signature,
            # gone endpoint, etc.) — retrying the identical request won't change
            # that outcome, so only 5xx/network failures are worth retrying.
            retryable = status_code >= 500
        except httpx.HTTPError:
            logger.exception(
                "Webhook delivery attempt %d/%d failed for %s", attempt, MAX_ATTEMPTS, registration.url
            )

        session.add(
            WebhookDelivery(
                webhook_registration_id=registration.id,
                event_type=event_type,
                payload=envelope,
                response_status_code=status_code,
                success=success,
                idempotency_key=idempotency_key,
                attempt_number=attempt,
            )
        )
        await session.commit()

        if success or not retryable:
            return

        if attempt < MAX_ATTEMPTS:
            await asyncio.sleep(BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))


async def dispatch_event(event_type: str, data: dict[str, Any]) -> None:
    """Signs and POSTs `event_type` to every active registration subscribed to it,
    retrying 5xx/network failures with exponential backoff. Every attempt for one
    logical event (across every registration and every retry) shares a single
    idempotency key, so a receiver hit twice due to a retry can dedupe. Opens its
    own DB session rather than reusing a request-scoped one, since this runs as a
    background task after the triggering request has already returned its response."""
    envelope = {"event": event_type, "data": data, "timestamp": utcnow().isoformat()}
    body = json.dumps(envelope, sort_keys=True).encode()
    idempotency_key = str(uuid.uuid4())

    async with async_session_factory() as session:
        result = await session.exec(
            select(WebhookRegistration).where(WebhookRegistration.is_active)
        )
        registrations = [reg for reg in result.all() if event_type in reg.event_types]
        if not registrations:
            return

        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
            for registration in registrations:
                await _deliver_with_retries(
                    client, session, registration, event_type, envelope, body, idempotency_key
                )
