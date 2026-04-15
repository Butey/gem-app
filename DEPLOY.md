# Энциклопедия камней — Развёртывание
## Версия 1.0.2

---

## 🚀 Автоматическая установка

### Требования
- Сервер с **Linux** (Debian/Ubuntu/CentOS)
- **Python 3.9+**
- **root** или **sudo** доступ
- **500 МБ** свободного места
- Доступ к порту **5000**

---

### Шаг 1: Подготовка архива

**Локально:**
```bash
# Архив уже создан: /opt/gems_app_v1.0.1_deploy.tar.gz (49 МБ)
```

**Копирование на сервер:**
```bash
# Замените user и IP на ваши
scp /opt/gems_app_v1.0.1_deploy.tar.gz user@192.168.1.100:/opt/
```

**Или через wget/curl:**
```bash
# Если архив доступен по HTTP
wget http://your-server.com/gems_app_v1.0.1_deploy.tar.gz -O /opt/gems_app_v1.0.1_deploy.tar.gz
```

---

### Шаг 2: Распаковка

```bash
cd /opt
tar -xzf gems_app_v1.0.0-beta_deploy.tar.gz
cd gems_app

# Проверка файлов
ls -la
# Должны быть: app.py, install_gems_app.sh, VERSION, backups/
```

---

### Шаг 3: Запуск автоматической установки

```bash
# Скрипт требует прав root
sudo ./install_gems_app.sh /opt/gems_app/backups/gems_app_v1.0.0-beta_20260322.tar.gz
```

**Что делает скрипт:**

| Шаг | Действие |
|-----|----------|
| 1 | Проверяет права root |
| 2 | Создаёт пользователя `gems` |
| 3 | Создаёт директории (`uploads`, `logs`, `backups`) |
| 4 | Распаковывает архив |
| 5 | Создаёт Python virtualenv |
| 6 | Устанавливает зависимости |
| 7 | Инициализирует базу данных |
| 8 | Создаёт systemd службу |
| 9 | Запускает приложение |

**Время установки:** ~2-5 минут (в зависимости от скорости интернета)

---

### Шаг 3.1: Альтернативная установка (из файлов)

Если файлы проекта уже скопированы в `/opt/gem-app`, используйте скрипт `setup_from_files.sh`:

```bash
cd /opt/gem-app
sudo ./setup_from_files.sh
```

**Что делает скрипт:**

| Шаг | Действие |
|-----|----------|
| 1 | Проверяет директорию и наличие `app.py` |
| 2 | Создаёт директории (`uploads`, `logs`, `backups`) |
| 3 | Создаёт Python virtualenv |
| 4 | Устанавливает зависимости |
| 5 | Инициализирует базу данных |
| 6 | Создаёт systemd службу |
| 7 | Запускает приложение |

**Переменные окружения для настройки:**
```bash
export ADMIN_USERNAME=myadmin
export ADMIN_PASSWORD=secret123
sudo ./setup_from_files.sh
```

---

### Шаг 4: Проверка установки

После установки скрипт покажет:

```
═══════════════════════════════════════════════════════
  ✓ Установка завершена успешно!
═══════════════════════════════════════════════════════

📌 Информация:
  Версия: 1.0.0-beta
  Порт: 5000
  Директория: /opt/gems_app

🌐 Доступ к приложению:
  http://192.168.1.100:5000
  http://localhost:5000

🔐 Админ-панель:
  URL: /admin/login
  Логин: admin
  Пароль: museum2026
```

**Проверка статуса:**
```bash
sudo systemctl status gems_app.service
```

**Проверка в браузере:**
```
http://<IP-сервера>:5000/
```

---

### Шаг 5: Первая настройка

**1. Смените пароль администратора:**

```bash
sudo nano /opt/gems_app/app.py
```

Найдите строку:
```python
ADMIN_CREDENTIALS = {
    'username': 'admin',
    'password': 'museum2026'  # ← Замените на свой пароль
}
```

Перезапустите сервис:
```bash
sudo systemctl restart gems_app.service
```

**2. Настройте firewall (если нужен):**

```bash
# UFW (Ubuntu)
sudo ufw allow 5000/tcp
sudo ufw reload

# firewalld (CentOS)
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

**3. Настройте reverse proxy (опционально):**

Для доступа через домен с HTTPS настройте nginx:

```bash
sudo nano /etc/nginx/sites-available/gems_app
```

```nginx
server {
    listen 80;
    server_name gems.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/gems_app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🔧 Управление после установки

### Статус
```bash
sudo systemctl status gems_app.service
```

### Перезапуск
```bash
sudo systemctl restart gems_app.service
```

### Остановка/Запуск
```bash
sudo systemctl stop gems_app.service
sudo systemctl start gems_app.service
```

### Логи
```bash
# Журнал systemd
sudo journalctl -u gems_app.service -f

# Файл логов приложения
sudo tail -f /opt/gems_app/logs/app.log
```

### Обновление
```bash
cd /opt/gems_app
sudo ./deploy.sh update
```

### Бэкап
```bash
cd /opt/gems_app
./backup.sh

# Бэкап будет в: /opt/gems_app/backups/
```

---

## 🆘 Troubleshooting

### Приложение недоступно

```bash
# Проверка статуса
sudo systemctl status gems_app.service

# Проверка логов
sudo journalctl -u gems_app.service --no-pager -n 50

# Проверка порта
sudo netstat -tlnp | grep 5000
```

### Ошибка при установке

```bash
# Проверка прав
ls -la /opt/gems_app/

# Проверка Python
python3 --version
which python3

# Переустановка зависимостей
cd /opt/gems_app
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

### Сброс установки

```bash
# Остановка сервиса
sudo systemctl stop gems_app.service
sudo systemctl disable gems_app.service

# Удаление
sudo rm -rf /opt/gems_app
sudo rm /etc/systemd/system/gems_app.service
sudo systemctl daemon-reload

# Удаление пользователя (опционально)
sudo userdel -r gems
```

---

## 📦 Структура после установки

```
/opt/gems_app/
├── app.py                    # Основное приложение
├── models.py                 # Модели данных
├── database.py               # Работа с БД
├── config.py                 # Конфигурация
├── gems.db                   # SQLite база данных
├── VERSION                   # Версия приложения
├── install_gems_app.sh       # Скрипт установки
├── deploy.sh                 # Скрипт управления
├── backup.sh                 # Скрипт бэкапов
├── templates/                # HTML шаблоны
├── static/
│   ├── css/                  # Стили
│   └── js/                   # Скрипты
├── uploads/                  # Загруженные изображения
├── logs/
│   └── app.log               # Логи приложения
├── backups/                  # Резервные копии
├── temp/                     # Временные файлы
└── venv/                     # Python virtualenv
```

---

## 🔐 Безопасность

1. **Смените пароль администратора** сразу после установки
2. **Настройте firewall** — откройте только порт 5000
3. **Используйте HTTPS** через nginx reverse proxy
4. **Регулярно делайте бэкапы** — минимум раз в неделю
5. **Обновляйте зависимости** — проверяйте `requirements.txt`

---

### Переменные окружения (ENV)

Вместо хранения учётных данных в коде используйте **переменные окружения**.

#### Настройка

**Вариант 1 — через systemd:**

Отредактируйте файл службы:
```bash
sudo nano /etc/systemd/system/gems_app.service
```

Добавьте строки в секцию `[Service]`:
```ini
[Service]
# ... существующие строки ...
Environment="ADMIN_USERNAME=myuser"
Environment="ADMIN_PASSWORD=secret123"
```

Перезапустите сервис:
```bash
sudo systemctl daemon-reload
sudo systemctl restart gems_app.service
```

**Вариант 2 — через командную строку:**
```bash
export ADMIN_USERNAME=myuser
export ADMIN_PASSWORD=secret123
sudo systemctl restart gems_app.service
```

#### Доступные переменные

| Переменная | По умолчанию | Описание |
|-----------|-------------|----------|
| `ADMIN_USERNAME` | `admin` | Логин админ-панели |
| `ADMIN_PASSWORD` | `museum2026` | Пароль админ-панели |
| `SECRET_KEY` | `dev-key-change-in-prod` | Ключ сессий Flask |

#### Проверка

```bash
# Проверить текущие значения
systemctl show gems_app.service | grep Environment

# Протестировать вход
curl -I http://localhost:5000/admin/login
```

⚠️ **В production обязательно смените `SECRET_KEY` и админ-пароль!**

---

## 📞 Поддержка

- **Документация:** `/opt/gems_app/DEPLOY.md`
- **CHANGELOG:** `/opt/gems_app/CHANGELOG.md`
- **Логи:** `sudo journalctl -u gems_app.service`
- **Версия:** `cat /opt/gems_app/VERSION`

---

**Версия:** 1.0.1  
**Дата обновления:** 2026-03-22

### Требования
- Python 3.9+
- systemd
- root/sudo доступ

### Шаг 1: Подготовка

```bash
# Создание пользователя
sudo useradd -r -s /bin/bash -d /opt/gems_app -m gems

# Установка зависимостей
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
```

### Шаг 2: Установка приложения

```bash
cd /opt/gems_app

# Создание virtualenv
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Инициализация БД
python init_db.py

# Выход из virtualenv
deactivate
```

### Шаг 3: Настройка systemd

```bash
sudo nano /etc/systemd/system/gems_app.service
```

Содержимое:
```ini
[Unit]
Description=Gems Encyclopedia App
After=network.target

[Service]
Type=simple
User=gems
Group=gems
WorkingDirectory=/opt/gems_app
Environment="PATH=/opt/gems_app/venv/bin"
ExecStart=/opt/gems_app/venv/bin/gunicorn --workers 4 --bind 0.0.0.0:5000 app:app
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### Шаг 4: Запуск

```bash
sudo systemctl daemon-reload
sudo systemctl enable gems_app.service
sudo systemctl start gems_app.service
sudo systemctl status gems_app.service
```

---

## 🔐 Доступы

**Админ-панель:**
- URL: `/admin/login`
- Логин: `admin`
- Пароль: `museum2026`

⚠️ **Смените пароль после установки!**

### Настройка отладки поиска

В админ-панели доступна страница настроек `/admin/settings`:

1. Войдите в админ-панель
2. Нажмите **⚙ Настройки**
3. Включите галочку «Включить отладку поиска»
4. Сохраните настройки

После включения:
- В админ-панели появится баннер со ссылкой на отладку
- В футере сайта появится ссылка «Отладка поиска»
- Страница `/debug/search?q=запрос` покажет SQL-запрос и сниппеты

---

## 📝 Управление

### Статус
```bash
sudo systemctl status gems_app.service
```

### Перезапуск
```bash
sudo systemctl restart gems_app.service
```

### Остановка
```bash
sudo systemctl stop gems_app.service
```

### Логи
```bash
# Через journalctl
sudo journalctl -u gems_app.service -f

# Файл логов
tail -f /opt/gems_app/logs/app.log
```

---

## 💾 Бэкап

### Создание бэкапа
```bash
cd /opt/gems_app
./backup.sh
```

### Восстановление
```bash
cd /opt/gems_app
tar -xzf backups/gems_app_backup_*.tar.gz
```

---

## 📊 Мониторинг

### Проверка процесса
```bash
ps aux | grep gunicorn
cat /opt/gems_app/app.pid
```

### Проверка порта
```bash
netstat -tlnp | grep 5000
ss -tlnp | grep 5000
```

### Проверка БД
```bash
cd /opt/gems_app
sqlite3 gems.db "SELECT COUNT(*) FROM gems;"
```

---

## 🆘 Troubleshooting

### Приложение не запускается

```bash
# Проверка логов
sudo journalctl -u gems_app.service --no-pager -n 50

# Проверка прав
ls -la /opt/gems_app/
ls -la /opt/gems_app/logs/
ls -la /opt/gems_app/uploads/

# Проверка БД
sqlite3 /opt/gems_app/gems.db ".tables"
```

### Ошибка "Address already in use"

```bash
# Найти процесс на порту 5000
lsof -i :5000

# Убить процесс
kill -9 <PID>

# Перезапустить сервис
sudo systemctl restart gems_app.service
```

### Проблемы с правами доступа

```bash
sudo chown -R gems:gems /opt/gems_app
sudo chmod 755 /opt/gems_app
sudo chmod 700 /opt/gems_app/uploads /opt/gems_app/logs
```

---

## 📞 Поддержка

- Логи: `/opt/gems_app/logs/app.log`
- Версия: `cat /opt/gems_app/VERSION`
- CHANGELOG: `/opt/gems_app/CHANGELOG.md`

---

**Версия:** 1.0.0-beta  
**Дата:** 2026-03-22
