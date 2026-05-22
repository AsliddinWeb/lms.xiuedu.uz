#!/usr/bin/env bash
# Dev muhitni birinchi marta ko'tarish

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "→ .env fayllarni yaratish (mavjud bo'lmasa)"
[[ -f .env ]] || cp .env.example .env
[[ -f backend/.env ]] || cp backend/.env.example backend/.env
[[ -f frontend/.env ]] || cp frontend/.env.example frontend/.env

echo "→ Infratuzilma servislarini ko'tarish (postgres, redis, minio, mailhog)"
docker compose up -d postgres redis minio mailhog

echo "→ Backend dependencies"
cd "$ROOT/backend"
if command -v uv >/dev/null 2>&1; then
    uv pip install --system -e ".[dev]"
else
    pip install -e ".[dev]"
fi

echo "→ Alembic migration (boshlang'ich)"
# Phase 0: hali model yo'q. Phase 1 da: alembic upgrade head
echo "  (Phase 0 — modellar Phase 1 da qo'shiladi)"

echo "→ Frontend dependencies"
cd "$ROOT/frontend"
if command -v pnpm >/dev/null 2>&1; then
    pnpm install
else
    echo "  pnpm topilmadi. O'rnating: corepack enable && corepack prepare pnpm@latest --activate"
fi

echo
echo "Dev setup tayyor."
echo
echo "Backend:  cd backend && uvicorn app.main:app --reload --port 8200"
echo "User UI:  cd frontend && pnpm dev:user   → http://localhost:8201"
echo "Admin UI: cd frontend && pnpm dev:admin  → http://localhost:8203"
echo "MinIO:    http://localhost:8213          (login: minio_admin / minio_dev_password)"
echo "Mailhog:  http://localhost:8215"
