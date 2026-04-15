#!/bin/bash
#
# deploy.sh — Быстрое развертывание приложения "Энциклопедия камней"
# Использование: ./deploy.sh [install|update|restart|status|uninstall]
#

set -e  # Останавливаемся при ошибке

# === Настройки ===
APP_NAME="gems_app"
APP_DIR="/opt/gem-app"
VENV_DIR="$APP_DIR/venv"
USER="root"
GROUP="root"
PORT=5000
HOST="0.0.0.0"
LOG_FILE="$APP_DIR/logs/app.log"
PID_FILE="$APP_DIR/app.pid"
SYSTEMD_SERVICE="/etc/systemd/system/$APP_NAME.service"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# === Функции ===
log_info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Скрипт требует прав root (sudo)"
        exit 1
    fi
}

create_user() {
    if ! id "$USER" &>/dev/null; then
        log_info "Создаю пользователя $USER..."
        useradd -r -s /bin/bash -d "$APP_DIR" -m "$USER"
    else
        log_warn "Пользователь $USER уже существует"
    fi
    usermod -a -G "$GROUP" "$USER" 2>/dev/null || true
}

create_dirs() {
    log_info "Создаю директорию приложения: $APP_DIR"
    mkdir -p "$APP_DIR"/{static/{css,js,img},templates,uploads,logs}
    
    log_info "Настраиваю права доступа..."
    chown -R "$USER:$GROUP" "$APP_DIR"
    chmod 755 "$APP_DIR"
    chmod 700 "$APP_DIR/uploads" "$APP_DIR/logs"
}

setup_venv() {
    log_info "Настраиваю Python virtualenv..."
    
    if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
        python3 -m venv "$VENV_DIR"
    fi
    
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r "$APP_DIR/requirements.txt"
    
    log_info "✓ Virtualenv готов"
}

init_database() {
    log_info "Инициализация базы данных..."
    source "$VENV_DIR/bin/activate"
    cd "$APP_DIR"
    
    python3 -c "
from app import app, create_tables
import os
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
create_tables(app)
print('✓ База данных создана')
"
}

create_systemd_service() {
    log_info "Создаю systemd service..."
    
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

# Security hardening
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    log_info "✓ Service создан: $APP_NAME.service"
}

enable_autostart() {
    log_info "Включаю автозапуск..."
    systemctl enable "$APP_NAME.service"
    systemctl start "$APP_NAME.service"
    sleep 2
    show_status
}

show_status() {
    echo ""
    log_info "Статус приложения:"
    if systemctl is-active --quiet "$APP_NAME.service"; then
        echo -e "  ${GREEN}● Активен${NC} (порт $PORT)"
    else
        echo -e "  ${RED}○ Неактивен${NC}"
    fi
    echo "  Лог: $LOG_FILE"
    echo "  Доступ: http://$(hostname -I | awk '{print $1}'):$PORT"
    echo ""
}

do_install() {
    log_info "=== Начало установки $APP_NAME ==="
    
    check_root
    create_user
    create_dirs
    
    log_info "Копирую файлы проекта..."
    # Копируем всё, кроме венв и __pycache__
    cp -r ./* "$APP_DIR/" 2>/dev/null || true
    cp -r ./.[^.]* "$APP_DIR/" 2>/dev/null || true
    chown -R "$USER:$GROUP" "$APP_DIR"
    
    setup_venv
    init_database
    create_systemd_service
    enable_autostart
    
    log_info "=== Установка завершена ==="
    echo ""
    echo "Доступ к приложению: http://$(hostname -I | awk '{print $1}'):$PORT"
    echo "Админ-панель: /admin/login (логин: admin, пароль: museum2026)"
    echo ""
    log_warn "Пароль администратора указан в app.py (ADMIN_CREDENTIALS)"
}

do_update() {
    log_info "=== Обновление приложения ==="
    
    if [[ ! -d "$APP_DIR" ]]; then
        log_error "Приложение не установлено. Используйте: $0 install"
        exit 1
    fi
    
    log_info "Останавливаю сервис..."
    systemctl stop "$APP_NAME.service" 2>/dev/null || true
    
    log_info "Обновляю файлы..."
    cp -r ./* "$APP_DIR/" 2>/dev/null || true
    chown -R "$USER:$GROUP" "$APP_DIR"
    
    log_info "Обновляю зависимости..."
    source "$VENV_DIR/bin/activate"
    pip install --upgrade -r "$APP_DIR/requirements.txt"
    
    log_info "Перезапускаю сервис..."
    systemctl start "$APP_NAME.service"
    
    show_status
    log_info "✓ Обновление завершено"
}

do_restart() {
    log_info "Перезапуск сервиса..."
    systemctl restart "$APP_NAME.service"
    sleep 2
    show_status
}

do_stop() {
    log_info "Остановка сервиса..."
    systemctl stop "$APP_NAME.service"
    show_status
}

do_start() {
    log_info "Запуск сервиса..."
    systemctl start "$APP_NAME.service"
    sleep 2
    show_status
}

do_uninstall() {
    log_warn "=== УДАЛЕНИЕ ПРИЛОЖЕНИЯ ==="
    read -p "Вы уверены? Все данные будут удалены! (yes/no): " CONFIRM
    if [[ "$CONFIRM" != "yes" ]]; then
        log_info "Отменено"
        exit 0
    fi
    
    log_info "Останавливаю сервис..."
    systemctl stop "$APP_NAME.service" 2>/dev/null || true
    systemctl disable "$APP_NAME.service" 2>/dev/null || true
    rm -f "$SYSTEMD_SERVICE"
    systemctl daemon-reload
    
    log_info "Удаляю файлы приложения..."
    rm -rf "$APP_DIR"
    
    log_info "Удаляю пользователя $USER..."
    userdel -r "$USER" 2>/dev/null || true
    
    log_info "✓ Приложение удалено"
}

do_logs() {
    if [[ -f "$LOG_FILE" ]]; then
        tail -n 100 -f "$LOG_FILE"
    else
        log_error "Лог-файл не найден: $LOG_FILE"
    fi
}

do_backup() {
    BACKUP_DIR="/backup/${APP_NAME}_$(date +%Y%m%d_%H%M%S)"
    log_info "Создаю бэкап: $BACKUP_DIR"
    
    mkdir -p "$BACKUP_DIR"
    cp -r "$APP_DIR/uploads" "$BACKUP_DIR/"
    cp "$APP_DIR/gems.db" "$BACKUP_DIR/" 2>/dev/null || true
    
    tar -czf "${BACKUP_DIR}.tar.gz" -C "$(dirname "$BACKUP_DIR")" "$(basename "$BACKUP_DIR")"
    rm -rf "$BACKUP_DIR"
    
    log_info "✓ Бэкап создан: ${BACKUP_DIR}.tar.gz"
}

# === Главная ===
case "${1:-install}" in
    install)
        do_install
        ;;
    update)
        do_update
        ;;
    restart)
        do_restart
        ;;
    start)
        do_start
        ;;
    stop)
        do_stop
        ;;
    status)
        show_status
        ;;
    logs)
        do_logs
        ;;
    backup)
        do_backup
        ;;
    uninstall)
        do_uninstall
        ;;
    *)
        echo "Использование: $0 {install|update|restart|start|stop|status|logs|backup|uninstall}"
        echo ""
        echo "Команды:"
        echo "  install   — полная установка приложения (требует root)"
        echo "  update    — обновление файлов и зависимостей"
        echo "  restart   — перезапуск сервиса"
        echo "  start/stop — управление сервисом"
        echo "  status    — показать статус приложения"
        echo "  logs      — просмотр логов в реальном времени"
        echo "  backup    — создать бэкап БД и загруженных файлов"
        echo "  uninstall — полное удаление приложения"
        exit 1
        ;;
esac