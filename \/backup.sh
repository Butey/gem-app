#!/bin/bash
#
# backup.sh — Создание бэкапа файлов и БД
# Использование: ./backup.sh [файл_или_папка]
#

set -e

BACKUP_DIR="/opt/gems_app/backups"
DATE=$(date +%Y%m%d_%H%M%S)
CHANGELOG="/opt/gems_app/CHANGELOG.md"

log_change() {
    local description="$1"
    local date=$(date +%Y-%m-%d)
    
    # Если сегодня ещё нет записей — добавляем заголовок
    if ! grep -q "## \[$date\]" "$CHANGELOG" 2>/dev/null; then
        sed -i "/^---$/a\\n## [$date]\\n\\n### Изменения" "$CHANGELOG" 2>/dev/null || \
        echo -e "\n## [$date]\n\n### Изменения" >> "$CHANGELOG"
    fi
    
    # Добавляем запись
    echo "- $description" >> "$CHANGELOG"
    echo "✓ Запись добавлена в CHANGELOG.md"
}

create_backup() {
    local target="$1"
    
    if [[ ! -e "$target" ]]; then
        echo "❌ Файл/папка не найдены: $target"
        exit 1
    fi
    
    local filename=$(basename "$target")
    local backup_name="${filename}.${DATE}.bak"
    
    if [[ -d "$target" ]]; then
        tar -czf "$BACKUP_DIR/${filename}.${DATE}.tar.gz" -C "$(dirname "$target")" "$filename"
        echo "✓ Бэкап создан: $BACKUP_DIR/${filename}.${DATE}.tar.gz"
    else
        cp "$target" "$BACKUP_DIR/$backup_name"
        echo "✓ Бэкап создан: $BACKUP_DIR/$backup_name"
    fi
}

# === Главная ===
case "${1:-}" in
    --log)
        shift
        log_change "$*"
        ;;
    --list)
        echo "📦 Бэкапы в $BACKUP_DIR:"
        ls -lht "$BACKUP_DIR" 2>/dev/null || echo "  (пусто)"
        ;;
    --cleanup)
        echo "🗑️ Удаление бэкапов старше 30 дней..."
        find "$BACKUP_DIR" -type f -mtime +30 -delete
        echo "✓ Очистка завершена"
        ;;
    "")
        echo "Использование: $0 <файл|папка> [--log 'описание']"
        echo ""
        echo "Опции:"
        echo "  <файл>       — создать бэкап файла"
        echo "  --log 'текст' — добавить запись в CHANGELOG"
        echo "  --list       — показать все бэкапы"
        echo "  --cleanup    — удалить старые бэкапы (>30 дней)"
        echo ""
        echo "Примеры:"
        echo "  $0 admin.py --log 'Исправлен пароль администратора'"
        echo "  $0 uploads --log 'Бэкап загрузок перед обновлением'"
        ;;
    *)
        create_backup "$1"
        if [[ -n "$2" && "$2" == "--log" ]]; then
            log_change "$3"
        fi
        ;;
esac
