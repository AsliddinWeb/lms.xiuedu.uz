"""Phase 2a — Academic structure + 559-qaror validatsiyalar.

Smoke test: super admin barcha CRUD'larni amalga oshiradi, talaba 403 oladi.
559-qaror 14 (distance flag) va 15 (300/30 quota) bandlari validatsiya qilinadi.
"""

from __future__ import annotations

import uuid

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete, text

from app.core.database import SessionLocal
from app.modules.academic.models import (
    AcademicCalendar,
    Curriculum,
    CurriculumSubject,
    Department,
    Faculty,
    Specialty,
    Subject,
    SubjectPrerequisite,
)
from app.modules.auth.models import LoginAttempt, UserSession
from app.modules.organizations.models import Organization

VALID_PASSWORD = "Str0ng!Password"
ADMIN_EMAIL = "admin@xiuedu.uz"
ADMIN_PASSWORD = "ChangeMe!2026"


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def clean_academic():
    async with SessionLocal() as db:
        # Tartib FK ga e'tibor — bolalardan boshlab
        await db.execute(delete(CurriculumSubject))
        await db.execute(delete(Curriculum))
        await db.execute(delete(SubjectPrerequisite))
        await db.execute(delete(Subject))
        await db.execute(delete(Specialty))
        await db.execute(delete(Department))
        await db.execute(delete(Faculty))
        await db.execute(delete(AcademicCalendar))
        await db.execute(delete(Organization))
        await db.execute(delete(UserSession))
        await db.execute(delete(LoginAttempt))
        await db.execute(
            text(
                "DELETE FROM user_roles WHERE user_id IN "
                "(SELECT id FROM users WHERE email LIKE '%@example.com')"
            )
        )
        await db.execute(
            text(
                "DELETE FROM profiles WHERE user_id IN "
                "(SELECT id FROM users WHERE email LIKE '%@example.com')"
            )
        )
        await db.execute(text("DELETE FROM users WHERE email LIKE '%@example.com'"))
        await db.commit()
    yield


def _email() -> str:
    return f"u_{uuid.uuid4().hex[:10]}@example.com"


async def _admin(client: AsyncClient) -> str:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    return r.json()["access_token"]


async def _student(client: AsyncClient) -> str:
    email = _email()
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": VALID_PASSWORD, "full_name": "Talaba Test"},
    )
    r = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": VALID_PASSWORD}
    )
    return r.json()["access_token"]


async def _build_chain(client: AsyncClient, token: str) -> dict[str, int]:
    """Org → Faculty → Department zanjirini yaratadi va id'larni qaytaradi."""
    h = {"Authorization": f"Bearer {token}"}
    org = (
        await client.post(
            "/api/v1/organizations",
            json={"code": "XIU", "name": "Xalqaro Innovatsiya Universiteti", "type": "private"},
            headers=h,
        )
    ).json()
    fac = (
        await client.post(
            "/api/v1/faculties",
            json={"organization_id": org["id"], "code": "IT", "name": "AT fakulteti"},
            headers=h,
        )
    ).json()
    dep = (
        await client.post(
            "/api/v1/departments",
            json={"faculty_id": fac["id"], "code": "SE", "name": "Dasturiy injiniring"},
            headers=h,
        )
    ).json()
    return {"org_id": org["id"], "faculty_id": fac["id"], "department_id": dep["id"]}


# ----------------------------------------------------------------------------
# RBAC enforcement
# ----------------------------------------------------------------------------


async def test_student_cannot_create_organization(client: AsyncClient) -> None:
    token = await _student(client)
    r = await client.post(
        "/api/v1/organizations",
        json={"code": "X", "name": "Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


async def test_student_cannot_create_faculty(client: AsyncClient) -> None:
    student_token = await _student(client)
    admin_token = await _admin(client)
    chain = await _build_chain(client, admin_token)
    r = await client.post(
        "/api/v1/faculties",
        json={"organization_id": chain["org_id"], "code": "X", "name": "X"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert r.status_code == 403


async def test_student_can_read_subjects(client: AsyncClient) -> None:
    """Talabaga subject.read berilgan."""
    token = await _student(client)
    r = await client.get(
        "/api/v1/subjects", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200


# ----------------------------------------------------------------------------
# Organization → Faculty → Department CRUD
# ----------------------------------------------------------------------------


async def test_org_create_and_get(client: AsyncClient) -> None:
    token = await _admin(client)
    h = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        "/api/v1/organizations",
        json={"code": "TEST", "name": "Test Univ", "type": "private", "domain": "test.uz"},
        headers=h,
    )
    assert r.status_code == 201
    org_id = r.json()["id"]
    g = await client.get(f"/api/v1/organizations/{org_id}", headers=h)
    assert g.status_code == 200
    assert g.json()["code"] == "TEST"


async def test_faculty_uniqueness_per_org(client: AsyncClient) -> None:
    token = await _admin(client)
    h = {"Authorization": f"Bearer {token}"}
    chain = await _build_chain(client, token)
    # Bir xil OTM + kod = 409
    r = await client.post(
        "/api/v1/faculties",
        json={"organization_id": chain["org_id"], "code": "IT", "name": "Dup"},
        headers=h,
    )
    assert r.status_code == 409


async def test_department_filter_by_faculty(client: AsyncClient) -> None:
    token = await _admin(client)
    h = {"Authorization": f"Bearer {token}"}
    chain = await _build_chain(client, token)
    r = await client.get(
        f"/api/v1/departments?faculty_id={chain['faculty_id']}", headers=h
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["faculty_id"] == chain["faculty_id"]


# ----------------------------------------------------------------------------
# Specialty (559-qaror 14, 15-bandlar)
# ----------------------------------------------------------------------------


async def test_specialty_bachelor_quota_max_300(client: AsyncClient) -> None:
    token = await _admin(client)
    h = {"Authorization": f"Bearer {token}"}
    chain = await _build_chain(client, token)

    r = await client.post(
        "/api/v1/specialties",
        json={
            "department_id": chain["department_id"],
            "code": "60611100",
            "name": "Test bakalavr",
            "level": "bachelor",
            "duration_years": 4,
            "education_form": "distance",
            "language": "uz-lat",
            "annual_quota": 350,
        },
        headers=h,
    )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert any("300" in d.get("msg", "") for d in detail)


async def test_specialty_master_quota_max_30(client: AsyncClient) -> None:
    token = await _admin(client)
    h = {"Authorization": f"Bearer {token}"}
    chain = await _build_chain(client, token)

    r = await client.post(
        "/api/v1/specialties",
        json={
            "department_id": chain["department_id"],
            "code": "70611100",
            "name": "Test magistr",
            "level": "master",
            "duration_years": 2,
            "education_form": "distance",
            "language": "uz-lat",
            "annual_quota": 35,
        },
        headers=h,
    )
    assert r.status_code == 422
    assert any("30" in d.get("msg", "") for d in r.json()["detail"])


async def test_specialty_create_with_distance_enabled(client: AsyncClient) -> None:
    token = await _admin(client)
    h = {"Authorization": f"Bearer {token}"}
    chain = await _build_chain(client, token)

    r = await client.post(
        "/api/v1/specialties",
        json={
            "department_id": chain["department_id"],
            "code": "60611100",
            "name": "Dasturiy injiniring",
            "level": "bachelor",
            "duration_years": 4,
            "education_form": "distance",
            "language": "uz-lat",
            "distance_enabled": True,
            "annual_quota": 250,
        },
        headers=h,
    )
    assert r.status_code == 201
    assert r.json()["distance_enabled"] is True
    assert r.json()["annual_quota"] == 250


async def test_specialty_enable_distance_endpoint(client: AsyncClient) -> None:
    token = await _admin(client)
    h = {"Authorization": f"Bearer {token}"}
    chain = await _build_chain(client, token)

    sp = (
        await client.post(
            "/api/v1/specialties",
            json={
                "department_id": chain["department_id"],
                "code": "60611100",
                "name": "Test",
                "level": "bachelor",
                "duration_years": 4,
                "education_form": "fulltime",
                "language": "uz-lat",
            },
            headers=h,
        )
    ).json()
    assert sp["distance_enabled"] is False

    r = await client.post(
        f"/api/v1/specialties/{sp['id']}/enable-distance", headers=h
    )
    assert r.status_code == 200
    assert r.json()["distance_enabled"] is True


async def test_specialty_filter_distance_only(client: AsyncClient) -> None:
    token = await _admin(client)
    h = {"Authorization": f"Bearer {token}"}
    chain = await _build_chain(client, token)

    # Ikkita yo'nalish — biri distance, biri kunduzgi
    await client.post(
        "/api/v1/specialties",
        json={
            "department_id": chain["department_id"],
            "code": "60611100",
            "name": "Distance",
            "level": "bachelor",
            "duration_years": 4,
            "education_form": "distance",
            "language": "uz-lat",
            "distance_enabled": True,
        },
        headers=h,
    )
    await client.post(
        "/api/v1/specialties",
        json={
            "department_id": chain["department_id"],
            "code": "60611101",
            "name": "Fulltime",
            "level": "bachelor",
            "duration_years": 4,
            "education_form": "fulltime",
            "language": "uz-lat",
        },
        headers=h,
    )
    r = await client.get("/api/v1/specialties?distance_only=true", headers=h)
    assert r.status_code == 200
    items = r.json()["items"]
    assert all(s["distance_enabled"] for s in items)
    assert len(items) == 1


# ----------------------------------------------------------------------------
# Subject + prerequisites
# ----------------------------------------------------------------------------


async def test_subject_create_with_prerequisites(client: AsyncClient) -> None:
    token = await _admin(client)
    h = {"Authorization": f"Bearer {token}"}
    chain = await _build_chain(client, token)

    s1 = (
        await client.post(
            "/api/v1/subjects",
            json={
                "department_id": chain["department_id"],
                "code": "PROG-101",
                "name": "Dasturlash asoslari",
                "credits": 6,
            },
            headers=h,
        )
    ).json()
    s2 = (
        await client.post(
            "/api/v1/subjects",
            json={
                "department_id": chain["department_id"],
                "code": "PROG-201",
                "name": "OOP",
                "credits": 6,
                "prerequisite_ids": [s1["id"]],
            },
            headers=h,
        )
    ).json()
    assert s1["id"] in s2["prerequisite_ids"]


# ----------------------------------------------------------------------------
# Curriculum
# ----------------------------------------------------------------------------


async def test_curriculum_create_with_subjects(client: AsyncClient) -> None:
    token = await _admin(client)
    h = {"Authorization": f"Bearer {token}"}
    chain = await _build_chain(client, token)

    sp = (
        await client.post(
            "/api/v1/specialties",
            json={
                "department_id": chain["department_id"],
                "code": "60611100",
                "name": "SE",
                "level": "bachelor",
                "duration_years": 4,
                "education_form": "distance",
                "language": "uz-lat",
            },
            headers=h,
        )
    ).json()
    sub = (
        await client.post(
            "/api/v1/subjects",
            json={
                "department_id": chain["department_id"],
                "code": "PROG-101",
                "name": "Dasturlash",
                "credits": 6,
            },
            headers=h,
        )
    ).json()

    r = await client.post(
        "/api/v1/curricula",
        json={
            "specialty_id": sp["id"],
            "name": "SE 2026",
            "version": "2026-v1",
            "valid_from": "2026-09-01",
            "based_on": "DTS",
            "total_credits": 240,
            "subjects": [{"subject_id": sub["id"], "semester": 1}],
        },
        headers=h,
    )
    assert r.status_code == 201
    assert len(r.json()["subjects"]) == 1


async def test_curriculum_clone_creates_new_version(client: AsyncClient) -> None:
    token = await _admin(client)
    h = {"Authorization": f"Bearer {token}"}
    chain = await _build_chain(client, token)
    sp = (
        await client.post(
            "/api/v1/specialties",
            json={
                "department_id": chain["department_id"],
                "code": "60611100",
                "name": "SE",
                "level": "bachelor",
                "duration_years": 4,
                "education_form": "distance",
                "language": "uz-lat",
            },
            headers=h,
        )
    ).json()
    sub = (
        await client.post(
            "/api/v1/subjects",
            json={
                "department_id": chain["department_id"],
                "code": "PROG-101",
                "name": "Dasturlash",
                "credits": 6,
            },
            headers=h,
        )
    ).json()
    src = (
        await client.post(
            "/api/v1/curricula",
            json={
                "specialty_id": sp["id"],
                "name": "SE 2026",
                "version": "2026-v1",
                "valid_from": "2026-09-01",
                "total_credits": 240,
                "subjects": [{"subject_id": sub["id"], "semester": 1}],
            },
            headers=h,
        )
    ).json()

    r = await client.post(
        f"/api/v1/curricula/{src['id']}/clone",
        json={"new_version": "2027-v1", "new_valid_from": "2027-09-01"},
        headers=h,
    )
    assert r.status_code == 200
    cloned = r.json()
    assert cloned["id"] != src["id"]
    assert cloned["version"] == "2027-v1"
    assert len(cloned["subjects"]) == 1


async def test_curriculum_approve(client: AsyncClient) -> None:
    token = await _admin(client)
    h = {"Authorization": f"Bearer {token}"}
    chain = await _build_chain(client, token)
    sp = (
        await client.post(
            "/api/v1/specialties",
            json={
                "department_id": chain["department_id"],
                "code": "60611100",
                "name": "SE",
                "level": "bachelor",
                "duration_years": 4,
                "education_form": "distance",
                "language": "uz-lat",
            },
            headers=h,
        )
    ).json()
    c = (
        await client.post(
            "/api/v1/curricula",
            json={
                "specialty_id": sp["id"],
                "name": "SE",
                "version": "v1",
                "valid_from": "2026-09-01",
                "total_credits": 240,
            },
            headers=h,
        )
    ).json()
    r = await client.post(f"/api/v1/curricula/{c['id']}/approve", headers=h)
    assert r.status_code == 200
    assert r.json()["approved_by"] is not None
    assert r.json()["approved_at"] is not None


# ----------------------------------------------------------------------------
# Academic calendar
# ----------------------------------------------------------------------------


async def test_calendar_create_and_current(client: AsyncClient) -> None:
    token = await _admin(client)
    h = {"Authorization": f"Bearer {token}"}
    chain = await _build_chain(client, token)

    from datetime import date, timedelta

    today = date.today()
    cal = (
        await client.post(
            "/api/v1/academic-calendars",
            json={
                "organization_id": chain["org_id"],
                "academic_year": "2026-2027",
                "name": "2026-2027",
                "start_date": (today - timedelta(days=10)).isoformat(),
                "end_date": (today + timedelta(days=300)).isoformat(),
                "semesters": [
                    {
                        "name": "Kuzgi",
                        "start_date": (today - timedelta(days=10)).isoformat(),
                        "end_date": (today + timedelta(days=130)).isoformat(),
                    }
                ],
                "holidays": [],
            },
            headers=h,
        )
    ).json()
    assert cal["academic_year"] == "2026-2027"

    r = await client.get(
        f"/api/v1/academic-calendars/current?organization_id={chain['org_id']}",
        headers=h,
    )
    assert r.status_code == 200
    assert r.json() is not None
    assert r.json()["id"] == cal["id"]


async def test_calendar_unique_per_org_year(client: AsyncClient) -> None:
    token = await _admin(client)
    h = {"Authorization": f"Bearer {token}"}
    chain = await _build_chain(client, token)
    payload = {
        "organization_id": chain["org_id"],
        "academic_year": "2026-2027",
        "name": "Kuzgi",
        "start_date": "2026-09-01",
        "end_date": "2027-06-30",
    }
    r1 = await client.post("/api/v1/academic-calendars", json=payload, headers=h)
    r2 = await client.post("/api/v1/academic-calendars", json=payload, headers=h)
    assert r1.status_code == 201
    assert r2.status_code == 409
