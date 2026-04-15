#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль поиска для Gems Encyclopedia
Выносит общую логику поиска из app.py для устранения дублирования
"""

import sqlite3
from typing import List, Dict
from flask import Flask


def get_db_connection(app: Flask) -> sqlite3.Connection:
    """Создаёт подключение к SQLite БД"""
    db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def search_gems(app: Flask, query: str, limit: int = 10) -> List[Dict]:
    """
    Выполняет поиск минералов по названию и описанию.
    Использует префиксный поиск для коротких запросов (1-3 символа)
    и FTS5 для запросов 4+ символов.

    Args:
        app: Flask application instance
        query: поисковый запрос
        limit: ограничение количества результатов

    Returns:
        Список словарей с результатами поиска
    """
    if len(query) < 1:
        return []

    conn = get_db_connection(app)
    cursor = conn.cursor()

    results = []

    try:
        # Префиксный поиск для коротких запросов
        if len(query) <= 3:
            results = _prefix_search(cursor, query, limit)
        # FTS5 поиск для длинных запросов
        else:
            results = _fts_search(cursor, query, limit)
    finally:
        conn.close()

    return results


def _prefix_search(cursor, query: str, limit: int) -> List[Dict]:
    """Префиксный поиск с поддержкой кириллицы"""
    query_upper = query.capitalize()
    
    cursor.execute('''
        SELECT g.id, g.name, g.slug, g.category, g.image_filename,
               g.description as snippet
        FROM gems g
        WHERE g.name LIKE ? OR g.name LIKE ? OR
              g.description LIKE ? OR g.description LIKE ?
        ORDER BY g.name
        LIMIT ?
    ''', (f'{query}%', f'{query_upper}%',
          f'%{query}%', f'%{query_upper}%', limit))
    
    return [_format_result(row, query) for row in cursor.fetchall()]


def _fts_search(cursor, query: str, limit: int) -> List[Dict]:
    """Полнотекстовый поиск с использованием FTS5"""
    terms = query.split()
    fts_query = ' '.join(f'{term}*' for term in terms)
    
    cursor.execute('''
        SELECT g.id, g.name, g.slug, g.category, g.image_filename,
               snippet(gems_search, 0, '<mark>', '</mark>', '…', 50) as snippet
        FROM gems_search
        JOIN gems g ON gems_search.rowid = g.id
        WHERE gems_search MATCH ?
        ORDER BY bm25(gems_search)
        LIMIT ?
    ''', (fts_query, limit))
    
    return [_format_result(row, query) for row in cursor.fetchall()]


def _format_result(row, query: str) -> Dict:
    """Форматирует результат поиска, создавая сниппет"""
    snippet = row['snippet'] or ''
    
    # Если сниппет не содержит запрос — создаём контекст из описания
    if query.lower() not in snippet.lower() and row['snippet'] and len(row['snippet']) > 100:
        snippet = _create_snippet(row['snippet'], query)
    
    # Ограничиваем длину сниппета
    if len(snippet) > 160:
        snippet = snippet[:157] + '…'
    
    return {
        'id': row['id'],
        'name': row['name'],
        'slug': row['slug'],
        'category': row['category'],
        'image': f'/uploads/{row["image_filename"]}' if row['image_filename'] else '/static/img/placeholder.png',
        'snippet': snippet,
    }


def _create_snippet(text: str, query: str, context_size: int = 40) -> str:
    """Создаёт сниппет с подсветкой поискового запроса"""
    idx = text.lower().find(query.lower())
    if idx == -1:
        return text[:160]
    
    start = max(0, idx - context_size)
    end = min(len(text), idx + len(query) + context_size)
    
    snippet = ('…' if start > 0 else '') + \
              text[start:idx] + \
              f'<mark>{text[idx:idx+len(query)]}</mark>' + \
              text[idx+len(query):end] + \
              ('…' if end < len(text) else '')
    
    return snippet
