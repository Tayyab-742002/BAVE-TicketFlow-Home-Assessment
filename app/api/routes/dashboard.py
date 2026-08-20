from fastapi import APIRouter
from sqlalchemy import func
from sqlmodel import select

from app.api.deps import RedisDep, RequireAgent, SessionDep
from app.models.enums import TicketPriority, TicketStatus
from app.models.ticket import Ticket
from app.schemas.dashboard import DashboardStats
from app.services.cache_service import (
    DASHBOARD_STATS_KEY,
    DASHBOARD_STATS_TTL_SECONDS,
    get_cached,
    set_cached,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/stats",
    response_model=DashboardStats,
    summary="Agent dashboard counts (Agent-only)",
    description="Total ticket count plus a breakdown by status and priority — "
    "every enum value is always present, with `0` for anything with no tickets. "
    "Cached in Redis for 60s, invalidated immediately on any ticket write.",
)
async def get_dashboard_stats(
    session: SessionDep, redis: RedisDep, agent: RequireAgent
) -> DashboardStats:
    cached = await get_cached(redis, DASHBOARD_STATS_KEY)
    if cached is not None:
        return DashboardStats.model_validate(cached)

    total = (await session.exec(select(func.count()).select_from(Ticket))).one()

    by_status_rows = (
        await session.exec(select(Ticket.status, func.count()).group_by(Ticket.status))
    ).all()
    by_priority_rows = (
        await session.exec(select(Ticket.priority, func.count()).group_by(Ticket.priority))
    ).all()

    by_status = {s.value: 0 for s in TicketStatus}
    by_status.update({status.value: count for status, count in by_status_rows})

    by_priority = {p.value: 0 for p in TicketPriority}
    by_priority.update({priority.value: count for priority, count in by_priority_rows})

    stats = DashboardStats(total_tickets=total, by_status=by_status, by_priority=by_priority)

    await set_cached(
        redis, DASHBOARD_STATS_KEY, stats.model_dump(mode="json"), DASHBOARD_STATS_TTL_SECONDS
    )
    return stats
