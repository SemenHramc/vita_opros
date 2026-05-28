from datetime import date, datetime
from pydantic import BaseModel


class EmployeeOut(BaseModel):
    id: int
    telegram_id: int
    telegram_username: str | None
    full_name: str
    role: str

    model_config = {"from_attributes": True}


class ClientOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class ClientResponseOut(BaseModel):
    id: int
    response_id: int
    client_id: int
    client_name: str | None = None
    score_workload: int | None
    has_blockers: bool | None
    blocker_text: str | None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ResponseOut(BaseModel):
    id: int
    employee_id: int
    employee_name: str | None = None
    week_start: date
    score_workload: int | None
    score_deadlines: int | None
    score_communication: int | None
    has_blockers: bool | None
    blocker_text: str | None
    score_energy: int | None
    has_comment: bool | None
    comment_text: str | None
    completed_at: datetime | None
    has_midweek_updates: bool = False
    client_responses: list[ClientResponseOut] = []

    model_config = {"from_attributes": True}


class WeekSummary(BaseModel):
    week_start: date
    total_employees: int
    completed_surveys: int
    completion_rate: float
    avg_workload: float | None
    avg_deadlines: float | None
    avg_communication: float | None
    avg_energy: float | None
    blockers: list[dict]
    comments: list[dict]


class ClientHeatmapItem(BaseModel):
    client_name: str
    employee_name: str
    score_workload: int | None


class ClientBlockerItem(BaseModel):
    client_name: str
    employee_name: str
    blocker_text: str