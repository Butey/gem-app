#!/bin/bash
#
# install_gems_app.sh — Автоматическая установка "Энциклопедия камней" на новый сервер
# Версия: 1.0.1
#
# Использование: ./install_gems_app.sh [путь_к_архиву]
# Пример: ./install_gems_app.sh /opt/gems_app_v1.0.1.tar.gz
#

set -e  # Останавливаемся при ошибке

# === Настройки ===
APP_NAME="gems_app"
APP_DIR="/opt/$APP_NAME"
VENV_DIR="$APP_DIR/venv"
USER="gems"
GROUP="gems"
PORT=5000
HOST="0.0.0.0"
LOG_FILE="$APP_DIR/logs/app.log"
PID_FILE="$APP_DIR/app.pid"
SYSTEMD_SERVICE="/etc/systemd/system/$APP_NAME.service"
ADMIN_PASSWORD="museum2026"

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

check_archive() {
    if [[ -z "$1" ]]; then
        log_error "Не указан путь к архиву"
        echo "Использование: $0 <путь_к_архиву>"
        echo "Пример: $0 /opt/gems_app_v1.0.0-beta.tar.gz"
        exit 1
    fi
    
    if [[ ! -f "$1" ]]; then
        log_error "Архив не найден: $1"
        exit 1
    fi
    
    ARCHIVE_PATH="$1"
    log_info "Архив найден: $ARCHIVE_PATH"
}

create_user() {
    log_step "Создание пользователя $USER..."
    
    if ! id "$USER" &>/dev/null; then
        useradd -r -s /bin/bash -d "$APP_DIR" -m "$USER"
        log_info "Пользователь $USER создан"
    else
        log_warn "Пользователь $USER уже существует"
    fi
}

create_dirs() {
    log_step "Создание директорий..."
    
    mkdir -p "$APP_DIR"/{static/{css,js},templates,uploads,logs,backups,temp}
    
    chown -R "$USER:$GROUP" "$APP_DIR"
    chmod 755 "$APP_DIR"
    chmod 700 "$APP_DIR/uploads" "$APP_DIR/logs"
    
    log_info "Директории созданы"
}

extract_archive() {
    log_step "Распаковка архива..."

    tar -xzf "$ARCHIVE_PATH" -C "$APP_DIR" --exclude='venv' --exclude='__pycache__' --exclude='.cache' --exclude='logs/*.log'
    
    # Если передан полный deploy архив, ищем бэкап внутри
    if [[ -f "$APP_DIR/backups/gems_app_v1.0.1_*.tar.gz" ]]; then
        BACKUP_FILE=$(ls "$APP_DIR/backups/gems_app_v1.0.1_"*.tar.gz 2>/dev/null | head -1)
        if [[ -n "$BACKUP_FILE" ]]; then
            tar -xzf "$BACKUP_FILE" -C "$APP_DIR" --exclude='venv' --exclude='__pycache__'
        fi
    fi
    
    chown -R "$USER:$GROUP" "$APP_DIR"
    
    log_info "Файлы распакованы"
}

setup_venv() {
    log_step "Настройка Python virtualenv..."
    
    if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
        python3 -m venv "$VENV_DIR"
    fi
    
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    
    if [[ -f "$APP_DIR/requirements.txt" ]]; then
        pip install -r "$APP_DIR/requirements.txt"
    else
        pip install flask flask-sqlalchemy gunicorn
    fi
    
    deactivate
    log_info "✓ Virtualenv готов"
}

init_database() {
    log_step "Инициализация базы данных..."
    
    source "$VENV_DIR/bin/activate"
    cd "$APP_DIR"
    
    "$VENV_DIR/bin/python" init_db.py
    
    deactivate
    log_info "✓ База данных создана"
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
ExecStart=$VENV_DIR/bin/gunicorn --workers 4 --bind $HOST:$PORT --access-logfile $LOG_FILE --error-logfile $LOG_FILE --pid $PID_FILE app:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable "$APP_NAME.service"
    
    log_info "✓ Service создан: $APP_NAME.service"
}

start_service() {
    log_step "Запуск приложения..."
    
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
    echo ""
    echo "═══════════════════════════════════════════════════════"
    echo -e "  ${GREEN}✓ Установка завершена успешно!${NC}"
    echo "═══════════════════════════════════════════════════════"
    echo ""
    echo "📌 Информация:"
    echo "  Версия: 1.0.1"
    echo "  Порт: $PORT"
    echo "  Директория: $APP_DIR"
    echo ""
    echo "🌐 Доступ к приложению:"
    echo "  http://$(hostname -I | awk '{print $1}'):$PORT"
    echo "  http://localhost:$PORT"
    echo ""
    echo "🔐 Админ-панель:"
    echo "  URL: /admin/login"
    echo "  Логин: admin"
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
    echo "  ├── app.py              # Приложение"
    echo "  ├── models.py           # Модели"
    echo "  ├── database.py         # БД"
    echo "  ├── config.py           # Конфигурация"
    echo "  ├── gems.db             # База данных"
    echo "  ├── templates/          # Шаблоны"
    echo "  ├── static/             # CSS, JS"
    echo "  ├── uploads/            # Загрузки"
    echo "  ├── logs/               # Логи"
    echo "  ├── backups/            # Бэкапы"
    echo "  └── venv/               # Virtualenv"
    echo ""
    echo "═══════════════════════════════════════════════════════"
}

# === Главная ===
main() {
    echo ""
    echo "═══════════════════════════════════════════════════════"
    echo "  Энциклопедия камней — Установка"
    echo "  Версия: 1.0.0-beta"
    echo "═══════════════════════════════════════════════════════"
    echo ""
    
    check_root
    check_archive "$1"
    create_user
    create_dirs
    extract_archive
    setup_venv
    init_database
    create_systemd_service
    start_service
    show_info
}

main "$@"
