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
- `lms.xiuedu.uz` → `localhost:8201`
- `lms-admin.xiuedu.uz` → `localhost:8203`
- `api.xiuedu.uz` (yoki shu sub-path) → `localhost:8200`
- `storage.xiuedu.uz` → `localhost:8212` (MinIO S3 API, presigned URL'lar uchun)
- `live.xiuedu.uz` → `localhost:7880` (LiveKit WS)

---

## 2. Project'ni klonlash

```bash
sudo mkdir -p /opt/lms
sudo chown $USER:$USER /opt/lms
cd /opt/lms
git clone <repo-url> .
```

---

## 3. Konfiguratsiya — `.env.production` fayllar

### Root `.env.production` (docker-compose uchun)

```bash
cp .env.production.example .env.production
nano .env.production
```

Quyidagilarni **majburiy** o'zgartiring:

| O'zgaruvchi | Buyruq |
|---|---|
| `POSTGRES_PASSWORD` | `openssl rand -base64 32` |
| `REDIS_PASSWORD` | `openssl rand -base64 24` |
| `MINIO_ROOT_PASSWORD` | `openssl rand -base64 32` |
| `LIVEKIT_API_SECRET` | `openssl rand -hex 32` (min. 32 belgi) |
| `VITE_API_URL_USER` | Talaba domain'i, masalan `https://lms.xiuedu.uz/api/v1` |
| `VITE_API_URL_ADMIN` | Admin domain'i, masalan `https://lms-admin.xiuedu.uz/api/v1` |

### Backend `.env.production`

```bash
cp backend/.env.production.example backend/.env.production
nano backend/.env.production
```

**Eng muhim sozlamalar:**

| O'zgaruvchi | Eslatma |
|---|---|
| `JWT_SECRET_KEY` | `openssl rand -hex 64` |
| `DATABASE_URL` | Root .env'dagi `POSTGRES_PASSWORD` bilan mos kelishi kerak |
| `REDIS_URL` | `redis://:PAROL@redis:6379/0` |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | Root .env'dagi root user/parol |
| `CORS_ORIGINS` | Real prod domain'lar, vergul bilan |
| `APP_FRONTEND_URL`, `ADMIN_FRONTEND_URL` | HTTPS bilan |
| `SMTP_*` | Real SMTP server (Mailhog production'da yo'q) |
| `HEMIS_API_URL`, `HEMIS_API_TOKEN` | HEMIS sinxronizatsiya uchun |
| `LIVEKIT_URL_PUBLIC` | Brauzerdan ko'rinadigan `wss://` URL |
| `COOKIE_DOMAIN=.xiuedu.uz`, `COOKIE_SECURE=true` | Production cookie sozlamalari |

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
