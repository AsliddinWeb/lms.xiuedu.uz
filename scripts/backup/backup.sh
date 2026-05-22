#!/usr/bin/env bash
# Phase 7f — Backup: pg_dump + MinIO mirror.
#
# Foydalanish:
#   ./scripts/backup/backup.sh                  # default — ./backups/<timestamp>/
#   BACKUP_DIR=/data/backups ./scripts/backup/backup.sh
#
# Cron uchun (har kuni 03:00):
#   0 3 * * * cd /opt/lms && ./scripts/backup/backup.sh >> /var/log/lms-backup.log 2>&1
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=${BACKUP_DIR:-./backups/$TIMESTAMP}
mkdir -p "$BACKUP_DIR"

POSTGRES_USER=${POSTGRES_USER:-lms}
POSTGRES_DB=${POSTGRES_DB:-lms_xiuedu}
PG_CONTAINER=${PG_CONTAINER:-lms_postgres}

MINIO_BUCKET=${MINIO_BUCKET:-lms-files}
MINIO_CONTAINER=${MINIO_CONTAINER:-lms_minio}
MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-minio_admin}
MINIO_SECRET_KEY=${MINIO_SECRET_KEY:-minio_dev_secret_at_least_32_chars}

echo "[backup] start: $TIMESTAMP → $BACKUP_DIR"

# ---------- 1. PostgreSQL dump ----------
echo "[backup] pg_dump $POSTGRES_DB ..."
docker exec "$PG_CONTAINER" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -F c -f /tmp/db.dump
docker cp "$PG_CONTAINER:/tmp/db.dump" "$BACKUP_DIR/postgres.dump"
docker exec "$PG_CONTAINER" rm /tmp/db.dump
PG_SIZE=$(du -h "$BACKUP_DIR/postgres.dump" | cut -f1)
echo "[backup] pg_dump OK ($PG_SIZE)"

# ---------- 2. MinIO bucket mirror ----------
echo "[backup] minio mirror $MINIO_BUCKET ..."
MC_TMP=$(mktemp -d)
trap 'rm -rf "$MC_TMP"' EXIT

# mc client via docker (alpine image, small)
docker run --rm --network host \
    -v "$BACKUP_DIR:/backup" \
    -v "$MC_TMP:/root/.mc" \
    minio/mc:latest sh -c "
        mc alias set local http://localhost:8212 $MINIO_ACCESS_KEY $MINIO_SECRET_KEY > /dev/null
        mc mirror --quiet local/$MINIO_BUCKET /backup/minio
    "
MINIO_SIZE=$(du -sh "$BACKUP_DIR/minio" 2>/dev/null | cut -f1 || echo "0")
echo "[backup] minio mirror OK ($MINIO_SIZE)"

# ---------- 3. Backup summary ----------
cat > "$BACKUP_DIR/manifest.txt" <<EOF
LMS XIU backup
Timestamp: $TIMESTAMP
PostgreSQL: $POSTGRES_DB ($PG_SIZE)
MinIO:      $MINIO_BUCKET ($MINIO_SIZE)
Host:       $(hostname)
EOF

echo "[backup] complete: $BACKUP_DIR"
echo "[backup] manifest: $BACKUP_DIR/manifest.txt"

# ---------- 4. Retention (oxirgi 14 kunni saqlash) ----------
if [ -n "${BACKUP_DIR%/*}" ] && [ -d "${BACKUP_DIR%/*}" ]; then
    cd "${BACKUP_DIR%/*}"
    ls -dt 20* 2>/dev/null | tail -n +15 | xargs -r rm -rf
    echo "[backup] retention: kept 14 most recent"
fi
