#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gems Encyclopedia App — Каталог минералов с поиском и админ-панелью
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory, abort, session, flash
from werkzeug.utils import secure_filename
from config import Config
from models import db, Gem
from database import init_app, create_tables
from search import search_gems
from debug import debug_bp
from filters import register_filters, transliterate, CATEGORY_PLURAL_TO_SINGULAR
from functools import wraps
from datetime import timedelta
import sqlite3
import os
import re

app = Flask(__name__)
app.config.from_object(Config)

# Регистрация Blueprint'ов
app.register_blueprint(debug_bp)

# Регистрация Jinja2 фильтров
register_filters(app)

init_app(app)
create_tables(app)

# === Context processor для алфавитного указателя ===
@app.context_processor
def inject_alphabet_index():
    """Добавляет алфавитный указатель во все шаблоны"""
    # Получаем текущий контекст запроса
    from flask import request
    category = request.args.get('category', '')
    parent_category = request.args.get('parent_category', '')
    
    # Конвертируем множественное число в единственное для БД
    if category:
        category = CATEGORY_PLURAL_TO_SINGULAR.get(category, category)
    
    # Формируем запрос с учётом категории
    query = Gem.query
    if category:
        query = query.filter_by(category=category)
    elif parent_category:
        query = query.filter_by(parent_category=parent_category)
    
    alphabet_index = {}
    gems = query.order_by(Gem.name).all()
    for gem in gems:
        first_letter = gem.name[0].upper()
        if first_letter not in alphabet_index:
            alphabet_index[first_letter] = []
        alphabet_index[first_letter].append(gem)
    
    return dict(alphabet_index=alphabet_index, CATEGORY_PLURAL_TO_SINGULAR=CATEGORY_PLURAL_TO_SINGULAR)

# === Админ-панель: настройки ===
# Учётные данные берутся из config (поддержка переменных окружения)
ADMIN_CREDENTIALS = {
    'username': app.config['ADMIN_USERNAME'],
    'password': app.config['ADMIN_PASSWORD']
}

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Требуется авторизация', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# === Статика ===
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# === Главная страница (стартовая) ===
@app.route('/')
def welcome():
    """Стартовая страница с категориями"""
    return render_template('welcome.html')

# === Каталог минералов ===

@app.route('/catalog')
def catalog():
    """Каталог минералов с фильтрами и алфавитом"""
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '')
    parent_category = request.args.get('parent_category', '')
    letter = request.args.get('letter', '')  # Новая переменная для буквы
    search_query = request.args.get('q', '')  # Поиск
    per_page = 20  # Карточек на страницу

    # Конвертируем множественное число в единственное для БД
    if category:
        category = CATEGORY_PLURAL_TO_SINGULAR.get(category, category)

    query = Gem.query
    if category:
        query = query.filter_by(category=category)
    elif parent_category:
        query = query.filter_by(parent_category=parent_category)

    # Фильтрация по первой букве
    if letter:
        query = query.filter(Gem.name.ilike(f'{letter}%'))

    # Поиск по названию
    if search_query:
        query = query.filter(Gem.name.ilike(f'%{search_query}%'))

    # Сортировка по названию
    gems = query.order_by(Gem.name).paginate(page=page, per_page=per_page, error_out=False)

    return render_template('index.html',
                         gems=gems,
                         current_category=category,
                         current_parent_category=parent_category,
                         current_letter=letter,
                         pagination=gems)

# === Поиск с подсказками (обновлено: использует search.py) ===
@app.route('/api/search/suggest')
def search_suggest():
    """AJAX-поиск с подсказками для autocomplete"""
    query = request.args.get('q', '').strip().lower()
    results = search_gems(app, query, limit=10)
    return jsonify(results)

# === Страница камня ===
@app.route('/gem/<slug>')
def gem_detail(slug):
    gem = Gem.query.filter_by(slug=slug).first_or_404()
    return render_template('gem_detail.html', gem=gem)

# === Админка: вход ===
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_CREDENTIALS['username'] and password == ADMIN_CREDENTIALS['password']:
            session['admin_logged_in'] = True
            session.permanent = True
            flash('Вход выполнен', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Неверные учётные данные', 'error')
            return redirect(url_for('admin_login'))
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Выход выполнен', 'info')
    return redirect(url_for('index'))

# === Админка: CRUD ===
@app.route('/admin')
@admin_required
def admin_dashboard():
    gems = Gem.query.order_by(Gem.name).all()
    return render_template('admin_dashboard.html', gems=gems)

@app.route('/admin/create', methods=['GET', 'POST'])
@admin_required
def admin_create():
    if request.method == 'POST':
        return save_gem(None)
    return render_template('admin_form.html', gem=None, action='create')

@app.route('/admin/edit/<int:gem_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit(gem_id):
    gem = Gem.query.get_or_404(gem_id)
    if request.method == 'POST':
        return save_gem(gem)
    return render_template('admin_form.html', gem=gem, action='edit')

@app.route('/admin/delete/<int:gem_id>', methods=['POST'])
@admin_required
def admin_delete(gem_id):
    gem = Gem.query.get_or_404(gem_id)
    if gem.image_filename:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], gem.image_filename))
        except OSError:
            pass
    db.session.delete(gem)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

def save_gem(gem):
    """Сохраняет данные минерала (create/update) с обработкой ошибок"""
    try:
        name = request.form['name']
        slug = request.form['slug'] or transliterate(name)

        existing = Gem.query.filter(Gem.slug == slug, Gem.id != (gem.id if gem else None)).first()
        if existing:
            return render_template('admin_form.html', gem=gem, action='edit' if gem else 'create',
                                 error='Запись с таким URL уже существует')

        if not gem:
            gem = Gem()

        gem.name = name
        gem.slug = slug
        gem.category = request.form['category']
        gem.parent_category = request.form.get('parent_category', '')
        gem.description = request.form['description']
        gem.properties = request.form.get('properties', '')
        gem.locations = request.form.get('locations', '')
        gem.facts = request.form.get('facts', '')
        gem.zodiac = request.form.get('zodiac', '')
        gem.magic_props = request.form.get('magic_props', '')

        # Обработка главного изображения
        if 'image' in request.files and request.files['image'].filename:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{slug}_{file.filename}")
                if gem.image_filename:
                    try:
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], gem.image_filename))
                    except OSError:
                        pass
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                gem.image_filename = filename

        # Обработка галереи (множественная загрузка)
        if 'gallery' in request.files:
            gallery_files = request.files.getlist('gallery')
            gallery_list = gem.get_gallery() if gem.get_gallery() else []

            for file in gallery_files:
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(f"{slug}_gallery_{file.filename}")
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    gallery_list.append(filename)

            gem.set_gallery(gallery_list)

        # Удаление фото из галереи (если отмечены)
        if 'remove_gallery' in request.form:
            remove_indices = request.form.getlist('remove_gallery')
            gallery_list = gem.get_gallery()
            for idx in sorted(remove_indices, reverse=True):
                try:
                    idx_int = int(idx)
                    if 0 <= idx_int < len(gallery_list):
                        # Удаляем файл
                        try:
                            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], gallery_list[idx_int]))
                        except OSError:
                            pass
                        gallery_list.pop(idx_int)
                except ValueError:
                    pass
            gem.set_gallery(gallery_list)

        db.session.add(gem)
        db.session.commit()
        flash('Минерал сохранён', 'success')
        return redirect(url_for('admin_dashboard'))

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка сохранения: {str(e)}', 'error')
        return render_template('admin_form.html', gem=gem, action='edit' if gem else 'create',
                             error='Произошла ошибка при сохранении')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'webp'}

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)