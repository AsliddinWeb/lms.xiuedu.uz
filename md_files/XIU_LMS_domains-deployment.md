# Domen arxitekturasi va deployment

## 1. Domen taqsimoti

LMS platformasi to'rtta subdomain orqali deploy qilinadi:

| Subdomain | Maqsad | Server | Texnologiya |
|---|---|---|---|
| `lms.xiuedu.uz` | Talaba va o'qituvchi frontend | Web server (Nginx) | Vue 3 SPA (build) |
| `lms-admin.xiuedu.uz` | Admin va Super-admin paneli | Web server (Nginx) | Vue 3 SPA (alohida build) |
| `lms-api.xiuedu.uz` | Backend REST API | App server | FastAPI + Uvicorn/Gunicorn |
| `lms-cdn.xiuedu.uz` | Static fayllar, video, hujjatlar | Object storage / CDN | MinIO yoki S3 + CloudFlare |

### 1.1 Nima uchun shunday bo'linadi?

**`lms.xiuedu.uz` va `lms-admin.xiuedu.uz` alohida:**
- Admin panel kichik foydalanuvchilar guruhiga (50-100 kishi) mo'ljallangan, lekin sezgir operatsiyalar bajaradi (foydalanuvchi yaratish, kontingent o'zgartirish, baholarni manipulyatsiya qilish).
- Alohida domain'da bo'lsa, IP whitelist yoki VPN orqali kirishni cheklash mumkin.
- Frontend bundle ham alohida — admin paneli kerak emas bo'lgan kodlar talabaga yuborilmaydi (bundle hajmi kichikroq).
- Agar admin panelida XSS yoki boshqa zaiflik bo'lsa, talaba domain'iga ta'sir qilmaydi.

**`lms-api.xiuedu.uz` alohida:**
- CORS va Cookie sozlamalari frontend'lardan farqli.
- Rate limiting alohida ishlaydi, statik fayllar request'i API'ga ta'sir qilmaydi.
- API alohida serverga (yoki Kubernetes pod'iga) deploy qilinadi.
- Frontend yiqilsa ham, mobile ilovalar va boshqa klientlar API bilan ishlay oladi.

**`lms-cdn.xiuedu.uz` alohida:**
- Video darslar (10-500 MB), PDF darsliklar, talaba avatarlari shu yerda.
- CloudFlare CDN orqali butun dunyoga tezroq tarqatish.
- Asosiy serverning bandwidth'ini band qilmaydi.
- `Cache-Control: public, max-age=31536000` immutable fayllar uchun.

## 2. DNS sozlamalari

DNS provider'da quyidagi yozuvlar yaratiladi (cPanel yoki CloudFlare DNS):

```
Tip   Nom              Qiymat                    TTL
A     lms              <SERVER_IP>               300
A     lms-admin        <SERVER_IP>               300
A     lms-api          <APP_SERVER_IP>           300
A     lms-cdn          <CDN_OR_STORAGE_IP>       300

# Yoki CDN orqali:
CNAME lms-cdn          xiuedu.b-cdn.net          300

# Mail (DSI/HEMIS hisobotlari uchun)
MX    @                mail.xiuedu.uz            300

# SPF, DKIM, DMARC
TXT   @                "v=spf1 include:..."      300
```

## 3. SSL sertifikatlar

**Tavsiya:** Wildcard sertifikat — `*.xiuedu.uz`. Bu bitta sertifikat barcha subdomain'larni qamrab oladi.

### 3.1 Let's Encrypt orqali (bepul)

```bash
# Certbot o'rnatish
sudo apt install certbot python3-certbot-nginx python3-certbot-dns-cloudflare

# Wildcard sertifikat (DNS-01 challenge orqali)
sudo certbot certonly \
  --dns-cloudflare \
  --dns-cloudflare-credentials /etc/cloudflare.ini \
  -d xiuedu.uz \
  -d "*.xiuedu.uz" \
  --email admin@xiuedu.uz \
  --agree-tos
```

### 3.2 UZINFOCOM orqali (rasmiy)

Davlat oliy ta'lim muassasalari uchun UZINFOCOM tomonidan beriladi. Hujjatlar:
- OTM rasmiy maktubi
- Ariza forma
- Domen egaligi tasdig'i

## 4. Nginx konfiguratsiyasi

### 4.1 `lms.xiuedu.uz` — Talaba/o'qituvchi frontend

```nginx
upstream frontend_static {
    server 127.0.0.1:3000;
}

server {
    listen 443 ssl http2;
    server_name lms.xiuedu.uz;

    ssl_certificate /etc/letsencrypt/live/xiuedu.uz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/xiuedu.uz/privkey.pem;

    root /var/www/lms-frontend/dist;
    index index.html;

    # Vue Router (history mode)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Static assets — uzoq cache
    location ~* \.(js|css|woff2|png|jpg|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' fonts.googleapis.com; img-src 'self' data: https://lms-cdn.xiuedu.uz; connect-src 'self' https://lms-api.xiuedu.uz wss://lms-api.xiuedu.uz; font-src fonts.gstatic.com" always;
}

server {
    listen 80;
    server_name lms.xiuedu.uz;
    return 301 https://$host$request_uri;
}
```

### 4.2 `lms-admin.xiuedu.uz` — Admin panel

```nginx
server {
    listen 443 ssl http2;
    server_name lms-admin.xiuedu.uz;

    ssl_certificate /etc/letsencrypt/live/xiuedu.uz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/xiuedu.uz/privkey.pem;

    # IP whitelist — faqat universitet ofisidan
    # allow 5.135.xxx.xxx;       # Universitet IP-blok
    # allow 84.54.xxx.xxx;       # Server IP
    # deny all;
    # Production'da yoqing, dev davrida kommentariyada

    root /var/www/lms-admin/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location ~* \.(js|css|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Admin paneliga indekslash taqiqlanadi
    add_header X-Robots-Tag "noindex, nofollow" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
}
```

### 4.3 `lms-api.xiuedu.uz` — Backend API

```nginx
upstream backend {
    least_conn;
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8001 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8002 max_fails=3 fail_timeout=30s;
}

# Rate limiting
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=5r/m;
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=60r/m;

server {
    listen 443 ssl http2;
    server_name lms-api.xiuedu.uz;

    ssl_certificate /etc/letsencrypt/live/xiuedu.uz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/xiuedu.uz/privkey.pem;

    client_max_body_size 100M;  # Video uploads
    proxy_read_timeout 300s;     # Long-running tasks

    # Auth endpoints — strict rate limit
    location ~ ^/api/v1/auth/(login|register|forgot-password) {
        limit_req zone=auth_limit burst=3 nodelay;
        proxy_pass http://backend;
        include /etc/nginx/proxy_params;
    }

    # Umumiy API
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://backend;
        include /etc/nginx/proxy_params;
    }

    # WebSocket (live class, proctoring, notifications)
    location /ws/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
    }

    # OpenAPI docs (faqat staging/dev)
    location /docs {
        # Production'da:
        # return 404;
        proxy_pass http://backend;
    }

    # CORS — faqat o'zimizning frontend'lar
    add_header Access-Control-Allow-Origin $http_origin always;
    add_header Access-Control-Allow-Credentials "true" always;
    add_header Vary "Origin" always;

    # CORS preflight
    if ($request_method = 'OPTIONS') {
        add_header Access-Control-Allow-Methods "GET, POST, PUT, PATCH, DELETE, OPTIONS";
        add_header Access-Control-Allow-Headers "Authorization, Content-Type, X-Requested-With";
        add_header Access-Control-Max-Age 86400;
        return 204;
    }
}
```

`/etc/nginx/proxy_params`:

```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_redirect off;
proxy_buffering off;
```

### 4.4 `lms-cdn.xiuedu.uz` — Static fayllar va media

**Variant A: MinIO (o'z serverda)**

```nginx
server {
    listen 443 ssl http2;
    server_name lms-cdn.xiuedu.uz;

    ssl_certificate /etc/letsencrypt/live/xiuedu.uz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/xiuedu.uz/privkey.pem;

    client_max_body_size 1G;  # Katta video fayllar

    # MinIO ga proxy
    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300;
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }

    # Cache control
    add_header Cache-Control "public, max-age=31536000, immutable";

    # CORS — faqat lms.xiuedu.uz va lms-admin.xiuedu.uz
    add_header Access-Control-Allow-Origin "https://lms.xiuedu.uz" always;
}
```

**Variant B: CloudFlare R2 yoki BunnyCDN (tavsiya)**

DNS:
```
CNAME  lms-cdn   xiuedu.b-cdn.net
```

CloudFlare/Bunny panelida:
- Origin: MinIO yoki S3
- Cache TTL: 1 yil immutable fayllar uchun
- Geo-restriction: O'zbekiston + Markaziy Osiyo

## 5. Server arxitekturasi

### 5.1 Minimal setup (bitta server, kichik OTM, < 1000 talaba)

```
┌─────────────────────────────────────────────┐
│  VPS (8 CPU, 16 GB RAM, 200 GB SSD)         │
├─────────────────────────────────────────────┤
│  Nginx (reverse proxy + SSL)                │
│   ├─ lms.xiuedu.uz       → Vue static      │
│   ├─ lms-admin.xiuedu.uz → Vue static      │
│   ├─ lms-api.xiuedu.uz   → FastAPI:8000    │
│   └─ lms-cdn.xiuedu.uz   → MinIO:9000      │
│                                              │
│  Docker Compose:                             │
│   ├─ FastAPI (3 worker)                     │
│   ├─ PostgreSQL 16                          │
│   ├─ Redis 7                                │
│   ├─ MinIO                                  │
│   └─ Celery worker                          │
└─────────────────────────────────────────────┘
```

### 5.2 Production setup (alohida serverlar, > 5000 talaba)

```
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  Web Server      │   │  App Server      │   │  Database        │
│  (Nginx + SPA)   │   │  (FastAPI x N)   │   │  PostgreSQL +    │
│                  │   │                  │   │  Redis           │
│  lms.xiuedu.uz   │←─→│  lms-api.xiuedu  │←─→│                  │
│  lms-admin...    │   │                  │   │                  │
└──────────────────┘   └──────────────────┘   └──────────────────┘
                              ↓
                       ┌──────────────────┐
                       │  Object Storage  │
                       │  MinIO / S3      │
                       │  lms-cdn...      │
                       └──────────────────┘
                              ↓
                       ┌──────────────────┐
                       │  CloudFlare CDN  │
                       │  (edge cache)    │
                       └──────────────────┘
```

**Tavsiya etilgan provayderlar:**
- **UCloud** (uztelecom) — O'zbekiston hududida, davlat talabiga muvofiq (559-son qaror, 8-band: server O'zbekiston hududida)
- **Hosting.uz** — local hosting
- **PS.uz** (Peoples Server) — VPS

## 6. Frontend muhit o'zgaruvchilari

### `frontend/.env.production`

```bash
# lms.xiuedu.uz va lms-admin.xiuedu.uz uchun
VITE_API_URL=https://lms-api.xiuedu.uz/api/v1
VITE_WS_URL=wss://lms-api.xiuedu.uz/ws
VITE_CDN_URL=https://lms-cdn.xiuedu.uz
VITE_APP_URL=https://lms.xiuedu.uz
VITE_ADMIN_URL=https://lms-admin.xiuedu.uz

# OneID
VITE_ONEID_CLIENT_ID=xxx
VITE_ONEID_REDIRECT_URI=https://lms.xiuedu.uz/auth/oneid/callback
VITE_ONEID_AUTHORIZE_URL=https://my.gov.uz/oneid/v1/oauth/authorize

# Sentry
VITE_SENTRY_DSN=xxx

# Google Analytics / Plausible
VITE_ANALYTICS_DOMAIN=lms.xiuedu.uz
```

### `frontend/.env.development`

```bash
VITE_API_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/ws
VITE_CDN_URL=http://localhost:9000
VITE_APP_URL=http://localhost:5173
```

## 7. Backend muhit o'zgaruvchilari

### `backend/.env.production`

```bash
# Database
DATABASE_URL=postgresql://lms_user:STRONG_PASSWORD@db.internal:5432/lms_xiuedu
REDIS_URL=redis://redis.internal:6379/0

# Domains
APP_DOMAIN=lms.xiuedu.uz
ADMIN_DOMAIN=lms-admin.xiuedu.uz
API_DOMAIN=lms-api.xiuedu.uz
CDN_DOMAIN=lms-cdn.xiuedu.uz

# CORS (faqat o'zimizning subdomain'lar)
CORS_ORIGINS=https://lms.xiuedu.uz,https://lms-admin.xiuedu.uz

# JWT
JWT_SECRET=<generate-strong-secret-with-openssl-rand-hex-64>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# OneID
ONEID_CLIENT_ID=xxx
ONEID_CLIENT_SECRET=xxx
ONEID_REDIRECT_URI=https://lms.xiuedu.uz/auth/oneid/callback
ONEID_TOKEN_URL=https://my.gov.uz/oneid/v1/oauth/token

# HEMIS
HEMIS_API_URL=https://student.xiuedu.uz/rest/v1
HEMIS_API_TOKEN=xxx

# OTJBAT (Vazirlik integratsiya)
OTJBAT_API_URL=https://otjbat.gov.uz/api/v1
OTJBAT_API_KEY=xxx

# TSDIN (Ta'lim sifati DSI)
TSDIN_API_URL=https://tsdin.gov.uz/api/v1
TSDIN_API_KEY=xxx

# MinIO/S3
MINIO_ENDPOINT=lms-cdn.xiuedu.uz
MINIO_ACCESS_KEY=xxx
MINIO_SECRET_KEY=xxx
MINIO_BUCKET=lms-files
MINIO_USE_SSL=true

# Email
SMTP_HOST=smtp.xiuedu.uz
SMTP_PORT=587
SMTP_USER=noreply@xiuedu.uz
SMTP_PASSWORD=xxx
SMTP_FROM=noreply@xiuedu.uz

# SMS (Eskiz)
SMS_API_URL=https://notify.eskiz.uz/api
SMS_API_TOKEN=xxx

# Payment gateways
CLICK_SERVICE_ID=xxx
CLICK_MERCHANT_ID=xxx
CLICK_SECRET_KEY=xxx
PAYME_MERCHANT_ID=xxx
PAYME_SECRET_KEY=xxx

# Sentry
SENTRY_DSN=xxx
SENTRY_ENVIRONMENT=production

# Proctoring
PROCTORING_S3_BUCKET=lms-proctoring-recordings
PROCTORING_RETENTION_DAYS=365

# Akademik holat (559-son qaror talablariga muvofiq)
ACADEMIC_YEAR=2025-2026
SEMESTER=autumn
TEACHER_STUDENT_RATIO_MAX=50
```

## 8. Deployment workflow

### 8.1 Build pipeline

```bash
# Frontend (lms.xiuedu.uz)
cd frontend
npm install
npm run build:user      # Vite build → dist/user
rsync -avz dist/user/ deploy@server:/var/www/lms-frontend/dist/

# Frontend (lms-admin.xiuedu.uz)
npm run build:admin     # Vite build → dist/admin
rsync -avz dist/admin/ deploy@server:/var/www/lms-admin/dist/

# Backend (lms-api.xiuedu.uz)
cd backend
docker build -t registry.xiuedu.uz/lms-backend:$TAG .
docker push registry.xiuedu.uz/lms-backend:$TAG
ssh deploy@app-server "docker pull registry.xiuedu.uz/lms-backend:$TAG && docker compose up -d"
```

### 8.2 Vite config — multi-app build

`frontend/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'

export default defineConfig(({ mode }) => ({
  base: '/',
  build: {
    outDir: mode === 'admin' ? 'dist/admin' : 'dist/user',
    rollupOptions: {
      input: mode === 'admin'
        ? './src/admin/main.ts'
        : './src/user/main.ts'
    }
  },
  server: {
    proxy: {
      '/api': 'https://lms-api.xiuedu.uz',
      '/ws':  { target: 'wss://lms-api.xiuedu.uz', ws: true }
    }
  }
}))
```

`package.json`:
```json
{
  "scripts": {
    "build:user":  "vite build --mode user",
    "build:admin": "vite build --mode admin",
    "build:all":   "npm run build:user && npm run build:admin"
  }
}
```

## 9. Cookie va Session strategiyasi

JWT tokenlar **HttpOnly Cookie** orqali yuboriladi va `Domain=.xiuedu.uz` bilan barcha LMS subdomain'larida ishlaydi:

```python
# backend/app/auth/cookies.py
response.set_cookie(
    key="access_token",
    value=token,
    max_age=900,           # 15 daqiqa
    httponly=True,
    secure=True,           # HTTPS only
    samesite="lax",
    domain=".xiuedu.uz"    # Subdomain'lar orasida ishlash
)
```

Bu yerda muhim — `Domain=.xiuedu.uz` (boshida nuqta) lms.xiuedu.uz va lms-admin.xiuedu.uz orasida session'ni share qilishga imkon beradi, lekin `xiuedu.uz` (info sayt) ga ham ko'rinadi. Agar info sayt ham xuddi shu serverda bo'lsa va u bilan share qilish kerak bo'lmasa — alohida cookie domain ishlatish lozim.

## 10. Monitoring va kuzatuv

| Subdomain | Health endpoint | Monitoring |
|---|---|---|
| `lms.xiuedu.uz` | `/health` (static) | UptimeRobot / Pingdom |
| `lms-admin.xiuedu.uz` | `/health` | UptimeRobot |
| `lms-api.xiuedu.uz` | `/api/v1/health` | Prometheus + Grafana, Sentry |
| `lms-cdn.xiuedu.uz` | `/minio/health/live` | Prometheus |

### Status sahifasi (ixtiyoriy)

`status.xiuedu.uz` — barcha xizmatlar uptime'i (Cachet yoki Statping orqali).

## 11. Backup va Disaster Recovery

| Komponent | Backup chastotasi | Saqlash joyi | Retention |
|---|---|---|---|
| PostgreSQL (asosiy DB) | Har 6 soatda | S3 + offsite | 30 kun |
| MinIO (video, fayllar) | Kunlik snapshot | S3 mirror | 90 kun |
| Redis (sessiyalar) | Backup shart emas | — | — |
| Nginx config | Git versiyalashda | GitHub/GitLab | ∞ |
| SSL sertifikatlar | Avtomatik (Certbot) | Server | 90 kun (avto-renew) |

## 12. 559-son qaror muvofiqligi

| Talab | Manba | Yechim |
|---|---|---|
| Server O'zbekiston hududida | 559-son qaror, 3-bob, 8-band | UCloud (uztelecom) yoki PS.uz |
| Yuqori tezlikdagi internet | 4-band | Min. 1 Gbps backbone |
| HEMIS integratsiya | 6-bob, 29-band | `https://student.xiuedu.uz` orqali |
| DSI (Ta'lim sifati) integratsiya | 29-band | `https://tsdin.gov.uz` orqali |
| Avtoproktoring | 4-bob, 10-band | DeepFace + MediaPipe + Whisper |
| Wildcard SSL | Xavfsizlik | Let's Encrypt yoki UZINFOCOM |

## 13. To'rt-domenli setup checklist

- [ ] DNS A-yozuvlar yaratilgan (4 ta subdomain)
- [ ] Wildcard SSL sertifikat olingan (`*.xiuedu.uz`)
- [ ] Nginx server bloklari yozilgan (4 ta)
- [ ] Frontend `.env.production` ikki versiyada (user, admin)
- [ ] Backend `.env.production` to'rt domain'ni biladi
- [ ] CORS faqat `lms.xiuedu.uz` va `lms-admin.xiuedu.uz` ga ruxsat beradi
- [ ] Cookie `Domain=.xiuedu.uz` bilan ishlaydi
- [ ] CSP headers CDN va API URL'lariga ruxsat beradi
- [ ] HEMIS API token qo'yilgan
- [ ] OneID redirect URI `lms.xiuedu.uz`ga to'g'ri keladi
- [ ] MinIO bucket policy CDN domain'ga mos
- [ ] Backup automation qo'yilgan (cron yoki BorgBackup)
- [ ] Monitoring (Sentry, UptimeRobot) sozlangan
- [ ] Status sahifasi yoki dashboard tayyor
