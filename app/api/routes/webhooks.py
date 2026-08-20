import secrets
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.api.deps import RequireAgent, SessionDep
from app.models.webhook import WebhookDelivery, WebhookRegistration
from app.schemas.webhook import (
    WebhookDeliveryRead,
    WebhookRegistrationCreate,
    WebhookRegistrationRead,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("", response_model=WebhookRegistrationRead, status_code=status.HTTP_201_CREATED)
async def register_webhook(
    payload: WebhookRegistrationCreate, session: SessionDep, agent: RequireAgent
) -> WebhookRegistration:
    webhook = WebhookRegistration(
        agent_id=agent.id,
        url=str(payload.url),
        secret=secrets.token_urlsafe(32),
        event_types=payload.event_types,
    )
    session.add(webhook)
    await session.commit()
    await session.refresh(webhook)
    return webhook


@router.get("", response_model=list[WebhookRegistrationRead])
async def list_webhooks(session: SessionDep, agent: RequireAgent) -> list[WebhookRegistration]:
    result = await session.exec(
        select(WebhookRegistration).order_by(WebhookRegistration.created_at.desc())
    )
    return result.all()


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(webhook_id: uuid.UUID, session: SessionDep, agent: RequireAgent) -> None:
    webhook = await session.get(WebhookRegistration, webhook_id)
    if webhook is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Webhook registration not found")
    await session.delete(webhook)
    await session.commit()


@router.get("/{webhook_id}/deliveries", response_model=list[WebhookDeliveryRead])
async def list_webhook_deliveries(
    webhook_id: uuid.UUID, session: SessionDep, agent: RequireAgent
) -> list[WebhookDelivery]:
    webhook = await session.get(WebhookRegistration, webhook_id)
    if webhook is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Webhook registration not found")

    result = await session.exec(
        select(WebhookDelivery)
        .where(WebhookDelivery.webhook_registration_id == webhook_id)
        .order_by(WebhookDelivery.attempted_at.desc())
    )
    return result.all()
