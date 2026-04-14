# Gems Encyclopedia App - Context

## Описание проекта
**Gems Encyclopedia App** — каталог минералов с поиском и админ-панелью.

- **Версия:** 1.0.1
- **Фреймворк:** Flask 3.0.0
- **База данных:** SQLite (gems.db)
- **ORM:** SQLAlchemy 3.1.1

## Структура проекта
```
/opt/gems_app/
├── app.py                  # Главное приложение Flask
├── config.py               # Конфигурация (SECRET_KEY, DB URI, UPLOAD_FOLDER)
├── database.py             # Инициализация БД
├── models.py               # Модели ORM (Gem)
├── requirements.txt        # Зависимости Python
├── gems.db                 # База данных SQLite
├── uploads/                # Папка для загруженных изображений
├── templates/              # Jinja2 шаблоны
├── static/                 # CSS/JS/изображения
├── backup.sh               # Скрипт бэкапирования
├── deploy.sh               # Скрипт деплоя
├── install_gems_app.sh     # Скрипт установки
├── init_db.py              # Инициализация БД
├── import_sample_gems.py   # Импорт тестовых данных
└── CHANGELOG.md            # История изменений
```

## Доступ и запуск
- **Production:** http://<ip>:5000/
- **Запуск как systemd-служба:** `gems_app.service` (gunicorn с 4 workers)
- **Перезапуск:** `systemctl restart gems_app.service`

## Технологии
- **Backend:** Flask + SQLAlchemy
- **Frontend:** Jinja2 шаблоны, CSS (glassmorphism дизайн)
- **База данных:** SQLite
- **Деплой:** systemd + gunicorn

## Особенности
- Поиск минералов
- Админ-панель
- Загрузка изображений (макс. 16MB)
- Glassmorphism дизайн карточки минерала (`?style=glass`)
- Шкала Мооса с визуализацией (градиент 10 цветов)
- Цветовые свотчи с HEX значениями
- Сессии с таймаутом 2 часа

## Git
- **Ветка main:** production (v1.0.1)
- **Репозиторий:** /opt/gems_app

## Файлы для backups
- `/opt/gem-app-neon/backups/gem-app-neon-backup.tar.gz` (2,7 МБ)

## Важные пути
- **База данных:** `/opt/gems_app/gems.db`
- **Загрузки:** `/opt/gems_app/uploads/`
- **Логи:** journalctl -u gems_app.service
