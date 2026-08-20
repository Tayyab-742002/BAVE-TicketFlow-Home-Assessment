from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_tickets: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
