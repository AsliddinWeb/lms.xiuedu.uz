# XIU LMS Platform

Xalqaro Innovatsiya Universiteti (XIU) uchun masofaviy ta'lim platformasi. O'zbekiston Respublikasi Vazirlar Mahkamasining 2022-yil 3-oktabrdagi 559-son qarori va OʻzDSt 36.2030 standartiga muvofiq.

> **Single-tenant:** Loyiha **faqat XIU** uchun ishlab chiqiladi (boshqa OTM lar
> qo'shilmaydi). Schema multi-tenant ko'rinishida qoldirilgan, runtime butunlay
> XIU singleton. Tafsilot: [`md_files/single-tenant-architecture.md`](md_files/single-tenant-architecture.md).

To'liq texnik talablar — `md_files/xiu_lms_tz_md/lms_tz_xiuedu/docs/` papkasida.
Faol implementation hujjatlari — `md_files/` papkasi ostida (role-access-matrix,
single-tenant-architecture, phase4-gaps-tracker, XIU_LMS_domains-deployment).

## Domenlar

| Domen | Maqsad |
|---|---|
| `lms.xiuedu.uz` | Talaba va o'qituvchi frontend |
| `lms-admin.xiuedu.uz` | Admin va Super-admin paneli |
| `lms-api.xiuedu.uz` | Backend REST API |
| `lms-cdn.xiuedu.uz` | Static fayllar, video, hujjatlar |

## Stek

- **Backend:** FastAPI 0.110+, Python 3.11+, SQLAlchemy 2.0 (async), Alembic, Celery, Redis 7+
- **Frontend:** Vue 3 (Composition + TS), Vite, Tailwind CSS, Pinia, Vue Router 4
- **DB / Storage:** PostgreSQL 16+, MinIO (S3-compat)
- **Infra:** Docker, Nginx, GitHub Actions

## Loyiha tuzilmasi

```
lms_xiuedu/
├── backend/        # FastAPI ilovasi
├── frontend/       # Vue 3 SPA (user + admin, ikki entry point)
├── infra/          # Nginx, Postgres init, monitoring
├── scripts/        # Yordamchi skriptlar
├── md_files/       # Texnik topshiriq (TZ) hujjatlari
├── .github/        # CI/CD workflow'lari
├── docker-compose.yml
└── .env.example
```

## Ishga tushirish (lokal)

```bash
# 1. Environment fayllarini sozlash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 2. Servislarni ko'tarish
docker compose up -d postgres redis minio mailhog

# 3. Backend (host'dan, port 8200)
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8200

# 4. Frontend (alohida terminal)
cd frontend
pnpm install
pnpm dev:user      # http://localhost:8201
# yoki
pnpm dev:admin     # http://localhost:8203
```

## Docker bilan to'liq stack

```bash
docker compose up -d
```

| Xizmat | URL / Port |
|---|---|
| Backend API | http://localhost:8200 |
| Backend docs | http://localhost:8200/docs |
| Frontend (user) | http://localhost:8201 |
| Frontend (admin) | http://localhost:8203 |
| PostgreSQL | localhost:8210 |
| Redis | localhost:8211 |
| MinIO API | http://localhost:8212 |
| MinIO konsol | http://localhost:8213 |
| Mailhog SMTP | localhost:8214 |
| Mailhog UI | http://localhost:8215 |

> **Izoh:** Lokal portlar boshqa loyihalar tomonidan band bo'lmasligi uchun barcha
> xizmatlar 82xx oralig'iga ko'chirilgan. Konteyner ichida xizmatlar standart
> portlarda ishlaydi (postgres:5432, redis:6379, minio:9000, va h.k.).

## Loyihaning fazalari

11 ta fazaga bo'lingan, har biri alohida deliverable bilan. Joriy holat:
**Phase 4 yakunlandi** (Auth, RBAC, Akademik struktura, Content+Courses,
Assignments+Grading+Peer-review+Appeals) + **single-tenant migration tugadi**.
Keyingisi: **Phase 5 — Live darslar (WebRTC)**.

Reja va batafsil ma'lumot: `md_files/` papkasidagi MD fayllarda.

## Litsenziya

Maxfiy. Faqat ichki foydalanish uchun.
