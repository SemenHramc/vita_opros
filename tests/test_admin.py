import pytest
import pytest_asyncio
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import Employee, Client, EmployeeClient
from bot.routers.admin import _check_admin
from tests.conftest import make_employee, make_client


class TestCheckAdmin:
    @pytest.mark.asyncio
    async def test_allows_admin(self, db_session):
        admin = make_employee(telegram_id=1, username="admin", full_name="Admin User", role="admin")
        db_session.add(admin)
        await db_session.commit()
        await db_session.refresh(admin)

        from unittest.mock import MagicMock
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = admin.telegram_id
        message.answer = AsyncMock() if False else None

        result = await _check_admin(message, db_session)
        assert result is not None
        assert result.role == "admin"

    @pytest.mark.asyncio
    async def test_rejects_employee(self, db_session):
        emp = make_employee(telegram_id=2, username="emp", full_name="Regular User", role="employee")
        db_session.add(emp)
        await db_session.commit()

        from unittest.mock import AsyncMock, MagicMock
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = emp.telegram_id
        message.answer = AsyncMock()

        result = await _check_admin(message, db_session)
        assert result is None
        message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_rejects_unknown_user(self, db_session):
        from unittest.mock import AsyncMock, MagicMock
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = 99999
        message.answer = AsyncMock()

        result = await _check_admin(message, db_session)
        assert result is None


class TestAdminAddEmployee:
    @pytest.mark.asyncio
    async def test_add_employee_creates_record(self, db_session):
        admin = make_employee(telegram_id=10, username="admin1", full_name="Admin", role="admin")
        db_session.add(admin)
        await db_session.commit()

        from unittest.mock import AsyncMock, MagicMock
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = admin.telegram_id
        message.text = "/admin_add_employee Ivan ivan_dev"
        message.answer = AsyncMock()

        from bot.routers.admin import cmd_add_employee
        await cmd_add_employee(message, db_session)

        result = await db_session.execute(
            select(Employee).where(Employee.telegram_username == "ivan_dev")
        )
        emp = result.scalar_one_or_none()
        assert emp is not None
        assert emp.full_name == "Ivan"
        assert emp.role == "employee"

    @pytest.mark.asyncio
    async def test_add_employee_strips_at_sign(self, db_session):
        admin = make_employee(telegram_id=11, username="admin2", full_name="Admin", role="admin")
        db_session.add(admin)
        await db_session.commit()

        from unittest.mock import AsyncMock, MagicMock
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = admin.telegram_id
        message.text = "/admin_add_employee Petr @petr_dev"
        message.answer = AsyncMock()

        from bot.routers.admin import cmd_add_employee
        await cmd_add_employee(message, db_session)

        result = await db_session.execute(
            select(Employee).where(Employee.telegram_username == "petr_dev")
        )
        emp = result.scalar_one_or_none()
        assert emp is not None

    @pytest.mark.asyncio
    async def test_add_employee_rejects_duplicate_username(self, db_session):
        admin = make_employee(telegram_id=12, username="admin3", full_name="Admin", role="admin")
        existing = make_employee(telegram_id=100, username="dup_user", full_name="Dup")
        db_session.add_all([admin, existing])
        await db_session.commit()

        from unittest.mock import AsyncMock, MagicMock
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = admin.telegram_id
        message.text = "/admin_add_employee New dup_user"
        message.answer = AsyncMock()

        from bot.routers.admin import cmd_add_employee
        await cmd_add_employee(message, db_session)

        assert "уже существует" in message.answer.call_args[0][0] or "уже существует" in message.answer.call_args.kwargs.get("text", "")

    @pytest.mark.asyncio
    async def test_add_employee_rejects_non_admin(self, db_session):
        emp = make_employee(telegram_id=13, username="notadmin", full_name="Not Admin", role="employee")
        db_session.add(emp)
        await db_session.commit()

        from unittest.mock import AsyncMock, MagicMock
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = emp.telegram_id
        message.text = "/admin_add_employee Test test_user"
        message.answer = AsyncMock()

        from bot.routers.admin import cmd_add_employee
        await cmd_add_employee(message, db_session)

        result = await db_session.execute(
            select(Employee).where(Employee.telegram_username == "test_user")
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_add_employee_wrong_format(self, db_session):
        admin = make_employee(telegram_id=14, username="admin4", full_name="Admin", role="admin")
        db_session.add(admin)
        await db_session.commit()

        from unittest.mock import AsyncMock, MagicMock
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = admin.telegram_id
        message.text = "/admin_add_employee Ivan"
        message.answer = AsyncMock()

        from bot.routers.admin import cmd_add_employee
        await cmd_add_employee(message, db_session)

        assert "Формат" in message.answer.call_args[0][0]


class TestAdminAddEmployeeWithId:
    @pytest.mark.asyncio
    async def test_add_employee_with_id(self, db_session):
        admin = make_employee(telegram_id=20, username="admin_id", full_name="Admin", role="admin")
        db_session.add(admin)
        await db_session.commit()

        from unittest.mock import AsyncMock, MagicMock
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = admin.telegram_id
        message.text = "/admin_add_employee_with_id 55555 Oleg oleg_dev"
        message.answer = AsyncMock()

        from bot.routers.admin import cmd_add_employee_with_id
        await cmd_add_employee_with_id(message, db_session)

        result = await db_session.execute(
            select(Employee).where(Employee.telegram_id == 55555)
        )
        emp = result.scalar_one_or_none()
        assert emp is not None
        assert emp.full_name == "Oleg"

    @pytest.mark.asyncio
    async def test_add_employee_with_id_invalid_id(self, db_session):
        admin = make_employee(telegram_id=21, username="admin_id2", full_name="Admin", role="admin")
        db_session.add(admin)
        await db_session.commit()

        from unittest.mock import AsyncMock, MagicMock
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = admin.telegram_id
        message.text = "/admin_add_employee_with_id abc Name user"
        message.answer = AsyncMock()

        from bot.routers.admin import cmd_add_employee_with_id
        await cmd_add_employee_with_id(message, db_session)

        assert "числом" in message.answer.call_args[0][0]

    @pytest.mark.asyncio
    async def test_add_employee_with_id_duplicate(self, db_session):
        admin = make_employee(telegram_id=22, username="admin_id3", full_name="Admin", role="admin")
        existing = make_employee(telegram_id=77777, username="existing_user", full_name="Existing")
        db_session.add_all([admin, existing])
        await db_session.commit()

        from unittest.mock import AsyncMock, MagicMock
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = admin.telegram_id
        message.text = "/admin_add_employee_with_id 77777 New new_user"
        message.answer = AsyncMock()

        from bot.routers.admin import cmd_add_employee_with_id
        await cmd_add_employee_with_id(message, db_session)

        assert "уже существует" in message.answer.call_args[0][0]


class TestAdminRemoveEmployee:
    @pytest.mark.asyncio
    async def test_remove_employee_by_username(self, db_session):
        admin = make_employee(telegram_id=30, username="admin_rm", full_name="Admin", role="admin")
        target = make_employee(telegram_id=301, username="target_user", full_name="Target")
        db_session.add_all([admin, target])
        await db_session.commit()

        from unittest.mock import AsyncMock, MagicMock
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = admin.telegram_id
        message.text = "/admin_remove_employee target_user"
        message.answer = AsyncMock()

        from bot.routers.admin import cmd_remove_employee
        await cmd_remove_employee(message, db_session)

        result = await db_session.execute(
            select(Employee).where(Employee.telegram_username == "target_user")
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_remove_employee_by_id(self, db_session):
        admin = make_employee(telegram_id=31, username="admin_rm2", full_name="Admin", role="admin")
        target = make_employee(telegram_id=302, username="target2", full_name="Target2")
        db_session.add_all([admin, target])
        await db_session.commit()

        from unittest.mock import AsyncMock, MagicMock
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = admin.telegram_id
        message.text = f"/admin_remove_employee {target.telegram_id}"
        message.answer = AsyncMock()

        from bot.routers.admin import cmd_remove_employee
        await cmd_remove_employee(message, db_session)

        result = await db_session.execute(
            select(Employee).where(Employee.id == target.id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_remove_employee_not_found(self, db_session):
        admin = make_employee(telegram_id=32, username="admin_rm3", full_name="Admin", role="admin")
        db_session.add(admin)
        await db_session.commit()

        from unittest.mock import AsyncMock, MagicMock
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = admin.telegram_id
        message.text = "/admin_remove_employee nonexistent"
        message.answer = AsyncMock()

        from bot.routers.admin import cmd_remove_employee
        await cmd_remove_employee(message, db_session)

        assert "не найден" in message.answer.call_args[0][0]

    @pytest.mark.asyncio
    async def test_remove_employee_cascades_responses(self, db_session):
        admin = make_employee(telegram_id=33, username="admin_cas", full_name="Admin", role="admin")
        target = make_employee(telegram_id=303, username="cascade_user", full_name="Cascade")
        db_session.add_all([admin, target])
        await db_session.commit()
        await db_session.refresh(target)

        from bot.models import Response
        r = Response(employee_id=target.id, week_start=date(2026, 5, 11))
        db_session.add(r)
        await db_session.commit()

        from unittest.mock import AsyncMock, MagicMock
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = admin.telegram_id
        message.text = f"/admin_remove_employee {target.telegram_id}"
        message.answer = AsyncMock()

        from bot.routers.admin import cmd_remove_employee
        await cmd_remove_employee(message, db_session)

        result = await db_session.execute(
            select(Response).where(Response.employee_id == target.id)
        )
        assert result.scalar_one_or_none() is None


class TestAdminListEmployees:
    @pytest.mark.asyncio
    async def test_list_employees_shows_all(self, db_session):
        admin = make_employee(telegram_id=40, username="admin_list", full_name="Admin", role="admin")
        emp1 = make_employee(telegram_id=401, username="list_emp1", full_name="Alice")
        emp2 = make_employee(telegram_id=402, username="list_emp2", full_name="Bob")
        db_session.add_all([admin, emp1, emp2])
        await db_session.commit()

        from unittest.mock import AsyncMock, MagicMock
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = admin.telegram_id
        message.text = "/admin_list_employees"
        message.answer = AsyncMock()

        from bot.routers.admin import cmd_list_employees
        await cmd_list_employees(message, db_session)

        text = message.answer.call_args[0][0]
        assert "Alice" in text
        assert "Bob" in text

    @pytest.mark.asyncio
    async def test_list_employees_includes_admin(self, db_session):
        admin = make_employee(telegram_id=41, username="admin_empty", full_name="Admin", role="admin")
        db_session.add(admin)
        await db_session.commit()

        from unittest.mock import AsyncMock, MagicMock
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = admin.telegram_id
        message.text = "/admin_list_employees"
        message.answer = AsyncMock()

        from bot.routers.admin import cmd_list_employees
        await cmd_list_employees(message, db_session)

        text = message.answer.call_args[0][0]
        assert "Admin" in text
        assert "admin_empty" in text


class TestAdminClientCRUD:
    @pytest.mark.asyncio
    async def test_add_client(self, db_session):
        admin = make_employee(telegram_id=50, username="admin_cl", full_name="Admin", role="admin")
        db_session.add(admin)
        await db_session.commit()

        from unittest.mock import AsyncMock, MagicMock
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = admin.telegram_id
        message.text = "/admin_add_client BigCorp"
        message.answer = AsyncMock()

        from bot.routers.admin import cmd_add_client
        await cmd_add_client(message, db_session)

        result = await db_session.execute(
            select(Client).where(Client.name == "BigCorp")
        )
        client = result.scalar_one_or_none()
        assert client is not None

    @pytest.mark.asyncio
    async def test_add_client_duplicate(self, db_session):
        admin = make_employee(telegram_id=51, username="admin_cl2", full_name="Admin", role="admin")
        existing_client = make_client(name="DupClient")
        db_session.add_all([admin, existing_client])
        await db_session.commit()

        from unittest.mock import AsyncMock, MagicMock
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = admin.telegram_id
        message.text = "/admin_add_client DupClient"
        message.answer = AsyncMock()

        from bot.routers.admin import cmd_add_client
        await cmd_add_client(message, db_session)

        assert "уже существует" in message.answer.call_args[0][0]

    @pytest.mark.asyncio
    async def test_remove_client(self, db_session):
        admin = make_employee(telegram_id=52, username="admin_cl3", full_name="Admin", role="admin")
        client = make_client(name="RemoveMe")
        db_session.add_all([admin, client])
        await db_session.commit()
        await db_session.refresh(client)

        from unittest.mock import AsyncMock, MagicMock
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = admin.telegram_id
        message.text = "/admin_remove_client RemoveMe"
        message.answer = AsyncMock()

        from bot.routers.admin import cmd_remove_client
        await cmd_remove_client(message, db_session)

        result = await db_session.execute(
            select(Client).where(Client.id == client.id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_remove_client_not_found(self, db_session):
        admin = make_employee(telegram_id=53, username="admin_cl4", full_name="Admin", role="admin")
        db_session.add(admin)
        await db_session.commit()

        from unittest.mock import AsyncMock, MagicMock
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = admin.telegram_id
        message.text = "/admin_remove_client GhostClient"
        message.answer = AsyncMock()

        from bot.routers.admin import cmd_remove_client
        await cmd_remove_client(message, db_session)

        assert "не найден" in message.answer.call_args[0][0]

    @pytest.mark.asyncio
    async def test_list_clients(self, db_session):
        admin = make_employee(telegram_id=54, username="admin_cl5", full_name="Admin", role="admin")
        c1 = make_client(name="Alpha")
        c2 = make_client(name="Beta")
        db_session.add_all([admin, c1, c2])
        await db_session.commit()

        from unittest.mock import AsyncMock, MagicMock
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = admin.telegram_id
        message.text = "/admin_list_clients"
        message.answer = AsyncMock()

        from bot.routers.admin import cmd_list_clients
        await cmd_list_clients(message, db_session)

        text = message.answer.call_args[0][0]
        assert "Alpha" in text
        assert "Beta" in text

    @pytest.mark.asyncio
    async def test_list_clients_empty(self, db_session):
        admin = make_employee(telegram_id=55, username="admin_cl6", full_name="Admin", role="admin")
        db_session.add(admin)
        await db_session.commit()

        from unittest.mock import AsyncMock, MagicMock
        message = MagicMock()
        message.from_user = MagicMock()
        message.from_user.id = admin.telegram_id
        message.text = "/admin_list_clients"
        message.answer = AsyncMock()

        from bot.routers.admin import cmd_list_clients
        await cmd_list_clients(message, db_session)

        text = message.answer.call_args[0][0]
        assert "пуст" in text.lower()
