# XIU LMS — Production Deploy

Ubuntu 22.04 + Docker server'da deploy qilish bo'yicha qadamlar.

---

## 1. Server tayyorlash

Bu hujjat **Ubuntu 22.04 + Docker + Docker Compose v2 oldindan o'rnatilgan** server'ni nazarda tutadi.

```bash
docker --version              # >= 24.x
docker compose version        # v2.x
```

Tashqi nginx domain → port forward sozlangan bo'lishi kerak:
- `lms.xiuedu.uz` → `localhost:8201` (talaba frontend)
- `lms-admin.xiuedu.uz` → `localhost:8203` (admin frontend)
- `lms-api.xiuedu.uz` → `localhost:8200` (backend API)
- `lms-cdn.xiuedu.uz` → `localhost:8212` (MinIO S3, presigned URL'lar uchun)

---

## 2. Project'ni klonlash

```bash
sudo mkdir -p /opt/lms
sudo chown $USER:$USER /opt/lms
cd /opt/lms
git clone <repo-url> .
```

---

## 3. Konfiguratsiya — yagona `.env.production`

Barcha secret'lar va sozlamalar **bitta** root `.env.production` faylida.
Backend container uni compose orqali oladi — alohida `backend/.env.production`
KERAK EMAS.

```bash
cp .env.production.example .env.production
nano .env.production
```

**Majburiy o'zgartirish kerak bo'lgan secret'lar:**

| O'zgaruvchi | Generator buyruq |
|---|---|
| `POSTGRES_PASSWORD` | `openssl rand -hex 24` (HEX majburiy — URL-safe) |
| `REDIS_PASSWORD` | `openssl rand -hex 18` (HEX majburiy — URL-safe) |
| `MINIO_ROOT_USER` | Ixtiyoriy nom (masalan `lms_minio`) |
| `MINIO_ROOT_PASSWORD` | `openssl rand -hex 24` |
| `JWT_SECRET_KEY` | `openssl rand -hex 64` |
| `LIVEKIT_API_KEY` | `openssl rand -hex 16` |
| `LIVEKIT_API_SECRET` | `openssl rand -hex 32` (min. 32 belgi) |
| `SMTP_PASSWORD` | Real SMTP server parol (Gmail App Password va h.k.) |

**Domain sozlamalari (real prod):**

| O'zgaruvchi | Misol qiymat |
|---|---|
| `VITE_API_URL_USER` | `https://lms-api.xiuedu.uz/api/v1` |
| `VITE_API_URL_ADMIN` | `https://lms-api.xiuedu.uz/api/v1` |
| `CORS_ORIGINS` | `https://lms.xiuedu.uz,https://lms-admin.xiuedu.uz` |
| `APP_FRONTEND_URL` | `https://lms.xiuedu.uz` |
| `ADMIN_FRONTEND_URL` | `https://lms-admin.xiuedu.uz` |
| `MINIO_PUBLIC_URL` | `https://lms-cdn.xiuedu.uz` |
| `LIVEKIT_URL_PUBLIC` | `wss://lms-api.xiuedu.uz/livekit` |
| `COOKIE_DOMAIN` | `.xiuedu.uz` |

> **Eslatma:** Backend container'ga `DATABASE_URL`, `REDIS_URL`, `MINIO_ACCESS_KEY/SECRET_KEY`
> compose orqali **avtomatik tuziladi** (infra parol'laridan). Qo'shimcha sozlash shart emas.

---

## 4. Birinchi deploy

```bash
bash scripts/deploy/initial-deploy.sh
```

Script avtomatik bajaradigan amallar:
1. Eski konteynerlarni to'xtatish (agar bo'lsa)
2. Image'larni build qilish (5–15 daqiqa)
3. Infra servislar (postgres/redis/minio/livekit) ishga tushirish
4. Backend ishga tushirish + Alembic migration
5. Boshlang'ich seed: rollar, ruxsatlar, demo akkauntlar, badge katalogi
6. Frontend (user + admin) build va boshlash

---

## 5. Tekshirish

```bash
# Konteynerlar holati
docker compose --env-file .env.production -f docker-compose.prod.yml ps

# Backend health
curl http://localhost:8200/api/v1/health

# Frontend (Vue Router SPA fallback)
curl http://localhost:8201/health
curl http://localhost:8203/health
```

Brauzerdan:
- `https://lms.xiuedu.uz` — talaba interfeysi
- `https://lms-admin.xiuedu.uz` — admin interfeysi

Demo akkauntlar (`backend/.env.production` ichida `APP_DEBUG=false` bo'lsa ham seed orqali yaratiladi):
- `admin@xiuedu.uz` / `ChangeMe!2026`
- `teacher@xiuedu.uz` / `Teacher!2026`
- `student@xiuedu.uz` / `Student!2026`

**MUHIM:** Production'da ishga tushgan zahoti `admin` parolini o'zgartiring.

---

## 6. Yangilash (git pull → restart)

```bash
cd /opt/lms
git pull
bash scripts/deploy/update.sh
```

Script:
1. Image'larni qayta build qiladi
2. Alembic migration ishga tushiradi
3. Faqat backend va frontend konteynerlarini qayta yaratadi (rolling restart)
4. Eski image'larni tozalaydi

---

## 7. Backup (cron)

```bash
# Har kuni 03:00'da
crontab -e
0 3 * * * cd /opt/lms && bash scripts/backup/backup.sh >> /var/log/lms-backup.log 2>&1
```

Backup tuzilmasi:
```
backups/20260521_030000/
  ├── postgres.dump
  ├── minio/
  └── manifest.txt
```

Oxirgi 14 ta backup avtomatik saqlanadi.

---

## 8. Tez-tez ishlatiladigan buyruqlar

```bash
# Loglarni ko'rish
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f backend

# Faqat backend'ni qayta ishga tushirish
docker compose --env-file .env.production -f docker-compose.prod.yml restart backend

# DB ichiga kirish
docker compose --env-file .env.production -f docker-compose.prod.yml exec postgres psql -U lms -d lms_xiuedu

# Migration tarixi
docker compose --env-file .env.production -f docker-compose.prod.yml exec backend alembic history

# Test (production'da kerak bo'lmaydi, lekin smoke uchun)
docker compose --env-file .env.production -f docker-compose.prod.yml exec backend pytest tests/integration/test_student_e2e.py -v
```

---

## 9. Muammolarni hal qilish

### Backend ishga tushmaydi
```bash
docker compose --env-file .env.production -f docker-compose.prod.yml logs backend | tail -50
```
Tekshirish:
- `backend/.env.production` mavjud va to'g'ri to'ldirilgan
- `DATABASE_URL`, `REDIS_URL`, `MINIO_*` parol'lari root `.env.production` bilan mos keladimi
- Postgres healthcheck o'tdimi: `docker compose ... ps postgres`

### Frontend 502 / boshlang'ich rasm yo'q
- Vite build vaqtida `VITE_API_URL_*` to'g'ri ko'rsatilganmi tekshiring
- Build'ni qayta bajaring: `docker compose ... build --no-cache frontend-user frontend-admin`

### MinIO 403 (presigned URL)
- `MINIO_PUBLIC_URL` server'dagi tashqi nginx orqali ko'rinadigan URL bo'lishi kerak
- Bucket policy: `lms-files` uchun ba'zi prefikslar public, qolganlari private — `app/core/storage.py` init_storage avtomatik o'rnatadi
