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
from functools import wraps
from datetime import timedelta
import sqlite3
import os
import re

app = Flask(__name__)
app.config.from_object(Config)

# === Фильтр для переносов строк в шаблонах ===
@app.template_filter('nl2br')
def nl2br_filter(s):
    """Заменяет переносы строк на <br>"""
    if not s:
        return ''
    return s.replace('\n', '<br>')

# === Фильтр для цвета бейджа твёрдости по Моосу ===
@app.template_filter('mohs_color')
def mohs_color_filter(value: str) -> str:
    """
    Вычисляет цвет фона для бейджа твёрдости на основе значения.
    Использует градиент из 10 цветов шкалы Мооса.
    """
    # Цвета из moos_state.txt для уровней 1-10
    colors = [
        '#F5F5F5',  # 1 - Тальк
        '#B0E0E6',  # 2 - Гипс
        '#48D1CC',  # 3 - Кальцит
        '#90EE90',  # 4 - Флюорит
        '#C4D300',  # 5 - Апатит
        '#FFD700',  # 6 - Ортоклаз
        '#FF8C00',  # 7 - Кварц
        '#FF4500',  # 8 - Топаз
        '#800020',  # 9 - Корунд
        '#121212',  # 10 - Алмаз
    ]
    
    if not value:
        return '#2563eb'  # default blue
    
    try:
        # Берём первое значение из диапазона (например, "6,5–7" → 6,5)
        mohs_value = value.split('–')[0].split('-')[0].replace(',', '.').strip()
        num = float(mohs_value)
        
        # Вычисляем индекс в градиенте (0-9)
        # Позиция 1 = индекс 0, позиция 10 = индекс 9
        position = (num - 1) / 9  # 0.0 to 1.0
        index = position * 9  # 0 to 9
        
        # Интерполяция между соседними цветами
        lower_idx = int(index)
        upper_idx = min(lower_idx + 1, 9)
        fraction = index - lower_idx
        
        # Простая интерполяция RGB
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        def rgb_to_hex(rgb):
            return '#{:02X}{:02X}{:02X}'.format(
                max(0, min(255, int(rgb[0]))),
                max(0, min(255, int(rgb[1]))),
                max(0, min(255, int(rgb[2])))
            )
        
        lower_rgb = hex_to_rgb(colors[lower_idx])
        upper_rgb = hex_to_rgb(colors[upper_idx])
        
        interpolated = tuple(
            lower_rgb[i] + fraction * (upper_rgb[i] - lower_rgb[i])
            for i in range(3)
        )
        
        return rgb_to_hex(interpolated)
    except (ValueError, IndexError):
        return '#2563eb'  # default blue

# === Фильтр для цвета текста бейджа (светлый/тёмный) ===
@app.template_filter('text_color')
def text_color_filter(bg_hex: str) -> str:
    """
    Возвращает #000000 или #FFFFFF в зависимости от яркости фона.
    """
    try:
        bg_hex = bg_hex.lstrip('#')
        r, g, b = int(bg_hex[0:2], 16), int(bg_hex[2:4], 16), int(bg_hex[4:6], 16)
        # Формула яркости: (0.299*R + 0.587*G + 0.114*B)
        brightness = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return '#1a1a1a' if brightness > 0.5 else '#ffffff'
    except:
        return '#ffffff'

# === Фильтр для конвертации названия цвета в HEX ===
@app.template_filter('color_to_hex')
def color_to_hex_filter(color_name: str) -> str:
    """
    Конвертирует название цвета в HEX код.
    """
    color_map = {
        # Красные оттенки
        'красный': '#DC143C',
        'тёмно-красный': '#8B0000',
        'ярко-красный': '#FF0000',
        'светло-красный': '#FF6666',
        'красноватый': '#CC5555',
        'малиновый': '#DC143C',
        'вишнёвый': '#900020',
        'фиолетово-красный': '#8B0040',
        'оранжево-красный': '#FF4500',
        'буровато-красный': '#8B4513',
        
        # Оранжевые оттенки
        'оранжевый': '#FFA500',
        'ярко-оранжевый': '#FF6600',
        'тёмно-оранжевый': '#FF8C00',
        'жёлто-оранжевый': '#FFB100',
        
        # Жёлтые оттенки
        'жёлтый': '#FFD700',
        'ярко-жёлтый': '#FFFF00',
        'светло-жёлтый': '#FFFFE0',
        'тёмно-жёлтый': '#DAA520',
        'желтоватый': '#F0E68C',
        'золотистый': '#DAA520',
        'золотой': '#FFD700',
        
        # Зелёные оттенки
        'зелёный': '#008000',
        'ярко-зелёный': '#00FF00',
        'светло-зелёный': '#90EE90',
        'тёмно-зелёный': '#006400',
        'зеленоватый': '#98FB98',
        'жёлто-зелёный': '#9ACD32',
        'сине-зелёный': '#008B8B',
        'бирюзовый': '#40E0D0',
        'изумрудный': '#50C878',
        'оливковый': '#808000',
        'бледно-зелёный': '#98FB98',
        'небесно-зелёный': '#9FE5BF',
        
        # Синие оттенки
        'синий': '#0000FF',
        'ярко-синий': '#0066FF',
        'светло-синий': '#ADD8E6',
        'тёмно-синий': '#00008B',
        'голубой': '#87CEEB',
        'небесно-синий': '#87CEEB',
        'голубоватый': '#B0E0E6',
        'васильковый': '#6495ED',
        'лазурный': '#007FFF',
        'сапфировый': '#082567',
        
        # Фиолетовые оттенки
        'фиолетовый': '#800080',
        'ярко-фиолетовый': '#A020F0',
        'светло-фиолетовый': '#DDA0DD',
        'тёмно-фиолетовый': '#4B0082',
        'пурпурный': '#800080',
        'лиловый': '#C8A2C8',
        'сиреневый': '#C8A2C8',
        'лавандовый': '#E6E6FA',
        
        # Розовые оттенки
        'розовый': '#FFC0CB',
        'ярко-розовый': '#FF1493',
        'светло-розовый': '#FFB6C1',
        'тёмно-розовый': '#C71585',
        'розоватый': '#FFC0CB',
        'кремовый': '#FFFDD0',
        
        # Коричневые оттенки
        'коричневый': '#A52A2A',
        'тёмно-коричневый': '#654321',
        'светло-коричневый': '#D2B48C',
        'бурый': '#8B4513',
        'песочный': '#F4A460',
        'бежевый': '#F5F5DC',
        'шоколадный': '#D2691E',
        
        # Серые оттенки
        'серый': '#808080',
        'светло-серый': '#D3D3D3',
        'тёмно-серый': '#696969',
        'серо-голубой': '#B0C4DE',
        'серебристый': '#C0C0C0',
        'стальной': '#4682B4',
        'аспидный': '#708090',
        'мокрый асфальт': '#4B535A',
        
        # Чёрные и белые оттенки
        'чёрный': '#121212',
        'белый': '#FFFFFF',
        'бесцветный': '#F8F8FF',
        'молочный': '#FEFEFE',
    }
    
    if not color_name:
        return '#CCCCCC'
    
    color_name = color_name.lower().strip()
    
    # Точное совпадение
    if color_name in color_map:
        return color_map[color_name]
    
    # Частичное совпадение
    for key, value in color_map.items():
        if key in color_name or color_name in key:
            return value
    
    # Цвет по умолчанию
    return '#CCCCCC'

# === Фильтр для склонения названий категорий ===
@app.template_filter('category_plural')
def category_plural_filter(category: str) -> str:
    """
    Склоняет названия категорий для хлебных крошек.
    поделочный → поделочные
    органический → органические
    полудрагоценный → полудрагоценные
    """
    if not category:
        return ''
    
    # Словарь склонений
    category_forms = {
        'поделочный': 'поделочные',
        'органический': 'органические',
        'полудрагоценный': 'полудрагоценные',
        'строительные': 'строительные',
        'нерудные': 'нерудные',
        'руды металлов': 'руды металлов',
    }
    
    return category_forms.get(category, category)

# === Транслитерация для slug ===
def transliterate(text: str) -> str:
    """Преобразует кириллицу в латиницу для URL"""
    converter = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '',
        'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya', ' ': '-',
    }
    text = text.lower().strip()
    result = ''.join(converter.get(c, c) for c in text)
    result = re.sub(r'[^a-z0-9-]', '', result)
    result = re.sub(r'-+', '-', result)
    return result.strip('-')

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
ADMIN_CREDENTIALS = {
    'username': 'admin',
    'password': 'museum2026'  # ⚠️ ЗАМЕНИТЕ ПЕРЕД ПРОДАКШЕНОМ!
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

# Маппинг категорий: множественное число → единственное (для URL)
CATEGORY_PLURAL_TO_SINGULAR = {
    'поделочные': 'поделочный',
    'органические': 'органический',
    'полудрагоценные': 'полудрагоценный',
    'строительные': 'строительные',
    'нерудные': 'нерудные',
    'руды металлов': 'руды металлов',
}

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

# === Поиск с подсказками (обновлено: только заголовок и описание) ===
@app.route('/api/search/suggest')
def search_suggest():
    query = request.args.get('q', '').strip().lower()
    if len(query) < 2:
        return jsonify([])

    conn = sqlite3.connect(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # === 1. Префиксный поиск для коротких запросов (2-3 символа) ===
    if len(query) <= 3:
        # Для кириллицы SQLite не поддерживает LOWER/UPPER, поэтому ищем оба варианта
        query_upper = query.capitalize()
        cursor.execute('''
            SELECT g.id, g.name, g.slug, g.category, g.image_filename,
                   g.description as snippet
            FROM gems g
            WHERE g.name LIKE ? OR g.name LIKE ? OR
                  g.description LIKE ? OR g.description LIKE ?
            ORDER BY g.name
            LIMIT 10
        ''', (f'{query}%', f'{query_upper}%',
              f'%{query}%', f'%{query_upper}%'))

    # === 2. FTS5 поиск с префиксами для запросов 4+ символов ===
    else:
        terms = query.split()
        fts_query = ' '.join(f'{term}*' for term in terms)

        cursor.execute('''
            SELECT g.id, g.name, g.slug, g.category, g.image_filename,
                   snippet(gems_search, 0, '<mark>', '</mark>', '…', 50) as snippet
            FROM gems_search
            JOIN gems g ON gems_search.rowid = g.id
            WHERE gems_search MATCH ?
            ORDER BY bm25(gems_search)
            LIMIT 10
        ''', (fts_query,))

    results = []
    for row in cursor.fetchall():
        snippet = row['snippet'] or ''
        row_snippet = row['snippet']

        # Если сниппет не содержит запрос — берём контекст из описания
        if query.lower() not in snippet.lower() and row_snippet and len(row_snippet) > 100:
            desc = row_snippet
            idx = desc.lower().find(query)
            if idx >= 0:
                start = max(0, idx - 40)
                end = min(len(desc), idx + len(query) + 40)
                snippet = ('…' if start > 0 else '') + \
                         desc[start:idx] + \
                         f'<mark>{desc[idx:idx+len(query)]}</mark>' + \
                         desc[idx+len(query):end] + \
                         ('…' if end < len(desc) else '')

        if len(snippet) > 160:
            snippet = snippet[:157] + '…'

        results.append({
            'id': row['id'],
            'name': row['name'],
            'slug': row['slug'],
            'category': row['category'],
            'image': f'/uploads/{row["image_filename"]}' if row['image_filename'] else '/static/img/placeholder.png',
            'snippet': snippet
        })
    
    conn.close()
    return jsonify(results)

# === Страница камня ===
@app.route('/gem/<slug>')
def gem_detail(slug):
    gem = Gem.query.filter_by(slug=slug).first_or_404()
    return render_template('gem_detail.html', gem=gem)

# === Отладка поиска (обновлено: только заголовок и описание) ===
@app.route('/debug/search')
def debug_search():
    query = request.args.get('q', '').strip()
    results = []
    sql_query = ''

    if query:
        conn = sqlite3.connect(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if len(query) <= 3:
            query_upper = query.capitalize()
            sql_query = '''
                SELECT g.id, g.name, g.slug, g.category, g.parent_category, g.image_filename,
                       g.description
                FROM gems g
                WHERE g.name LIKE ? OR g.name LIKE ? OR
                      g.description LIKE ? OR g.description LIKE ?
                ORDER BY g.name
                LIMIT 20
            '''
            cursor.execute(sql_query, (f'{query}%', f'{query_upper}%',
                                       f'%{query}%', f'%{query_upper}%'))
        else:
            terms = query.split()
            fts_query = ' '.join(f'{term}*' for term in terms)
            sql_query = '''
                SELECT g.id, g.name, g.slug, g.category, g.parent_category, g.image_filename,
                       g.description,
                       snippet(gems_search, 0, '<mark>', '</mark>', '…', 50) as snippet
                FROM gems_search
                JOIN gems g ON gems_search.rowid = g.id
                WHERE gems_search MATCH ?
                ORDER BY bm25(gems_search)
                LIMIT 20
            '''
            cursor.execute(sql_query, (fts_query,))
        
        for row in cursor.fetchall():
            results.append({
                'id': row['id'],
                'name': row['name'],
                'slug': row['slug'],
                'category': row['category'],
                'parent_category': row['parent_category'],
                'image_filename': row['image_filename'],
                'description': row['description'][:200] if row['description'] else '',
                'properties': row['properties'][:200] if row['properties'] else '',
                'snippet': row['snippet'] if len(query) > 3 else None
            })
        
        conn.close()
    
    return render_template('debug_search.html', 
                         query=query, 
                         results=results, 
                         sql_query=sql_query,
                         result_count=len(results))

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
    return redirect(url_for('admin_dashboard'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'webp'}

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)