#!/usr/bin/env python3
"""Скрипт инициализации БД и создания папок"""
from app import app
from database import create_tables
import os

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    create_tables(app)
    print("✓ База данных инициализирована")
    print(f"✓ Папка загрузок: {app.config['UPLOAD_FOLDER']}")
    print("\nЗапустите приложение: python app.py")