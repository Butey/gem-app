#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug-модуль для отладки поиска в Gems Encyclopedia
"""

import sqlite3
from flask import Blueprint, render_template, request, current_app

debug_bp = Blueprint('debug', __name__, url_prefix='/debug')


@debug_bp.route('/search')
def debug_search():
    """Отладочная страница для тестирования поиска"""
    # Проверка включённой отладки поиска (через сессию или config)
    from flask import current_app, abort, session
    debug_enabled = session.get('debug_search_enabled', False) or current_app.config.get('DEBUG_SEARCH', False)
    if not debug_enabled:
        abort(403, description='Отладка поиска отключена. Включите в админ-панели.')
    
    query = request.args.get('q', '').strip()
    results = []
    sql_query = ''

    if query:
        db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if len(query) <= 3:
            query_upper = query.capitalize()
            sql_query = '''
                SELECT g.id, g.name, g.slug, g.category, g.parent_category, g.image_filename,
                       g.description, g.properties
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
                       g.description, g.properties,
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
