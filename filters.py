#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jinja2 фильтры для Gems Encyclopedia
Вынесены из app.py для модульности и читаемости
"""

import re
from typing import Dict


def nl2br_filter(s: str) -> str:
    """Заменяет переносы строк на <br>"""
    if not s:
        return ''
    return s.replace('\n', '<br>')


def mohs_color_filter(value: str) -> str:
    """
    Вычисляет цвет фона для бейджа твёрдости на основе значения.
    Использует градиент из 10 цветов шкалы Мооса.
    """
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
        return '#2563eb'

    try:
        mohs_value = value.split('–')[0].split('-')[0].replace(',', '.').strip()
        num = float(mohs_value)

        position = (num - 1) / 9
        index = position * 9

        lower_idx = int(index)
        upper_idx = min(lower_idx + 1, 9)
        fraction = index - lower_idx

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
        return '#2563eb'


def text_color_filter(bg_hex: str) -> str:
    """Возвращает цвет текста в зависимости от яркости фона"""
    try:
        bg_hex = bg_hex.lstrip('#')
        r, g, b = int(bg_hex[0:2], 16), int(bg_hex[2:4], 16), int(bg_hex[4:6], 16)
        brightness = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return '#1a1a1a' if brightness > 0.5 else '#ffffff'
    except:
        return '#ffffff'


# Карта цветов: название → HEX
COLOR_MAP: Dict[str, str] = {
    'красный': '#DC143C', 'тёмно-красный': '#8B0000', 'ярко-красный': '#FF0000',
    'светло-красный': '#FF6666', 'красноватый': '#CC5555', 'малиновый': '#DC143C',
    'вишнёвый': '#900020', 'фиолетово-красный': '#8B0040', 'оранжево-красный': '#FF4500',
    'буровато-красный': '#8B4513', 'оранжевый': '#FFA500', 'ярко-оранжевый': '#FF6600',
    'тёмно-оранжевый': '#FF8C00', 'жёлто-оранжевый': '#FFB100', 'жёлтый': '#FFD700',
    'ярко-жёлтый': '#FFFF00', 'светло-жёлтый': '#FFFFE0', 'тёмно-жёлтый': '#DAA520',
    'желтоватый': '#F0E68C', 'золотистый': '#DAA520', 'золотой': '#FFD700',
    'зелёный': '#008000', 'ярко-зелёный': '#00FF00', 'светло-зелёный': '#90EE90',
    'тёмно-зелёный': '#006400', 'зеленоватый': '#98FB98', 'жёлто-зелёный': '#9ACD32',
    'сине-зелёный': '#008B8B', 'бирюзовый': '#40E0D0', 'изумрудный': '#50C878',
    'оливковый': '#808000', 'бледно-зелёный': '#98FB98', 'небесно-зелёный': '#9FE5BF',
    'синий': '#0000FF', 'ярко-синий': '#0066FF', 'светло-синий': '#ADD8E6',
    'тёмно-синий': '#00008B', 'голубой': '#87CEEB', 'небесно-синий': '#87CEEB',
    'голубоватый': '#B0E0E6', 'васильковый': '#6495ED', 'лазурный': '#007FFF',
    'сапфировый': '#082567', 'фиолетовый': '#800080', 'ярко-фиолетовый': '#A020F0',
    'светло-фиолетовый': '#DDA0DD', 'тёмно-фиолетовый': '#4B0082', 'пурпурный': '#800080',
    'лиловый': '#C8A2C8', 'сиреневый': '#C8A2C8', 'лавандовый': '#E6E6FA',
    'розовый': '#FFC0CB', 'ярко-розовый': '#FF1493', 'светло-розовый': '#FFB6C1',
    'тёмно-розовый': '#C71585', 'розоватый': '#FFC0CB', 'кремовый': '#FFFDD0',
    'коричневый': '#A52A2A', 'тёмно-коричневый': '#654321', 'светло-коричневый': '#D2B48C',
    'бурый': '#8B4513', 'песочный': '#F4A460', 'бежевый': '#F5F5DC',
    'шоколадный': '#D2691E', 'серый': '#808080', 'светло-серый': '#D3D3D3',
    'тёмно-серый': '#696969', 'серо-голубой': '#B0C4DE', 'серебристый': '#C0C0C0',
    'стальной': '#4682B4', 'аспидный': '#708090', 'мокрый асфальт': '#4B535A',
    'чёрный': '#121212', 'белый': '#FFFFFF', 'бесцветный': '#F8F8FF',
    'молочный': '#FEFEFE',
}


def color_to_hex_filter(color_name: str) -> str:
    """Конвертирует название цвета в HEX код"""
    if not color_name:
        return '#CCCCCC'

    color_name = color_name.lower().strip()

    if color_name in COLOR_MAP:
        return COLOR_MAP[color_name]

    for key, value in COLOR_MAP.items():
        if key in color_name or color_name in key:
            return value

    return '#CCCCCC'


def category_plural_filter(category: str) -> str:
    """Склоняет названия категорий для хлебных крошек"""
    if not category:
        return ''

    category_forms = {
        'поделочный': 'поделочные',
        'органический': 'органические',
        'полудрагоценный': 'полудрагоценные',
        'строительные': 'строительные',
        'нерудные': 'нерудные',
        'руды металлов': 'руды металлов',
    }

    return category_forms.get(category, category)


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


def register_filters(app):
    """Регистрирует все фильтры в Flask приложении"""
    app.add_template_filter(nl2br_filter, 'nl2br')
    app.add_template_filter(mohs_color_filter, 'mohs_color')
    app.add_template_filter(text_color_filter, 'text_color')
    app.add_template_filter(color_to_hex_filter, 'color_to_hex')
    app.add_template_filter(category_plural_filter, 'category_plural')


# Маппинг категорий: множественное число → единственное (для URL)
CATEGORY_PLURAL_TO_SINGULAR = {
    'поделочные': 'поделочный',
    'органические': 'органический',
    'полудрагоценные': 'полудрагоценный',
    'строительные': 'строительные',
    'нерудные': 'нерудные',
    'руды металлов': 'руды металлов',
}
