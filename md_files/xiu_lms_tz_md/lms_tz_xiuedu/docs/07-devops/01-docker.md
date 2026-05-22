# 07.01. Docker konfiguratsiyasi

## Maqsad

Loyihani Docker konteynerlarda ishga tushirish, lokal va production muhitlarini birxillashtirish.

## Konteyner arxitekturasi

```
┌─────────────────────────────────────────────────────┐
│                   Nginx (Reverse Proxy)             │
│                       :80, :443                     │
└────────────┬───────────────────────────┬────────────┘
             │                           │
    ┌────────▼────────┐         ┌────────▼────────┐
    │  Frontend (Vue) │         │ Backend (FastAPI)│
    │      :5173      │         │      :8000       │
    └─────────────────┘         └────────┬─────────┘
                                         │
                ┌────────────────────────┼────────────────────────┐
                │                        │                        │
       ┌────────▼────────┐      ┌────────▼────────┐      ┌────────▼────────┐
       │  PostgreSQL     │      │     Redis       │      │     MinIO       │
       │     :5432       │      │     :6379       │      │  :9000, :9001   │
       └─────────────────┘      └─────────────────┘      └─────────────────┘
                                         │
                            ┌────────────┴────────────┐
                            │                         │
                   ┌────────▼────────┐       ┌────────▼────────┐
                   │  Celery Worker  │       │  Celery Beat    │
                   └─────────────────┘       └─────────────────┘
```

## Backend Dockerfile

`backend/Dockerfile`:

```dockerfile
# Multi-stage build
FROM python:3.11-slim AS builder

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install --no-cache-dir poetry==1.7.1 \
    && poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Production stage
FROM python:3.11-slim AS production

WORKDIR /app

# Runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application
COPY . .

# Non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

## Frontend Dockerfile

`frontend/Dockerfile`:

```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

# Production stage - Nginx
FROM nginx:1.25-alpine AS production

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

`frontend/nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Vue Router (history mode)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Static assets caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

## docker-compose.yml (Development)

`docker-compose.yml`:

```yaml
version: '3.9'

services:
  postgres:
    image: postgres:15-alpine
    container_name: lms_postgres
    environment:
      POSTGRES_USER: lms_user
      POSTGRES_PASSWORD: lms_password
      POSTGRES_DB: lms_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U lms_user -d lms_db"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - lms_network

  redis:
    image: redis:7-alpine
    container_name: lms_redis
    command: redis-server --requirepass redis_password
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - lms_network

  minio:
    image: minio/minio:latest
    container_name: lms_minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minio_admin
      MINIO_ROOT_PASSWORD: minio_password
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - lms_network

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: production
    container_name: lms_backend
    environment:
      DATABASE_URL: postgresql+asyncpg://lms_user:lms_password@postgres:5432/lms_db
      REDIS_URL: redis://:redis_password@redis:6379/0
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: minio_admin
      MINIO_SECRET_KEY: minio_password
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      ENVIRONMENT: development
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
    networks:
      - lms_network

  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: lms_celery_worker
    command: celery -A app.celery_app worker --loglevel=info --concurrency=4
    environment:
      DATABASE_URL: postgresql+asyncpg://lms_user:lms_password@postgres:5432/lms_db
      REDIS_URL: redis://:redis_password@redis:6379/0
      CELERY_BROKER_URL: redis://:redis_password@redis:6379/1
    volumes:
      - ./backend:/app
    depends_on:
      - backend
      - redis
    networks:
      - lms_network

  celery_beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: lms_celery_beat
    command: celery -A app.celery_app beat --loglevel=info
    environment:
      DATABASE_URL: postgresql+asyncpg://lms_user:lms_password@postgres:5432/lms_db
      CELERY_BROKER_URL: redis://:redis_password@redis:6379/1
    volumes:
      - ./backend:/app
    depends_on:
      - backend
      - redis
    networks:
      - lms_network

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: production
    container_name: lms_frontend
    ports:
      - "5173:80"
    depends_on:
      - backend
    networks:
      - lms_network

  nginx:
    image: nginx:1.25-alpine
    container_name: lms_nginx
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - frontend
      - backend
    networks:
      - lms_network

volumes:
  postgres_data:
  redis_data:
  minio_data:

networks:
  lms_network:
    driver: bridge
```

## .env namuna

`.env.example`:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://lms_user:lms_password@postgres:5432/lms_db
POSTGRES_USER=lms_user
POSTGRES_PASSWORD=change_me_in_production
POSTGRES_DB=lms_db

# Redis
REDIS_URL=redis://:redis_password@redis:6379/0
REDIS_PASSWORD=change_me_in_production

# JWT
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# MinIO / S3
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minio_admin
MINIO_SECRET_KEY=change_me_in_production
MINIO_BUCKET=lms-files

# HEMIS
HEMIS_API_URL=https://student.xiuedu.uz/rest/v1
HEMIS_API_TOKEN=your-hemis-token

# OneID
ONEID_CLIENT_ID=your-client-id
ONEID_CLIENT_SECRET=your-client-secret
ONEID_REDIRECT_URI=https://lms.xiuedu.uz/auth/oneid/callback

# Zoom
ZOOM_ACCOUNT_ID=your-account-id
ZOOM_CLIENT_ID=your-client-id
ZOOM_CLIENT_SECRET=your-client-secret

# Payment Gateways
CLICK_MERCHANT_ID=your-merchant-id
CLICK_SERVICE_ID=your-service-id
CLICK_SECRET_KEY=your-secret-key

PAYME_MERCHANT_ID=your-merchant-id
PAYME_SECRET_KEY=your-secret-key

# OTJBAT/TSDIN
OTJBAT_API_URL=https://otjbat.gov.uz/api/v1
OTJBAT_API_KEY=your-api-key

# SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@xiuedu.uz
SMTP_PASSWORD=your-password

# SMS Gateway (Eskiz/PlayMobile)
SMS_API_URL=https://notify.eskiz.uz/api
SMS_API_TOKEN=your-token

# Sentry
SENTRY_DSN=https://xxx@sentry.io/yyy

# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

## Production docker-compose

`docker-compose.prod.yml` (override):

```yaml
version: '3.9'

services:
  backend:
    restart: always
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
    environment:
      ENVIRONMENT: production
      DEBUG: false
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  frontend:
    restart: always
    deploy:
      replicas: 2

  postgres:
    restart: always
    environment:
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8 --lc-collate=uz_UZ.UTF-8"
    deploy:
      resources:
        limits:
          memory: 4G

  nginx:
    restart: always
```

## Foydali komandalar

```bash
# Development
docker-compose up -d
docker-compose logs -f backend
docker-compose exec backend bash

# Migration
docker-compose exec backend alembic upgrade head
docker-compose exec backend alembic revision --autogenerate -m "description"

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Backup
docker-compose exec postgres pg_dump -U lms_user lms_db > backup_$(date +%Y%m%d).sql

# Restore
docker-compose exec -T postgres psql -U lms_user lms_db < backup.sql

# Tozalash
docker-compose down -v  # Volumes bilan
docker system prune -af
```

## Acceptance kriteriyalar

- [ ] `docker-compose up` komandasi bilan to'liq stack ishga tushadi
- [ ] Barcha servislar healthcheck'dan o'tadi
- [ ] Production build optimallashtirilgan (multi-stage)
- [ ] Non-root user ishlatiladi (security)
- [ ] Volumes orqali ma'lumotlar saqlanadi
- [ ] .env.example fayli mavjud va to'liq
- [ ] Environment variable'lar secret manager'dan olinadi (production)
- [ ] Logs JSON format'da yoziladi
- [ ] Resource limits production'da o'rnatiladi
