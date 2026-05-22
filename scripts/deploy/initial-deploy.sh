#!/usr/bin/env bash
# ============================================================
# XIU LMS — initial production deploy
#
# Birinchi marta yangi server'da ishga tushirish.
# Project root'idan ishga tushiring:
#     bash scripts/deploy/initial-deploy.sh
#
# Talab qilinadigan oldindan tayyorlik:
#   1. Ubuntu 22.04 + docker + docker compose v2 o'rnatilgan
#   2. .env.production fayli to'ldirilgan (root va backend/)
#   3. Tashqi nginx domain -> port forward sozlangan
# ============================================================
set -euo pipefail

# --- Color helpers ---
log()   { echo -e "\033[1;36m[deploy]\033[0m $*"; }
warn()  { echo -e "\033[1;33m[deploy]\033[0m $*"; }
err()   { echo -e "\033[1;31m[deploy]\033[0m $*" >&2; exit 1; }

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"

# --- Preflight ---
[ -f "$COMPOSE_FILE" ] || err "$COMPOSE_FILE topilmadi. Project root'idan ishga tushiring."
[ -f "$ENV_FILE" ] || err "$ENV_FILE topilmadi. .env.production.example'dan ko'chiring va to'ldiring."
[ -f "backend/.env.production" ] || err "backend/.env.production topilmadi."

# Docker compose v2 tekshiruvi
docker compose version >/dev/null 2>&1 || err "docker compose v2 o'rnatilmagan."

log "1/6 — Eski konteynerlarni to'xtatish (agar bo'lsa)..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down --remove-orphans || true

log "2/6 — Image'larni build qilish (5-15 daqiqa)..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build --pull

log "3/6 — Infra servislarini boshlash (postgres/redis/minio/livekit)..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d postgres redis minio livekit

log "   Healthcheck'larni kutmoqda (~30s)..."
sleep 30

# Postgres tayyor ekanligini tekshirish
for i in {1..20}; do
  if docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T postgres pg_isready -U "$(grep '^POSTGRES_USER=' "$ENV_FILE" | cut -d= -f2)" >/dev/null 2>&1; then
    log "   postgres tayyor"
    break
  fi
  [ "$i" -eq 20 ] && err "postgres healthcheck o'tmadi"
  sleep 2
done

log "4/6 — Backend image'ni boshlash + Alembic migration..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d backend
sleep 5
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T backend alembic upgrade head

log "5/6 — Boshlang'ich seed (rollar, ruxsatlar, demo akkauntlar, badge katalog)..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T backend python -m app.db.seed || {
  warn "Seed jarayonida xatolik (akkauntlar oldindan mavjud bo'lishi mumkin). Davom etilmoqda."
}

log "6/6 — Frontend (user + admin) build va boshlash..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d frontend-user frontend-admin

log "Holat:"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

log "TAYYOR. Portlar:"
echo "  - Backend API:    http://server:$(grep '^BACKEND_PORT=' "$ENV_FILE" | cut -d= -f2)/api/v1/health"
echo "  - Frontend user:  http://server:$(grep '^FRONTEND_USER_PORT=' "$ENV_FILE" | cut -d= -f2)/health"
echo "  - Frontend admin: http://server:$(grep '^FRONTEND_ADMIN_PORT=' "$ENV_FILE" | cut -d= -f2)/health"
echo "  - MinIO console:  http://server:$(grep '^MINIO_CONSOLE_PORT=' "$ENV_FILE" | cut -d= -f2)/"
