## Qwen Added Memories
- Приложение Gems Encyclopedia App работает как systemd-служба gems_app.service (gunicorn с 4 workers). Для перезапуска использовать: systemctl restart gems_app.service
- Папка ./temp (относительно /opt/gems_app) — это папка с временными файлами проекта
