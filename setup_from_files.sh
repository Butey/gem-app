#!/bin/bash
#
# setup_from_files.sh — Развертывание приложения из скопированных файлов
# Использование: ./setup_from_files.sh [путь_к_директории]
# Пример: ./setup_from_files.sh /opt/gem-app
#
# Скрипт создаёт virtualenv, устанавливает зависимости, инициализирует БД
# и настраивает systemd-службу для уже скопированных файлов приложения.
#

set -e  # Останавливаемся при ошибке

# === Настройки ===
APP_NAME="gems_app"
APP_DIR="${1:-/opt/gem-app}"
VENV_DIR="$APP_DIR/venv"
USER="root"
GROUP="root"
PORT=5000
HOST="0.0.0.0"
LOG_FILE="$APP_DIR/logs/app.log"
PID_FILE="$APP_DIR/app.pid"
SYSTEMD_SERVICE="/etc/systemd/system/$APP_NAME.service"
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-museum2026}"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# === Функции ===
log_info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()    { echo -e "${BLUE}[STEP]${NC} $1"; }

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Скрипт требует прав root (sudo)"
        exit 1
    fi
}

check_app_dir() {
    if [[ ! -d "$APP_DIR" ]]; then
        log_error "Директория не найдена: $APP_DIR"
        exit 1
    fi

    if [[ ! -f "$APP_DIR/app.py" ]]; then
        log_error "app.py не найден в $APP_DIR"
        exit 1
    fi

    log_info "Директория приложения проверена: $APP_DIR"
}

create_dirs() {
    log_step "Создание директорий..."

    mkdir -p "$APP_DIR"/{static/{css,js,img},templates,uploads,logs,backups}

    chmod 755 "$APP_DIR"
    chmod 700 "$APP_DIR/uploads" "$APP_DIR/logs"

    log_info "Директории созданы/проверены"
}

setup_venv() {
    log_step "Настройка Python virtualenv..."

    if [[ -d "$VENV_DIR" ]]; then
        log_warn "Virtualenv уже существует, удаляю..."
        rm -rf "$VENV_DIR"
    fi

    python3 -m venv "$VENV_DIR"

    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip

    if [[ -f "$APP_DIR/requirements.txt" ]]; then
        pip install -r "$APP_DIR/requirements.txt"
    else
        log_warn "requirements.txt не найден, устанавливаю базовые пакеты"
        pip install flask flask-sqlalchemy gunicorn werkzeug
    fi

    # Добавляем gunicorn если его нет
    pip show gunicorn &>/dev/null || pip install gunicorn

    deactivate
    log_info "✓ Virtualenv создан"
}

init_database() {
    log_step "Инициализация базы данных..."

    source "$VENV_DIR/bin/activate"
    cd "$APP_DIR"

    # Создаём таблицы через database.py
    "$VENV_DIR/bin/python" -c "
from app import app
from database import create_tables
import os

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
create_tables(app)
print('✓ База данных создана')
"

    deactivate
    log_info "✓ База данных инициализирована"
}

create_systemd_service() {
    log_step "Создание systemd service..."

    cat > "$SYSTEMD_SERVICE" << EOF
[Unit]
Description=Gems Encyclopedia App
After=network.target

[Service]
Type=simple
User=$USER
Group=$GROUP
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
Environment="FLASK_ENV=production"
Environment="ADMIN_USERNAME=$ADMIN_USERNAME"
Environment="ADMIN_PASSWORD=$ADMIN_PASSWORD"
ExecStart=$VENV_DIR/bin/gunicorn --workers 4 --bind $HOST:$PORT --access-logfile $LOG_FILE --error-logfile $LOG_FILE --pid $PID_FILE app:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=on-failure
RestartSec=5

# Security hardening
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable "$APP_NAME.service"

    log_info "✓ Service создан: $SYSTEMD_SERVICE"
}

start_service() {
    log_step "Запуск приложения..."

    systemctl stop "$APP_NAME.service" 2>/dev/null || true
    sleep 1
    systemctl start "$APP_NAME.service"
    sleep 3

    if systemctl is-active --quiet "$APP_NAME.service"; then
        log_info "✓ Приложение запущено"
    else
        log_error "Не удалось запустить приложение"
        systemctl status "$APP_NAME.service" --no-pager
        exit 1
    fi
}

show_info() {
    local IP=$(hostname -I | awk '{print $1}')

    echo ""
    echo "═══════════════════════════════════════════════════════"
    echo -e "  ${GREEN}✓ Развертывание завершено успешно!${NC}"
    echo "═══════════════════════════════════════════════════════"
    echo ""
    echo "📌 Информация:"
    echo "  Приложение: $APP_NAME"
    echo "  Директория: $APP_DIR"
    echo "  Порт: $PORT"
    echo ""
    echo "🌐 Доступ к приложению:"
    echo "  http://$IP:$PORT"
    echo "  http://localhost:$PORT"
    echo ""
    echo "🔐 Админ-панель:"
    echo "  URL: /admin/login"
    echo "  Логин: $ADMIN_USERNAME"
    echo "  Пароль: $ADMIN_PASSWORD"
    echo ""
    echo "📝 Команды управления:"
    echo "  systemctl status $APP_NAME.service   # Статус"
    echo "  systemctl restart $APP_NAME.service  # Перезапуск"
    echo "  systemctl stop $APP_NAME.service     # Остановка"
    echo "  journalctl -u $APP_NAME.service -f   # Логи"
    echo ""
    echo "📁 Структура:"
    echo "  $APP_DIR"
    echo "  ├── app.py              # Приложение Flask"
    echo "  ├── models.py           # Модели ORM"
    echo "  ├── database.py         # Инициализация БД"
    echo "  ├── config.py           # Конфигурация"
    echo "  ├── requirements.txt    # Зависимости"
    echo "  ├── gems.db             # База данных SQLite"
    echo "  ├── templates/          # Jinja2 шаблоны"
    echo "  ├── static/             # CSS, JS, изображения"
    echo "  ├── uploads/            # Загруженные файлы"
    echo "  ├── logs/               # Логи приложения"
    echo "  ├── backups/            # Бэкапы"
    echo "  └── venv/               # Python virtualenv"
    echo ""
    echo "═══════════════════════════════════════════════════════"
}

# === Главная ===
main() {
    echo ""
    echo "═══════════════════════════════════════════════════════"
    echo "  Gems Encyclopedia App — Развертывание из файлов"
    echo "═══════════════════════════════════════════════════════"
    echo ""

    check_root
    check_app_dir
    create_dirs
    setup_venv
    init_database
    create_systemd_service
    start_service
    show_info
}

main "$@"
