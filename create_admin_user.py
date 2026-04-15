#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт создания первого пользователя админ-панели
Использование: python create_admin_user.py
"""

import os
import sys

# Добавляем путь к приложению
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, User

def create_admin_user():
    print("═" * 50)
    print("  Создание пользователя админ-панели")
    print("═" * 50)
    print()
    
    with app.app_context():
        # Проверяем, есть ли уже пользователи
        existing_users = User.query.all()
        
        if existing_users:
            print("⚠️  Уже существуют пользователи:")
            for user in existing_users:
                print(f"   - {user.username} (ID: {user.id})")
            print()
            
            response = input("Продолжить и создать нового пользователя? (y/n): ")
            if response.lower() != 'y':
                print("Отменено")
                return
        
        # Ввод данных
        username = input("Имя пользователя: ").strip()
        if not username:
            print("❌ Имя пользователя не может быть пустым")
            return
        
        # Проверка на существующего
        existing = User.query.filter_by(username=username).first()
        if existing:
            print(f"❌ Пользователь '{username}' уже существует")
            return
        
        password = input("Пароль: ")
        if not password:
            print("❌ Пароль не может быть пустым")
            return
        
        password_confirm = input("Подтвердите пароль: ")
        if password != password_confirm:
            print("❌ Пароли не совпадают")
            return
        
        # Создание пользователя
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        print()
        print(f"✅ Пользователь '{username}' успешно создан!")
        print()
        print("Теперь вы можете войти в админ-панель:")
        print(f"   Логин: {username}")
        print(f"   URL: /admin/login")
        print()

if __name__ == '__main__':
    create_admin_user()
