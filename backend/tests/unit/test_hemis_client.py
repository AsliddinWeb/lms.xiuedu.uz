"""Phase 10c — HEMIS API client (mock mode) testlari.

Real HTTP'ga tegmaymiz, faqat `mode='mock'` bilan fixture'lar qaytarilishini tekshiramiz.
Integration testlar (real HTTP) alohida `tests/integration/test_hemis_real.py`-da
(skip default, faqat HEMIS_MODE=real bo'lganda).
"""

from __future__ import annotations

import pytest

from app.integrations.hemis.client import (
    HemisAuthError,
    HemisClient,
    HemisError,
)


# ==== Auth ====


@pytest.mark.asyncio
async def test_student_login_success():
    async with HemisClient(mode="mock") as c:
        r = await c.student_login("999211100073", "DD7777777")
    assert "token" in r
    assert "student" in r["token"]


@pytest.mark.asyncio
async def test_student_login_wrong_password():
    async with HemisClient(mode="mock") as c:
        with pytest.raises(HemisAuthError):
            await c.student_login("999211100073", "xx")  # < 6 belgi


@pytest.mark.asyncio
async def test_student_login_unknown_user():
    async with HemisClient(mode="mock") as c:
        with pytest.raises(HemisAuthError):
            await c.student_login("000000", "validpass")


@pytest.mark.asyncio
async def test_tutor_login_success():
    async with HemisClient(mode="mock") as c:
        r = await c.tutor_login("tutor1", "pwd123", "captcha-token")
    assert "token" in r
    assert "refresh_token" in r


@pytest.mark.asyncio
async def test_tutor_login_missing_recaptcha():
    async with HemisClient(mode="mock") as c:
        with pytest.raises(HemisError):
            await c.tutor_login("tutor1", "pwd123", "")


# ==== SSO ====


@pytest.mark.asyncio
async def test_sso_targets():
    async with HemisClient(mode="mock") as c:
        login = await c.student_login("999211100073", "DD7777777")
        targets = await c.sso_targets(login["token"])
    codes = [t["code"] for t in targets]
    assert "lms" in codes


@pytest.mark.asyncio
async def test_sso_redirect_url_for_lms():
    async with HemisClient(mode="mock") as c:
        login = await c.student_login("999211100073", "DD7777777")
        r = await c.sso_redirect_url(login["token"], "lms")
    assert "redirect_url" in r
    assert "sso_token=" in r["redirect_url"]
    assert r["target"] == "lms"
    assert r["expires_in"] > 0


@pytest.mark.asyncio
async def test_sso_redirect_url_unknown_target():
    async with HemisClient(mode="mock") as c:
        login = await c.student_login("999211100073", "DD7777777")
        with pytest.raises(HemisError):
            await c.sso_redirect_url(login["token"], "nonexistent")


# ==== Student API ====


@pytest.mark.asyncio
async def test_account_me_returns_full_profile():
    async with HemisClient(mode="mock") as c:
        login = await c.student_login("999211100073", "DD7777777")
        me = await c.account_me(login["token"])
    assert me["id"] == 999001
    assert me["student_id_number"] == "999211100073"
    assert me["passport_pin"] == "12345678901234"
    assert me["full_name"]
    assert me["group"]["id"] == 5001
    assert me["faculty"]["code"] == "ATM"
    assert me["semester"]["current"] is True


@pytest.mark.asyncio
async def test_account_me_rejects_invalid_token():
    async with HemisClient(mode="mock") as c:
        with pytest.raises(HemisAuthError):
            await c.account_me("invalid-token")


@pytest.mark.asyncio
async def test_subject_list():
    async with HemisClient(mode="mock") as c:
        login = await c.student_login("999211100073", "DD7777777")
        subjects = await c.subject_list(login["token"], semester=7)
    assert len(subjects) >= 1
    assert subjects[0]["curriculumSubject"]["subject"]["code"]


@pytest.mark.asyncio
async def test_schedule():
    async with HemisClient(mode="mock") as c:
        login = await c.student_login("999211100073", "DD7777777")
        schedule = await c.schedule(login["token"])
    assert isinstance(schedule, list)


@pytest.mark.asyncio
async def test_gpa_list():
    async with HemisClient(mode="mock") as c:
        login = await c.student_login("999211100073", "DD7777777")
        gpa = await c.gpa_list(login["token"])
    assert all("gpa" in g for g in gpa)


@pytest.mark.asyncio
async def test_attendance():
    async with HemisClient(mode="mock") as c:
        login = await c.student_login("999211100073", "DD7777777")
        att = await c.attendance(login["token"])
    assert isinstance(att, list)


@pytest.mark.asyncio
async def test_semesters():
    async with HemisClient(mode="mock") as c:
        login = await c.student_login("999211100073", "DD7777777")
        sems = await c.semesters(login["token"])
    assert any(s["current"] for s in sems)


# ==== Backend API (admin) ====


@pytest.mark.asyncio
async def test_student_list_paginated():
    async with HemisClient(mode="mock") as c:
        r = await c.student_list(page=1, limit=10)
    assert "items" in r
    assert "pagination" in r


@pytest.mark.asyncio
async def test_employee_list():
    async with HemisClient(mode="mock") as c:
        r = await c.employee_list()
    assert len(r["items"]) >= 1
    emp = r["items"][0]
    assert emp["staffPosition"]["code"]
    assert emp["department"]["code"] == "ATM"


@pytest.mark.asyncio
async def test_department_list():
    async with HemisClient(mode="mock") as c:
        deps = await c.department_list()
    assert any(d["code"] == "ATM" for d in deps)


@pytest.mark.asyncio
async def test_group_list():
    async with HemisClient(mode="mock") as c:
        groups = await c.group_list()
    assert any(g["name"] == "ATM-21-1" for g in groups)


@pytest.mark.asyncio
async def test_curriculum_list():
    async with HemisClient(mode="mock") as c:
        curs = await c.curriculum_list()
    assert len(curs) >= 1


# ==== Tutor API ====


@pytest.mark.asyncio
async def test_tutor_profile():
    async with HemisClient(mode="mock") as c:
        login = await c.tutor_login("tutor1", "pwd123", "captcha")
        prof = await c.tutor_profile(login["token"])
    assert prof["name"]
    assert prof["department"]["code"]


@pytest.mark.asyncio
async def test_tutor_groups():
    async with HemisClient(mode="mock") as c:
        login = await c.tutor_login("tutor1", "pwd123", "captcha")
        groups = await c.tutor_groups(login["token"])
    assert len(groups) >= 1
    assert "studentsCount" in groups[0]


@pytest.mark.asyncio
async def test_tutor_group_students():
    async with HemisClient(mode="mock") as c:
        login = await c.tutor_login("tutor1", "pwd123", "captcha")
        students = await c.tutor_group_students(login["token"], group_id=5001)
    assert len(students) >= 1
    assert all("full_name" in s for s in students)


# ==== Phase 10g — Tutor expansion endpoints ====


@pytest.mark.asyncio
async def test_tutor_grade_gpa():
    async with HemisClient(mode="mock") as c:
        login = await c.tutor_login("tutor1", "pwd", "captcha")
        gpa = await c.tutor_grade_gpa(login["token"], group_id=5001)
    assert len(gpa) >= 1
    assert all("gpa" in g and "rank" in g for g in gpa)
    ranks = [g["rank"] for g in gpa]
    assert ranks == sorted(ranks)


@pytest.mark.asyncio
async def test_tutor_grade_gpa_rejects_student_token():
    async with HemisClient(mode="mock") as c:
        student_login = await c.student_login("999211100073", "DD7777777")
        with pytest.raises(HemisAuthError):
            await c.tutor_grade_gpa(student_login["token"], group_id=5001)


@pytest.mark.asyncio
async def test_tutor_attendance_by_subject():
    async with HemisClient(mode="mock") as c:
        login = await c.tutor_login("tutor1", "pwd", "captcha")
        att = await c.tutor_attendance_by_subject(login["token"], group_id=5001)
    assert len(att) >= 1
    assert all("attendance_percent" in a for a in att)


@pytest.mark.asyncio
async def test_tutor_grade_debtors():
    async with HemisClient(mode="mock") as c:
        login = await c.tutor_login("tutor1", "pwd", "captcha")
        debtors = await c.tutor_grade_debtors(login["token"], group_id=5001)
    assert isinstance(debtors, list)
    if debtors:
        assert "debt_count" in debtors[0]


# ==== Legacy aliases ====


@pytest.mark.asyncio
async def test_legacy_login_alias():
    async with HemisClient(mode="mock") as c:
        r = await c.login("999211100073", "DD7777777")
    assert "token" in r


@pytest.mark.asyncio
async def test_legacy_get_me_alias():
    async with HemisClient(mode="mock") as c:
        login = await c.student_login("999211100073", "DD7777777")
        me = await c.get_me(login["token"])
    assert me["id"] == 999001


# ==== Phase 10e — SSO callback flow ====


@pytest.mark.asyncio
async def test_sso_token_validates_via_account_me():
    """SSO token bilan account_me chaqirib bo'lishi kerak — bu validation mexanizmi."""
    async with HemisClient(mode="mock") as c:
        login = await c.student_login("999211100073", "DD7777777")
        sso = await c.sso_redirect_url(login["token"], "lms")
    # sso_token redirect_url query'da
    from urllib.parse import parse_qs, urlparse

    qs = parse_qs(urlparse(sso["redirect_url"]).query)
    sso_token = qs["sso_token"][0]
    assert sso_token.startswith("mock.sso.lms.")

    # Endi sso_token bilan account_me chaqiramiz — validation muvaffaqiyatli bo'lishi kerak
    async with HemisClient(mode="mock") as c:
        me = await c.account_me(sso_token)
    assert me["id"] == 999001


@pytest.mark.asyncio
async def test_sso_token_for_non_lms_target_does_not_validate():
    """SSO token boshqa target ('career') uchun bo'lsa bizning LMS uni rad qilmasligi kerak —
    HEMIS validation mexanizmi target-aware emas, faqat student token deb tan oladi.
    """
    async with HemisClient(mode="mock") as c:
        login = await c.student_login("999211100073", "DD7777777")
        sso = await c.sso_redirect_url(login["token"], "career")
    from urllib.parse import parse_qs, urlparse

    qs = parse_qs(urlparse(sso["redirect_url"]).query)
    career_token = qs["sso_token"][0]
    # `career` prefiksli sso_token mock'da "sso.lms" emas — rad qilinadi
    assert "sso.career" in career_token
    async with HemisClient(mode="mock") as c:
        with pytest.raises(HemisAuthError):
            await c.account_me(career_token)
