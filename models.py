from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Gem(db.Model):
    __tablename__ = 'gems'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False)  # руды металлов/нерудные/строительные/полудрагоценный/поделочный/органический
    parent_category = db.Column(db.String(50), nullable=True)  # полезные ископаемые/самоцветы
    description = db.Column(db.Text, nullable=False)
    properties = db.Column(db.Text)  # физические/химические свойства
    locations = db.Column(db.Text)   # места добычи
    facts = db.Column(db.Text)       # интересные факты
    zodiac = db.Column(db.Text)      # зодиакальные характеристики
    magic_props = db.Column(db.Text) # магические свойства
    image_filename = db.Column(db.String(200))  # имя файла изображения
    gallery = db.Column(db.Text)  # JSON список дополнительных фото
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_gallery(self):
        """Возвращает список фото галереи"""
        if not self.gallery:
            return []
        try:
            return json.loads(self.gallery)
        except:
            return []

    def set_gallery(self, images_list):
        """Устанавливает список фото галереи"""
        self.gallery = json.dumps(images_list, ensure_ascii=False)

    def __repr__(self):
        return f'<Gem {self.name}>'