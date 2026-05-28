from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from sqlalchemy import select, func, and_, case
from sqlalchemy.orm import selectinload

from bot.database import async_session
from bot.models import (
    Employee, Response, ClientResponse, Client, EmployeeClient, VacationPeriod,
)
from bot.services.export import export_week_csv, export_week_xlsx
from bot.utils import get_week_start
from dashboard.api.schemas import (
    ResponseOut, ClientResponseOut, WeekSummary, ClientHeatmapItem, ClientBlockerItem,
)

router = APIRouter()


@router.get("/weeks", response_model=list[date])
async def get_available_weeks():
    async with async_session() as session:
        result = await session.execute(
            select(Response.week_start).distinct().order_by(Response.week_start.desc())
        )
        return list(result.scalars().all())


@router.get("/employees", response_model=list[dict])
async def get_employees():
    async with async_session() as session:
        result = await session.execute(
            select(Employee).order_by(Employee.full_name)
        )
        employees = result.scalars().all()
        return [
            {
                "id": e.id,
                "full_name": e.full_name,
                "telegram_username": e.telegram_username,
                "role": e.role,
            }
            for e in employees
        ]


@router.get("/clients", response_model=list[dict])
async def get_clients():
    async with async_session() as session:
        result = await session.execute(select(Client).order_by(Client.name))
        clients = result.scalars().all()
        return [{"id": c.id, "name": c.name} for c in clients]


@router.get("/summary/{week_start}", response_model=WeekSummary)
async def get_week_summary(week_start: date):
    async with async_session() as session:
        total = await session.execute(select(func.count()).select_from(Employee))
        total_employees = total.scalar()

        result = await session.execute(
            select(Response)
            .where(
                Response.week_start == week_start,
                Response.completed_at.isnot(None),
            )
            .order_by(Response.employee_id)
        )
        responses = result.scalars().all()

        completed = len(responses)

        if completed > 0:
            wl_vals = [r.score_workload for r in responses if r.score_workload is not None]
            dl_vals = [r.score_deadlines for r in responses if r.score_deadlines is not None]
            comm_vals = [r.score_communication for r in responses if r.score_communication is not None]
            en_vals = [r.score_energy for r in responses if r.score_energy is not None]
            avg_wl = sum(wl_vals) / len(wl_vals) if wl_vals else None
            avg_dl = sum(dl_vals) / len(dl_vals) if dl_vals else None
            avg_comm = sum(comm_vals) / len(comm_vals) if comm_vals else None
            avg_en = sum(en_vals) / len(en_vals) if en_vals else None
        else:
            avg_wl = avg_dl = avg_comm = avg_en = None

        emp_ids = [r.employee_id for r in responses]
        emp_result = await session.execute(
            select(Employee).where(Employee.id.in_(emp_ids))
        )
        emp_map = {e.id: e.full_name for e in emp_result.scalars().all()}

        blockers = []
        comments = []
        for r in responses:
            name = emp_map.get(r.employee_id, "?")
            if r.has_blockers and r.blocker_text:
                blockers.append({"employee": name, "text": r.blocker_text})
            if r.has_comment and r.comment_text:
                comments.append({"employee": name, "text": r.comment_text})

        return WeekSummary(
            week_start=week_start,
            total_employees=total_employees,
            completed_surveys=completed,
            completion_rate=round(completed / total_employees * 100, 1) if total_employees else 0,
            avg_workload=round(avg_wl, 2) if avg_wl else None,
            avg_deadlines=round(avg_dl, 2) if avg_dl else None,
            avg_communication=round(avg_comm, 2) if avg_comm else None,
            avg_energy=round(avg_en, 2) if avg_en else None,
            blockers=blockers,
            comments=comments,
        )


@router.get("/responses/{week_start}", response_model=list[ResponseOut])
async def get_week_responses(week_start: date):
    async with async_session() as session:
        result = await session.execute(
            select(Response)
            .where(
                Response.week_start == week_start,
            )
            .options(
                selectinload(Response.employee),
                selectinload(Response.client_responses).selectinload(ClientResponse.client),
            )
            .order_by(Response.employee_id)
        )
        responses = result.scalars().all()

        out = []
        for r in responses:
            emp = r.employee

            has_midweek = any(
                cr.updated_at is not None and r.started_at is not None and cr.updated_at > r.started_at
                for cr in r.client_responses
            )

            cr_out = []
            for cr in r.client_responses:
                client = cr.client
                cr_out.append(ClientResponseOut(
                    id=cr.id,
                    response_id=cr.response_id,
                    client_id=cr.client_id,
                    client_name=client.name if client else "?",
                    score_workload=cr.score_workload,
                    has_blockers=cr.has_blockers,
                    blocker_text=cr.blocker_text,
                    updated_at=cr.updated_at,
                ))

            out.append(ResponseOut(
                id=r.id,
                employee_id=r.employee_id,
                employee_name=emp.full_name if emp else "?",
                week_start=r.week_start,
                score_workload=r.score_workload,
                score_deadlines=r.score_deadlines,
                score_communication=r.score_communication,
                has_blockers=r.has_blockers,
                blocker_text=r.blocker_text,
                score_energy=r.score_energy,
                has_comment=r.has_comment,
                comment_text=r.comment_text,
                completed_at=r.completed_at,
                has_midweek_updates=has_midweek,
                client_responses=cr_out,
            ))

        return out


@router.get("/heatmap/{week_start}", response_model=list[ClientHeatmapItem])
async def get_client_heatmap(week_start: date, client_id: Optional[int] = None):
    async with async_session() as session:
        query = (
            select(ClientResponse)
            .join(Response, ClientResponse.response_id == Response.id)
            .where(Response.week_start == week_start, Response.completed_at.isnot(None))
            .options(
                selectinload(ClientResponse.client),
                selectinload(ClientResponse.response).selectinload(Response.employee),
            )
        )
        if client_id:
            query = query.where(ClientResponse.client_id == client_id)

        result = await session.execute(query)
        client_responses = result.scalars().all()

        items = []
        for cr in client_responses:
            client = cr.client
            emp = cr.response.employee if cr.response else None
            items.append(ClientHeatmapItem(
                client_name=client.name if client else "?",
                employee_name=emp.full_name if emp else "?",
                score_workload=cr.score_workload,
            ))

        return items


@router.get("/client-blockers/{week_start}", response_model=list[ClientBlockerItem])
async def get_client_blockers(week_start: date, client_id: Optional[int] = None):
    async with async_session() as session:
        q = (
            select(ClientResponse)
            .join(Response, ClientResponse.response_id == Response.id)
            .where(
                Response.week_start == week_start,
                Response.completed_at.isnot(None),
                ClientResponse.has_blockers == True,
            )
            .options(
                selectinload(ClientResponse.client),
                selectinload(ClientResponse.response).selectinload(Response.employee),
            )
        )
        if client_id:
            q = q.where(ClientResponse.client_id == client_id)

        result = await session.execute(q)
        client_responses = result.scalars().all()

        items = []
        for cr in client_responses:
            client = cr.client
            emp = cr.response.employee if cr.response else None
            items.append(ClientBlockerItem(
                client_name=client.name if client else "?",
                employee_name=emp.full_name if emp else "?",
                blocker_text=cr.blocker_text or "",
            ))

        return items


@router.get("/dynamics")
async def get_dynamics(employee_id: Optional[int] = None):
    async with async_session() as session:
        q = (
            select(Response)
            .where(Response.completed_at.isnot(None))
            .order_by(Response.week_start)
        )
        if employee_id:
            q = q.where(Response.employee_id == employee_id)

        result = await session.execute(q)
        responses = result.scalars().all()

        weeks = {}
        for r in responses:
            week = r.week_start.isoformat()
            if week not in weeks:
                weeks[week] = {
                    "week_start": week,
                    "responses": [],
                }
            weeks[week]["responses"].append({
                "employee_id": r.employee_id,
                "score_workload": r.score_workload,
                "score_deadlines": r.score_deadlines,
                "score_communication": r.score_communication,
                "score_energy": r.score_energy,
            })

        result_list = []
        for week, data in sorted(weeks.items()):
            resps = data["responses"]
            n = len(resps)
            wl_vals = [r["score_workload"] for r in resps if r["score_workload"] is not None]
            dl_vals = [r["score_deadlines"] for r in resps if r["score_deadlines"] is not None]
            comm_vals = [r["score_communication"] for r in resps if r["score_communication"] is not None]
            en_vals = [r["score_energy"] for r in resps if r["score_energy"] is not None]
            result_list.append({
                "week_start": week,
                "avg_workload": round(sum(wl_vals) / len(wl_vals), 2) if wl_vals else None,
                "avg_deadlines": round(sum(dl_vals) / len(dl_vals), 2) if dl_vals else None,
                "avg_communication": round(sum(comm_vals) / len(comm_vals), 2) if comm_vals else None,
                "avg_energy": round(sum(en_vals) / len(en_vals), 2) if en_vals else None,
                "count": n,
            })

        return result_list


@router.get("/export/{week_start}/csv")
async def export_csv(week_start: date):
    content = await export_week_csv(week_start)
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=survey_{week_start}.csv"},
    )


@router.get("/export/{week_start}/xlsx")
async def export_excel(week_start: date):
    content = await export_week_xlsx(week_start)
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=survey_{week_start}.xlsx"},
    )


# Vacation Calendar

class VacationPeriodOut(BaseModel):
    start: date
    end: date
    days: int
    application_date: Optional[date] = None

    @field_validator('start', 'end', 'application_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if v is None or v == '':
            return None
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            if 'T' in v:
                v = v.split('T')[0]
            return date.fromisoformat(v)
        return v


class EmployeeVacationOut(BaseModel):
    employee_id: int
    name: str
    hire_date: Optional[date] = None
    total_days: Optional[int] = None
    periods: list[VacationPeriodOut] = []
    remaining: Optional[int] = None


class VacationSheetOut(BaseModel):
    year: str
    name: str
    employees: list[EmployeeVacationOut] = []


@router.get("/vacations", response_model=list[VacationSheetOut])
async def get_vacations():
    async with async_session() as session:
        result = await session.execute(
            select(Employee)
            .options(selectinload(Employee.vacation_periods))
            .order_by(Employee.full_name)
        )
        employees = result.scalars().all()

        years = {}
        known_years = sorted({str(p.year) for emp in employees for p in emp.vacation_periods}, reverse=True)

        if not known_years:
            return []

        for year in known_years:
            years[year] = {}
            for emp in employees:
                years[year][emp.id] = {
                    "employee_id": emp.id,
                    "name": emp.full_name,
                    "hire_date": emp.hire_date,
                    "total_days": emp.total_vacation_days,
                    "periods": [],
                }

        for emp in employees:
            for p in emp.vacation_periods:
                year = str(p.year)
                years[year][emp.id]["periods"].append(VacationPeriodOut(
                    start=p.start_date,
                    end=p.end_date,
                    days=p.days_count,
                    application_date=p.application_date,
                ))

        result_list = []
        for year in sorted(years.keys(), reverse=True):
            employees_list = []
            for emp_id in sorted(years[year].keys()):
                emp_data = years[year][emp_id]
                used = sum(p.days for p in emp_data["periods"])
                total = emp_data["total_days"] or 0
                remaining = total - used if total > 0 else None
                employees_list.append(EmployeeVacationOut(
                    employee_id=emp_data["employee_id"],
                    name=emp_data["name"],
                    hire_date=emp_data["hire_date"],
                    total_days=emp_data["total_days"],
                    periods=emp_data["periods"],
                    remaining=remaining,
                ))
            result_list.append(VacationSheetOut(
                year=year,
                name=f"Vacanations {year}",
                employees=employees_list,
            ))

        return result_list


class VacationPeriodIn(BaseModel):
    start: date
    end: date
    days: int
    application_date: Optional[date] = None
    period_number: int = 1


class EmployeeVacationIn(BaseModel):
    employee_id: int
    periods: list[VacationPeriodIn] = []


class VacationSheetIn(BaseModel):
    year: str
    employees: list[EmployeeVacationIn] = []


@router.post("/vacations")
async def save_vacations(data: list[VacationSheetIn]):
    async with async_session() as session:
        try:
            for sheet_data in data:
                year = int(sheet_data.year)
                for emp_data in sheet_data.employees:
                    emp_id = emp_data.employee_id

                    sorted_periods = sorted(emp_data.periods, key=lambda p: p.start)
                    for index, p in enumerate(sorted_periods):
                        actual_days = (p.end - p.start).days + 1
                        if p.end < p.start:
                            raise ValueError("End date must be after start date")
                        if p.days != actual_days:
                            raise ValueError("Days count does not match date range")
                        if index > 0 and sorted_periods[index - 1].end >= p.start:
                            raise ValueError("Vacation periods cannot overlap")
                    
                    old = await session.execute(
                        select(VacationPeriod).where(
                            VacationPeriod.employee_id == emp_id,
                            VacationPeriod.year == year,
                        )
                    )
                    for old_period in old.scalars().all():
                        await session.delete(old_period)
                    
                    for p in sorted_periods:
                        session.add(VacationPeriod(
                            employee_id=emp_id,
                            year=year,
                            start_date=p.start,
                            end_date=p.end,
                            days_count=p.days,
                            application_date=p.application_date,
                            period_number=p.period_number,
                        ))

            await session.commit()
        except ValueError as exc:
            await session.rollback()
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "ok"}
