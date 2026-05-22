# XIU Masofaviy Ta'lim Platformasi (LMS)

Oʻzbekiston Respublikasi Vazirlar Mahkamasining **2022-yil 3-oktabrdagi 559-son qarori** asosida XIU (Xalqaro Innovatsiya Universiteti) uchun ishlab chiqilayotgan zamonaviy LMS platformasi.

> **Single-tenant qaror (2026-05-10):** Loyiha **faqat XIU** uchun mo'ljallangan
> (boshqa OTM lar qo'shilmaydi). Schema multi-tenant ko'rinishida qoldirilgan,
> lekin runtime XIU singleton. Tafsilot: `../../../single-tenant-architecture.md`.
> Quyidagi TZ matnlari "OTM" deb yozsa, kontekst — XIU degan ma'noda.

## 🌐 Domenlar

| Domen | Maqsad |
|---|---|
| `lms.xiuedu.uz` | Talaba va o'qituvchi frontend |
| `lms-admin.xiuedu.uz` | Admin va Super-admin paneli |
| `lms-api.xiuedu.uz` | Backend REST API |
| `lms-cdn.xiuedu.uz` | Static fayllar, video, hujjatlar |

To'liq ma'lumot: `docs/07-devops/05-domains-deployment.md`

## 📋 Loyiha haqida

Bu loyiha — oliy ta'lim tashkilotlari (OTM) uchun professional masofaviy ta'lim platformasi. Talabalarni qabul qilishdan tortib diplom berishgacha bo'lgan butun ta'lim jarayonini avtomatlashtiradi.

## 🛠 Texnologik stek

**Backend:** FastAPI (Python 3.11+), PostgreSQL 15+, Redis, Celery, SQLAlchemy 2.0, Alembic
**Frontend:** Vue 3 (Composition API + TypeScript), Tailwind CSS, Pinia, Vite
**Infra:** Docker, Docker Compose, Kubernetes, Nginx, MinIO
**Integratsiyalar:** HEMIS, Zoom, OneID, Click, Payme, Antiplag.uz

## 📚 Hujjatlash strukturasi

```
docs/
├── 01-overview/         # Loyiha haqida umumiy ma'lumot
│   ├── 01-vision.md
│   ├── 02-requirements.md
│   ├── 03-glossary.md
│   └── 04-roles.md
│
├── 02-architecture/     # Texnik arxitektura
│   ├── 01-system-design.md
│   ├── 02-tech-stack.md
│   ├── 03-folder-structure.md
│   └── 04-coding-standards.md
│
├── 03-modules/          # Funksional modullar (her biri alohida sprint)
│   ├── 01-auth.md
│   ├── 02-users-rbac.md
│   ├── 03-academic.md
│   ├── 04-enrollment.md
│   ├── 05-content.md
│   ├── 06-courses.md
│   ├── 07-assignments.md
│   ├── 08-live-classes.md
│   ├── 09-exams-proctoring.md
│   ├── 10-payments.md
│   ├── 11-communications.md
│   └── 12-reports.md
│
├── 04-integrations/     # Tashqi tizimlar bilan integratsiya
│   ├── 01-hemis.md
│   ├── 02-zoom.md
│   ├── 03-oneid.md
│   ├── 04-payment-gateways.md
│   └── 05-otjbat-tsdin.md
│
├── 05-database/         # Ma'lumotlar bazasi
│   ├── 01-schema.md
│   ├── 02-migrations.md
│   └── 03-models.md
│
├── 06-frontend/         # Frontend tafsilotlari
│   ├── 01-design-system.md
│   ├── 02-pages.md
│   └── 03-components.md
│
├── 07-devops/           # Deployment va infrastruktura
│   ├── 01-docker.md
│   ├── 02-ci-cd.md
│   ├── 03-monitoring.md
│   ├── 04-security.md
│   └── 05-domains-deployment.md   # NEW: 4 ta subdomain arxitekturasi
│
└── 08-roadmap/          # Bosqichlar va vazifalar
    ├── 01-phases.md
    ├── 02-sprint-plan.md
    └── 03-claude-tasks.md
```

## 🎯 Claude bilan ishlash tartibi

VS Code'da Claude'ga loyiha bilan ishlash uchun:

1. **Boshlash:** `docs/01-overview/01-vision.md` ni o'qing — loyiha umumiy g'oyasi
2. **Arxitektura:** `docs/02-architecture/` bo'limini o'rganing — texnik qarorlar
3. **Modul tanlang:** `docs/03-modules/` dan 1 ta modulni tanlab boshlang
4. **Sprint rejasi:** `docs/08-roadmap/03-claude-tasks.md` da tayyor topshiriqlar

**Tavsiya:** Har bir modulni alohida Claude session'da yozing, kontekst toza bo'lsin.

## 📞 Aloqa

Loyiha menejeri: _____________
Texnik direktor: _____________

## 📜 Litsenziya

Maxfiy. Faqat ichki foydalanish uchun.
