#!/usr/bin/env bash
# ============================================================
# XIU LMS — update deploy (yangi versiyaga o'tkazish)
#
# Foydalanish (server'da, project root'dan):
#     git pull
#     bash scripts/deploy/update.sh
# ============================================================
set -euo pipefail

log()  { echo -e "\033[1;36m[update]\033[0m $*"; }
err()  { echo -e "\033[1;31m[update]\033[0m $*" >&2; exit 1; }

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"

[ -f "$COMPOSE_FILE" ] || err "$COMPOSE_FILE topilmadi"
[ -f "$ENV_FILE" ] || err "$ENV_FILE topilmadi"

log "1/4 — Image'larni qayta build qilish..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build --pull

log "2/4 — Alembic migration (backend ishlamoqda)..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T backend alembic upgrade head || {
  err "Migration xato. Eski versiyada qoldik."
}

log "3/4 — Servislarni yangilash (zero-downtime — rolling restart)..."
# Backend va frontend ni qayta yarating, infra (postgres/redis/minio) tegmaydi
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --no-deps --build backend frontend-user frontend-admin

log "4/4 — Eski image'larni tozalash..."
docker image prune -f --filter "label!=keep"

log "Holat:"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

log "TAYYOR."
