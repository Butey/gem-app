from models import db, Gem, User
import sqlite3
import os

def init_app(app):
    db.init_app(app)

def create_tables(app):
    with app.app_context():
        db.create_all()
        # Создаём FTS5 виртуальную таблицу для полнотекстового поиска
        conn = sqlite3.connect(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))
        cursor = conn.cursor()
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS gems_search USING fts5(
                name, description, properties, locations, facts, zodiac, magic_props,
                content='gems', content_rowid='id'
            )
        ''')
        # Добавляем индекс для parent_category
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_parent_category ON gems(parent_category)
        ''')
        # Триггеры для синхронизации FTS с основной таблицей
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS gems_ai AFTER INSERT ON gems BEGIN
                INSERT INTO gems_search(rowid, name, description, properties, locations, facts, zodiac, magic_props)
                VALUES (new.id, new.name, new.description, new.properties, new.locations, new.facts, new.zodiac, new.magic_props);
            END;
        ''')
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS gems_ad AFTER DELETE ON gems BEGIN
                INSERT INTO gems_search(gems_search, rowid, name, description, properties, locations, facts, zodiac, magic_props)
                VALUES('delete', old.id, old.name, old.description, old.properties, old.locations, old.facts, old.zodiac, old.magic_props);
            END;
        ''')
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS gems_au AFTER UPDATE ON gems BEGIN
                INSERT INTO gems_search(gems_search, rowid, name, description, properties, locations, facts, zodiac, magic_props)
                VALUES('delete', old.id, old.name, old.description, old.properties, old.locations, old.facts, old.zodiac, old.magic_props);
                INSERT INTO gems_search(rowid, name, description, properties, locations, facts, zodiac, magic_props)
                VALUES (new.id, new.name, new.description, new.properties, new.locations, new.facts, new.zodiac, new.magic_props);
            END;
        ''')
        conn.commit()
        conn.close()