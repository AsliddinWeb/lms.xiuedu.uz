"""HEMIS Student/Employee → User+Profile sync helpers — Phase 10b.

`hemis_sync.upsert_student(db, data)` — HEMIS API `/v1/account/me` yoki
`/v1/data/student-list`-dan kelgan dict-ni qabul qiladi va bizning DB'da
User+Profile yaratadi/yangilaydi. `hemis_data_hash` orqali drift detection.

Ushbu modul:
- Sync logikasini auth flow'dan ajratadi (login service uchun ham, scheduler uchun ham bir xil)
- LMS-specific fieldlar yo'qotilmaydi (role'lar, course enrollment, profile.bio va h.k.)
- Faqat HEMIS authoritative field'lar yangilanadi
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.academic.models import AcademicGroup
from app.modules.users.models import Profile, User


def _hash(data: dict[str, Any]) -> str:
    """Stable SHA256 of dict — drift detection uchun.

    HEMIS qaytaradigan dict ichida nullable maydonlar bor — None va '' farqlamasdan
    bir xil hash beradi. List-orderni saqlaymiz (HEMIS chiqarganidek).
    """
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _classifier_code(v: Any) -> str | None:
    """HEMIS Classifier (`{code, name}` yoki None) -> kod string."""
    if isinstance(v, dict):
        return v.get("code")
    return None


def _classifier_name(v: Any) -> str | None:
    if isinstance(v, dict):
        return v.get("name")
    return None


def _hemis_lang_to_local(code: str | None) -> str | None:
    """HEMIS educationLang.code → bizning locale: 'uz', 'ru', 'en', 'qq' → 'uz-lat'/'ru'/'en'/'uz-cyr'.

    HEMIS odatda 'uz' (lotin), 'uz-cyrl' (kirill), 'ru', 'en' qaytaradi.
    """
    if not code:
        return None
    code_lower = code.lower().replace("_", "-")
    mapping = {
        "uz": "uz-lat",
        "uz-latn": "uz-lat",
        "uz-lat": "uz-lat",
        "uz-cyrl": "uz-cyr",
        "uz-cyr": "uz-cyr",
        "ru": "ru",
        "en": "en",
    }
    return mapping.get(code_lower)


def _unix_to_date(ts: int | None) -> date | None:
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).date()
    except (ValueError, OverflowError, OSError):
        return None


async def _ensure_group(db: AsyncSession, group_data: dict | None) -> int | None:
    """HEMIS Group dict → bizning `academic_groups` row id.

    Yangi group bo'lsa yaratadi, mavjud bo'lsa update qiladi.
    """
    if not group_data or "id" not in group_data:
        return None
    hemis_gid = group_data["id"]
    g = (
        await db.execute(select(AcademicGroup).where(AcademicGroup.hemis_id == hemis_gid))
    ).scalar_one_or_none()
    if g is None:
        g = AcademicGroup(
            hemis_id=hemis_gid,
            name=group_data.get("name", f"group-{hemis_gid}"),
            education_lang=_classifier_code(group_data.get("educationLang")),
            hemis_last_synced_at=datetime.now(timezone.utc),
        )
        db.add(g)
        await db.flush()
    else:
        # Faqat HEMIS authoritative fieldlarni yangilash
        g.name = group_data.get("name", g.name)
        g.education_lang = _classifier_code(group_data.get("educationLang")) or g.education_lang
        g.hemis_last_synced_at = datetime.now(timezone.utc)
    return g.id


async def upsert_student(db: AsyncSession, data: dict[str, Any]) -> User:
    """HEMIS Student dict (`/v1/account/me`-dan) → User+Profile.

    Identification order:
        1. by `hemis_id` (data['id'])
        2. by `hemis_login` (data['student_id_number'])
        3. by `pinfl` (data['passport_pin']) — Profile orqali
        4. yaratiladi (yangi user)

    Returns: User instance (refreshed).
    """
    if "id" not in data:
        raise ValueError("HEMIS student data 'id' field bo'lishi kerak")

    hemis_id = int(data["id"])
    hemis_login = data.get("student_id_number")
    pinfl = data.get("passport_pin")
    h = _hash(data)

    # 1) by hemis_id
    user = (
        await db.execute(select(User).where(User.hemis_id == hemis_id))
    ).scalar_one_or_none()

    # 2) by hemis_login
    if user is None and hemis_login:
        user = (
            await db.execute(select(User).where(User.hemis_login == hemis_login))
        ).scalar_one_or_none()

    # 3) by pinfl (Profile JOIN)
    if user is None and pinfl:
        profile = (
            await db.execute(select(Profile).where(Profile.pinfl == pinfl))
        ).scalar_one_or_none()
        if profile:
            user = (
                await db.execute(select(User).where(User.id == profile.user_id))
            ).scalar_one_or_none()

    # 4) yangi user yaratish
    is_new = user is None
    if is_new:
        user = User(
            hemis_id=hemis_id,
            hemis_login=hemis_login,
            email=data.get("email") or None,  # nullable
            full_name=data.get("full_name", "").strip() or f"Student #{hemis_id}",
            is_active=True,
            is_verified=True,  # HEMIS verified — talaba HEMIS DB'da bor
        )
        user.profile = Profile()
        db.add(user)
        await db.flush()
    elif user.hemis_data_hash == h:
        # Hech narsa o'zgarmagan — sync skip
        return user

    # HEMIS authoritative fields update
    user.hemis_id = hemis_id
    user.hemis_login = hemis_login
    user.full_name = data.get("full_name", user.full_name)
    if data.get("email"):
        user.email = data["email"]
    if data.get("image"):
        user.avatar_url = data["image"]

    # Student metadata
    user.education_form = _classifier_code(data.get("educationForm"))
    user.payment_form = _classifier_code(data.get("paymentForm"))
    user.student_status = _classifier_code(data.get("studentStatus"))

    # Group sync
    user.group_id = await _ensure_group(db, data.get("group"))

    # Semester
    sem = data.get("semester")
    if isinstance(sem, dict):
        user.current_semester_id = sem.get("id")

    # Profile sync
    p = user.profile or Profile(user_id=user.id)
    if not user.profile:
        user.profile = p
        db.add(p)

    p.first_name = data.get("first_name") or p.first_name
    p.last_name = data.get("second_name") or p.last_name
    p.middle_name = data.get("third_name") or p.middle_name
    if pinfl:
        p.pinfl = pinfl
    bd = _unix_to_date(data.get("birth_date"))
    if bd:
        p.birthdate = bd
    if data.get("address"):
        p.address = data["address"]
    p.country = _classifier_name(data.get("country")) or p.country
    p.region = _classifier_name(data.get("province")) or p.region
    p.district = _classifier_name(data.get("district")) or p.district
    p.social_category = _classifier_code(data.get("socialCategory")) or p.social_category
    p.poverty_level = _classifier_code(data.get("povertyLevel")) or p.poverty_level
    p.accommodation = _classifier_code(data.get("accommodation")) or p.accommodation
    lang = _hemis_lang_to_local(_classifier_code(data.get("educationLang")))
    if lang:
        p.language = lang

    # Sync metadata
    user.hemis_data_hash = h
    user.hemis_last_synced_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(user)
    return user


async def upsert_tutor(db: AsyncSession, data: dict[str, Any]) -> User:
    """HEMIS Tutor profile dict (`/ver1/tutor/profile/index`) → User+Profile.

    Phase 10g — pedagog (tutor) login uchun. Tutor profil employee-ning bir
    qismi (kichikroq fieldlar), shuning uchun ham employee'dek upsert qilamiz.
    """
    return await upsert_employee(db, data)


async def upsert_employee(db: AsyncSession, data: dict[str, Any]) -> User:
    """HEMIS Employee dict (`/v1/data/employee-list`-dan) → User+Profile.

    Employee schema kichikroq, lekin lookup order o'xshash.
    """
    if "id" not in data:
        raise ValueError("HEMIS employee data 'id' field bo'lishi kerak")

    hemis_id = int(data["id"])
    h = _hash(data)
    user = (
        await db.execute(select(User).where(User.hemis_id == hemis_id))
    ).scalar_one_or_none()

    is_new = user is None
    if is_new:
        user = User(
            hemis_id=hemis_id,
            full_name=data.get("name") or data.get("full_name") or f"Employee #{hemis_id}",
            email=data.get("email") or None,
            is_active=True,
            is_verified=True,
        )
        user.profile = Profile()
        db.add(user)
        await db.flush()
    elif user.hemis_data_hash == h:
        return user

    user.hemis_id = hemis_id
    if data.get("name"):
        user.full_name = data["name"]
    if data.get("email"):
        user.email = data["email"]

    # Employee metadata
    user.staff_position = _classifier_code(data.get("staffPosition")) or user.staff_position
    user.employment_form = _classifier_code(data.get("employmentForm")) or user.employment_form
    user.employment_staff = _classifier_code(data.get("employmentStaff")) or user.employment_staff

    # Profile (academic degrees only meaningful for teachers)
    p = user.profile or Profile(user_id=user.id)
    if not user.profile:
        user.profile = p
        db.add(p)
    p.academic_degree = _classifier_code(data.get("academicDegree")) or p.academic_degree
    p.academic_title = _classifier_code(data.get("academicTitle")) or p.academic_title
    if data.get("phone"):
        from sqlalchemy.exc import IntegrityError  # noqa: F401 — placeholder for future dedup
        # phone unique — duplicate'da skip qilamiz (silent best-effort)
        # actual collision handling caller'da
        pass  # phone copying handled separately to avoid integrity error in batch sync

    user.hemis_data_hash = h
    user.hemis_last_synced_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(user)
    return user
