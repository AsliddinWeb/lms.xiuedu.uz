"""Seed script — default rollar, permission'lar va super admin.

Foydalanish:
  docker compose exec backend python -m app.db.seed
  docker compose exec backend python -m app.db.seed --admin-email admin@xiuedu.uz --admin-password ChangeMe!1
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.core.tenant import ensure_xiu_org
from app.db import models as _models  # noqa: F401  # Hamma modellarni ro'yxatga olish
from app.modules.rbac.models import Permission, Role, UserRole
from app.modules.users.models import Profile, User

# ---------------------------------------------------------------------------
# Permission katalogi (kategoriya → ro'yxat). Wildcard'lar bilan keng amal qiladi.
# ---------------------------------------------------------------------------

PERMISSIONS: list[tuple[str, str, str]] = [
    # (code, name, category)
    # Platform-level
    ("platform.*", "Platforma — universal", "platform"),
    # Org / Tenant
    ("org.read", "OTM ko'rish", "organization"),
    ("org.manage", "OTM boshqarish", "organization"),
    ("org.users.manage", "OTM foydalanuvchilarini boshqarish", "organization"),
    # Faculty
    ("faculty.read", "Fakultet ko'rish", "academic"),
    ("faculty.manage", "Fakultet boshqarish", "academic"),
    ("faculty.students.manage", "Fakultet talabalari", "academic"),
    ("faculty.curriculum.manage", "Fakultet o'quv reja", "academic"),
    ("faculty.reports.view", "Fakultet hisobotlari", "academic"),
    # Department
    ("department.read", "Kafedra ko'rish", "academic"),
    ("department.manage", "Kafedra boshqarish (CRUD)", "academic"),
    ("department.teachers.manage", "Kafedra o'qituvchilari", "academic"),
    ("department.subjects.manage", "Kafedra fanlari", "academic"),
    # Specialty + Curriculum + Calendar (Phase 2a)
    ("specialty.read", "Yo'nalish ko'rish", "academic"),
    ("specialty.manage", "Yo'nalish boshqarish", "academic"),
    ("subject.read", "Fan ko'rish", "academic"),
    ("subject.manage", "Fan boshqarish (CRUD)", "academic"),
    ("curriculum.read", "O'quv reja ko'rish", "academic"),
    ("curriculum.manage", "O'quv reja boshqarish", "academic"),
    ("calendar.read", "Akademik kalendar ko'rish", "academic"),
    ("calendar.manage", "Akademik kalendar boshqarish", "academic"),
    # Course / Lesson (Phase 3b — Courses MVP)
    ("course.read", "Kurs ko'rish", "course"),
    ("course.create", "Kurs yaratish", "course"),
    ("course.edit", "Kurs tahrirlash", "course"),
    ("course.publish", "Kursni publish/archive qilish", "course"),
    ("course.content.create", "Kurs kontenti yaratish", "course"),
    ("enrollment.read", "Kurs talabalarini ko'rish", "course"),
    ("enrollment.manage", "Talabalarni kursga qo'shish/o'chirish", "course"),
    ("enrollment.self", "Kursga o'zi yozilish (self-enrollment)", "course"),
    ("progress.write", "O'z lesson progressini saqlash", "course"),
    ("progress.read.all", "Talabalar progressini ko'rish (o'qituvchi)", "course"),
    # Content (Phase 3a) — qayta foydalaniluvchi o'quv kontenti
    ("content.read", "Kontent ko'rish", "content"),
    ("content.create", "Kontent yaratish/tahrirlash", "content"),
    ("content.publish", "Kontentni publish/archive qilish", "content"),
    # Assignment (Phase 4a + 4b)
    ("assignment.read", "Topshiriqlarni ko'rish", "assignment"),
    ("assignment.manage", "Topshiriq yaratish/tahrirlash/publish", "assignment"),
    ("assignment.submit", "Topshiriq topshirish", "assignment"),
    ("assignment.grade", "Topshiriq baholash", "assignment"),
    ("rubric.read", "Rubric ko'rish", "assignment"),
    ("rubric.manage", "Rubric yaratish/tahrirlash", "assignment"),
    # Phase 4e: peer review + appeals
    ("peer.review", "Peer review qilish (talaba)", "assignment"),
    ("appeal.create", "Bahoga apellyatsiya berish (talaba)", "assignment"),
    ("appeal.review", "Apellyatsiyalarga javob berish (pedagog)", "assignment"),
    # Exam
    ("exam.create", "Imtihon yaratish", "exam"),
    ("exam.attempt", "Imtihon topshirish", "exam"),
    ("exam.proctor", "Imtihon proktoring", "exam"),
    # Live (Phase 5a)
    ("live.read", "Live sessiyalar ro'yxatini ko'rish", "live"),
    ("live.host", "Live dars o'tkazish (yaratish, boshlash, tugatish)", "live"),
    ("live.join", "Live darsga kirish (talaba)", "live"),
    # Profile / Payment
    ("profile.edit", "Profil tahrirlash", "profile"),
    ("payment.view", "To'lov ko'rish", "payment"),
    ("payment.manage", "To'lov boshqarish", "payment"),
    # Reports / Audit / Monitoring
    ("reports.view", "Hisobotlar", "reports"),
    ("reports.read.*", "Hisobotlar (read all)", "reports"),
    ("monitoring.read.*", "Monitoring (read all)", "monitoring"),
    ("audit.read.*", "Audit log (read all)", "audit"),
    # Tickets / Support
    ("tickets.manage", "Tiketlar boshqarish", "support"),
    ("users.read", "Foydalanuvchilar ro'yxati", "users"),
    ("users.manage", "Foydalanuvchilarni boshqarish", "users"),
    ("password.reset.request", "Parol tiklash so'rovi", "users"),
]


# ---------------------------------------------------------------------------
# Rollar (10 ta) — docs/01-overview/04-roles.md ga muvofiq
# ---------------------------------------------------------------------------

ROLES: list[dict] = [
    {
        "code": "super_admin",
        "name": "Super Administrator",
        "description": "Butun platformani boshqaradi (multi-tenant darajasida)",
        "permissions": ["platform.*"],
    },
    {
        "code": "otm_admin",
        "name": "OTM Administratori",
        "description": "Bitta OTM doirasidagi barcha jarayonlar",
        "permissions": [
            "org.read", "org.manage", "org.users.manage",
            "users.read", "users.manage",
            "faculty.manage", "faculty.read",
            "department.read", "department.manage", "department.teachers.manage",
            "specialty.read", "specialty.manage",
            "subject.read", "subject.manage",
            "curriculum.read", "curriculum.manage",
            "calendar.read", "calendar.manage",
            "course.read", "course.create", "course.edit", "course.publish",
            "enrollment.read", "enrollment.manage", "progress.read.all",
            "content.read", "content.create", "content.publish",
            "assignment.read", "assignment.manage", "assignment.grade",
            "rubric.read", "rubric.manage", "appeal.review",
            "live.read", "live.host",
            "reports.view", "audit.read.*",
            "payment.manage",
        ],
    },
    {
        "code": "dean",
        "name": "Dekan",
        "description": "Fakultet darajasidagi ta'lim jarayoni",
        "permissions": [
            "faculty.read", "faculty.students.manage",
            "faculty.curriculum.manage", "faculty.reports.view",
            "department.read", "department.manage",
            "specialty.read", "specialty.manage",
            "subject.read", "curriculum.read", "calendar.read",
            "course.read", "enrollment.read", "progress.read.all",
            "content.read", "content.publish",
            "assignment.read",
            "rubric.read", "appeal.review",
            "live.read",
            "users.read",
        ],
    },
    {
        "code": "department_head",
        "name": "Kafedra mudiri",
        "description": "Kafedra darajasidagi pedagoglar va fanlar",
        "permissions": [
            "department.read", "department.teachers.manage", "department.subjects.manage",
            "subject.read", "subject.manage",
            "curriculum.read", "curriculum.manage",
            "calendar.read",
            "course.read", "course.create", "course.edit", "course.publish",
            "enrollment.read", "enrollment.manage", "progress.read.all",
            "content.read", "content.create", "content.publish",
            "assignment.read", "assignment.manage", "assignment.grade",
            "rubric.read", "rubric.manage", "appeal.review",
            "live.read", "live.host",
        ],
    },
    {
        "code": "teacher",
        "name": "Pedagog",
        "description": "Kontent yaratish, dars o'tish, baholash",
        "permissions": [
            "subject.read", "curriculum.read", "calendar.read",
            "course.read", "course.create", "course.edit", "course.publish",
            "course.content.create",
            "enrollment.read", "enrollment.manage", "progress.read.all",
            "content.read", "content.create", "content.publish",
            "assignment.read", "assignment.manage", "assignment.grade",
            "rubric.read", "rubric.manage", "appeal.review",
            "exam.create", "live.read", "live.host",
            "profile.edit",
        ],
    },
    {
        "code": "student",
        "name": "Talaba",
        "description": "Kursni o'rganish, vazifalarni topshirish",
        "permissions": [
            "subject.read", "curriculum.read", "calendar.read",
            "course.read", "enrollment.self", "progress.write",
            "content.read",
            "assignment.read", "assignment.submit",
            "rubric.read", "peer.review", "appeal.create",
            "exam.attempt",
            "live.read", "live.join",
            "profile.edit", "payment.view",
        ],
    },
    {
        "code": "external_teacher",
        "name": "Xorijiy pedagog",
        "description": "Masofadan dars o'tuvchi mehmon o'qituvchi",
        "permissions": [
            "course.read", "course.edit", "course.content.create",
            "enrollment.read", "progress.read.all",
            "content.read", "content.create",
            "live.read", "live.host",
            "profile.edit",
        ],
    },
    {
        "code": "tsdin_inspector",
        "name": "TSDIN nazoratchisi",
        "description": "Tashqi monitoring (faqat o'qish)",
        "permissions": ["monitoring.read.*", "audit.read.*", "reports.read.*"],
    },
    {
        "code": "support",
        "name": "Texnik qo'llab-quvvatlash",
        "description": "Foydalanuvchilarga yordam",
        "permissions": ["users.read", "tickets.manage", "password.reset.request"],
    },
    {
        "code": "guest",
        "name": "Mehmon (Auditor)",
        "description": "Demo materiallarni ko'rish",
        "permissions": [],
    },
]


# ---------------------------------------------------------------------------
# Seed funksiyalari
# ---------------------------------------------------------------------------


async def seed_permissions(db: AsyncSession) -> dict[str, Permission]:
    existing = {p.code: p for p in (await db.execute(select(Permission))).scalars().all()}
    for code, name, category in PERMISSIONS:
        if code in existing:
            continue
        p = Permission(code=code, name=name, category=category)
        db.add(p)
        existing[code] = p
    await db.flush()
    return existing


async def seed_roles(db: AsyncSession, perms: dict[str, Permission]) -> dict[str, Role]:
    result = await db.execute(select(Role).options(selectinload(Role.permissions)))
    existing = {r.code: r for r in result.scalars().all()}

    for spec in ROLES:
        role = existing.get(spec["code"])
        target = [perms[p] for p in spec["permissions"] if p in perms]
        if role is None:
            role = Role(
                code=spec["code"],
                name=spec["name"],
                description=spec["description"],
                is_system=True,
                permissions=target,  # eager init — lazy load yo'q
            )
            db.add(role)
            await db.flush()
            existing[spec["code"]] = role
        else:
            current = set(role.permissions)
            if set(target) != current:
                role.permissions = target

    await db.flush()
    return existing


async def seed_super_admin(
    db: AsyncSession,
    roles: dict[str, Role],
    *,
    email: str,
    password: str,
    full_name: str,
) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            is_active=True,
            is_verified=True,
        )
        user.profile = Profile()
        db.add(user)
        await db.flush()

    # Super admin rolini biriktirish (agar yo'q bo'lsa)
    super_role = roles["super_admin"]
    existing_role = await db.execute(
        select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == super_role.id)
    )
    if existing_role.scalar_one_or_none() is None:
        db.add(UserRole(user_id=user.id, role_id=super_role.id, scope_type="global"))
        await db.flush()

    return user


# ---------------------------------------------------------------------------
# Demo akkauntlar (sinab ko'rish uchun)
# ---------------------------------------------------------------------------

DEMO_USERS: list[dict] = [
    {
        "email": "student@xiuedu.uz",
        "password": "Student!2026",
        "full_name": "Demo Talaba",
        "role": "student",
        "is_verified": True,
    },
    {
        "email": "teacher@xiuedu.uz",
        "password": "Teacher!2026",
        "full_name": "Demo Pedagog",
        "role": "teacher",
        "is_verified": True,
    },
    {
        "email": "dean@xiuedu.uz",
        "password": "Dean!2026",
        "full_name": "Demo Dekan",
        "role": "dean",
        "is_verified": True,
    },
    # Eslatma: `otm-admin@xiuedu.uz` olib tashlandi — single-tenant XIU only.
    # `super_admin` (`admin@xiuedu.uz`) shu vazifani bajaradi.
]


async def seed_demo_users(
    db: AsyncSession, roles: dict[str, Role]
) -> list[tuple[str, str, str]]:
    """Demo akkauntlarni yaratadi. Mavjud bo'lsa o'tkazib yuboradi.

    Returns list of (email, password, role_code) — sessiyadan tashqari print qilish uchun.
    """
    created: list[tuple[str, str, str]] = []
    for spec in DEMO_USERS:
        existing = await db.execute(select(User).where(User.email == spec["email"]))
        user = existing.scalar_one_or_none()
        if user is None:
            user = User(
                email=spec["email"],
                password_hash=hash_password(spec["password"]),
                full_name=spec["full_name"],
                is_active=True,
                is_verified=spec["is_verified"],
            )
            user.profile = Profile()
            db.add(user)
            await db.flush()

        role = roles.get(spec["role"])
        if role is not None:
            ur_check = await db.execute(
                select(UserRole).where(
                    UserRole.user_id == user.id,
                    UserRole.role_id == role.id,
                    UserRole.scope_type == "global",
                )
            )
            if ur_check.scalar_one_or_none() is None:
                db.add(
                    UserRole(user_id=user.id, role_id=role.id, scope_type="global")
                )
                await db.flush()

        created.append((spec["email"], spec["password"], spec["role"]))
    return created


async def main(args: argparse.Namespace) -> None:
    async with SessionLocal() as db:
        # Single-tenant XIU organization (idempotent)
        xiu = await ensure_xiu_org(db)
        perms = await seed_permissions(db)
        roles = await seed_roles(db, perms)
        admin = await seed_super_admin(
            db,
            roles,
            email=args.admin_email,
            password=args.admin_password,
            full_name=args.admin_name,
        )
        demos = await seed_demo_users(db, roles)

        # Backfill: barcha mavjud demo va admin akkountlarni XIU'ga link
        from sqlalchemy import update
        await db.execute(
            update(User).where(User.tenant_id.is_(None)).values(tenant_id=xiu.id)
        )

        # Phase 11e — dastlabki badge katalogi
        from app.modules.gamification.seed import seed_badges
        badges_added = await seed_badges(db)

        await db.commit()

    print(f"✓ {badges_added} badge qo'shildi (mavjudlari saqlangan)")

    print(f"✓ XIU organization: id={xiu.id} (code={xiu.code})")
    print(f"✓ {len(perms)} permission, {len(roles)} role")
    print()
    print(f"✓ Super admin (lms-admin.xiuedu.uz):")
    print(f"  email:  {admin.email}")
    print(f"  parol:  {args.admin_password}")
    print()
    print(f"✓ Demo akkauntlar (lms.xiuedu.uz) — {len(demos)} ta:")
    for email, password, role_code in demos:
        print(f"  {email:30s}  parol: {password:18s}  rol: {role_code}")
    print()
    print("Login:")
    print(
        f"  curl -X POST http://localhost:8200/api/v1/auth/login \\\n"
        f"    -H 'Content-Type: application/json' \\\n"
        f"    -d '{{\"email\":\"{args.admin_email}\",\"password\":\"{args.admin_password}\"}}'"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--admin-email", default=os.getenv("SEED_ADMIN_EMAIL", "admin@xiuedu.uz"))
    parser.add_argument(
        "--admin-password", default=os.getenv("SEED_ADMIN_PASSWORD", "ChangeMe!2026")
    )
    parser.add_argument("--admin-name", default=os.getenv("SEED_ADMIN_NAME", "Super Administrator"))
    sys.exit(asyncio.run(main(parser.parse_args())) or 0)
