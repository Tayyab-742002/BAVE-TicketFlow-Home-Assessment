from fastapi import APIRouter, status
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep, VisibleTicket
from app.models.comment import Comment
from app.schemas.comment import CommentCreate, CommentRead
from app.services.websocket_manager import manager

router = APIRouter(prefix="/tickets/{ticket_id}/comments", tags=["comments"])


@router.post("", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
async def create_comment(
    payload: CommentCreate, ticket: VisibleTicket, session: SessionDep, current_user: CurrentUser
) -> Comment:
    comment = Comment(
        ticket_id=ticket.id,
        author_id=current_user.id,
        author_role=current_user.role,
        body=payload.body,
    )
    session.add(comment)
    await session.commit()
    await session.refresh(comment)

    event = {
        "event": "comment.created",
        "ticket_id": str(ticket.id),
        "data": CommentRead.model_validate(comment).model_dump(mode="json"),
    }
    await manager.broadcast_to_ticket(ticket.id, event)
    await manager.broadcast_to_dashboard(event)

    return comment


@router.get("", response_model=list[CommentRead])
async def list_comments(ticket: VisibleTicket, session: SessionDep) -> list[Comment]:
    result = await session.exec(
        select(Comment).where(Comment.ticket_id == ticket.id).order_by(Comment.created_at)
    )
    return result.all()
