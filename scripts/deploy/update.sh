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

log "2/4 — Alembic migration (yangi build qilingan image bilan)..."
# MUHIM: kod image'ga bake qilingan (prod'da source volume yo'q). Shu sababli
# migration'ni ESKI ishlab turgan container'da `exec` qilish yangi migration'ni
# KO'RMAYDI. Yangi image'dan bir martalik `run --rm` container ishga tushiramiz —
# bu yangi migration fayllarni ko'radi va eski backend hali ishlab turibdi
# (zero-downtime: schema avval ko'chadi, keyin step 3 da yangi kod ishga tushadi).
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" run --rm --no-deps backend alembic upgrade head || {
  err "Migration xato. Eski versiyada qoldik."
}

log "3/4 — Servislarni yangilash (zero-downtime — rolling restart)..."
# Backend va frontend ni qayta yarating, infra (postgres/redis/minio) tegmaydi
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --no-deps --build backend frontend-user frontend-admin
# Egress (server-side recording worker) ishlab turishini ta'minlaymiz.
# livekit'ga tegmaymiz (jonli darsni uzmaslik uchun) — egress uning namespace'iga ulanadi.
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --no-deps egress 2>/dev/null || \
  log "  (egress hali sozlanmagan/ishga tushmadi — alohida tekshiring)"

log "4/4 — Eski image'larni tozalash..."
docker image prune -f --filter "label!=keep"

log "Holat:"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

log "TAYYOR."
