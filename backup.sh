#!/bin/bash
# Бэкап PostgreSQL для UberGooranda
# Запускается cron'ом раз в сутки

set -euo pipefail   # остановиться при любой ошибке

# ─── Настройки ───
PROJECT_DIR="/opt/ubergooranda-server"
BACKUP_DIR="/opt/backups/postgres"
DB_NAME="ubergooranda"
DB_USER="app"
KEEP_DAYS=30        # сколько дней хранить локально

DATE=$(date +%Y-%m-%d_%H-%M)
FILENAME="ubergooranda_${DATE}.sql.gz"
FILEPATH="$BACKUP_DIR/$FILENAME"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') — старт бэкапа ==="

# ─── Создать директорию, если её нет ───
mkdir -p "$BACKUP_DIR"

# ─── Дамп БД ───
cd "$PROJECT_DIR"

if ! docker compose exec -T db pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$FILEPATH"; then
    echo "❌ ОШИБКА: pg_dump упал"
    rm -f "$FILEPATH"
    exit 1
fi

# ─── Проверить размер ───
SIZE=$(stat -c%s "$FILEPATH" 2>/dev/null || echo 0)
if [ "$SIZE" -lt 1024 ]; then
    echo "❌ ОШИБКА: файл слишком маленький ($SIZE байт) — дамп пустой?"
    rm -f "$FILEPATH"
    exit 1
fi

SIZE_KB=$(awk "BEGIN {printf \"%.0f\", $SIZE/1024}")
echo "✅ Бэкап создан: $FILENAME ($SIZE_KB КБ)"

# ─── Удалить старые бэкапы ───
echo "Удаляю бэкапы старше $KEEP_DAYS дней..."
find "$BACKUP_DIR" -name "ubergooranda_*.sql.gz" -mtime +$KEEP_DAYS -delete

echo "=== $(date '+%Y-%m-%d %H:%M:%S') — бэкап завершён ==="
echo ""
