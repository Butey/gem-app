#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_sample_gems.py — Импорт 5 случайных камней из jewellerymag.ru/gems/
Совместимо с Python 3.7+
"""

import os
import sys
import re
import time
import random
import argparse
import sqlite3
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import Optional, List, Dict, Any

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("❌ Установите зависимости: pip install requests beautifulsoup4 lxml")
    sys.exit(1)

# === Настройки ===
SOURCE_URL = "https://jewellerymag.ru/gems/"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
REQUEST_DELAY = (2, 4)
DEFAULT_COUNT = 10
MAX_RETRIES = 3

PROJECT_DIR = Path(__file__).parent.resolve()
DB_PATH = PROJECT_DIR / "gems.db"
UPLOADS_DIR = PROJECT_DIR / "uploads"

CATEGORY_KEYWORDS = {
    "драгоценный": ["алмаз", "рубин", "сапфир", "изумруд", "бриллиант"],
    "полудрагоценный": ["топаз", "гранат", "аметист", "цитрин", "аквамарин", "турмалин"],
    "поделочный": ["яшма", "малахит", "агат", "бирюза", "сердолик", "нефрит"],
    "органический": ["жемчуг", "янтарь", "коралл", "гагат"],
}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = text.replace("ё", "е")
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    })
    return session


def fetch_page(url: str, session: requests.Session) -> Optional[str]:
    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(random.uniform(*REQUEST_DELAY))
            response = session.get(url, timeout=15)
            response.raise_for_status()
            response.encoding = "utf-8"
            return response.text
        except requests.RequestException as e:
            print(f"⚠ Попытка {attempt + 1}/{MAX_RETRIES} неудачна: {e}")
            if attempt == MAX_RETRIES - 1:
                return None
    return None


def parse_gems_index(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    links = []
    
    selectors = [
        "article.gem-card a",
        "div.gem-item a",
        "ul.gems-list a",
        "a[href*='/gems/']",
    ]
    
    for selector in selectors:
        elements = soup.select(selector)
        for el in elements:
            href = el.get("href")
            if href and "/gems/" in href and not href.endswith("/gems/"):
                full_url = urljoin(base_url, href)
                full_url = full_url.split("#")[0].split("?")[0]
                if full_url not in links:
                    links.append(full_url)
    
    return links


def parse_gem_detail(html: str, url: str) -> Optional[Dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    
    title_el = soup.find("h1") or soup.find("title")
    if not title_el:
        return None
    name = title_el.get_text(strip=True)
    name = re.sub(r"\s*[—|]\s*.*$", "", name).strip()
    
    image_url = None
    img_el = soup.find("img", class_=re.compile(r"main|large|featured", re.I))
    if not img_el:
        img_el = soup.select_one("article img, .content img")
    if img_el and img_el.get("src"):
        image_url = urljoin(url, img_el["src"])
    
    description = ""
    content_areas = soup.select("article, .content, .description, .entry-content")
    for area in content_areas:
        paras = area.find_all("p", recursive=False) or area.find_all("p")
        if paras:
            description = "\n".join(p.get_text(strip=True) for p in paras[:3])
            break
    
    if len(description) < 50:
        for tag in ["p", "div"]:
            for el in soup.find_all(tag):
                text = el.get_text(strip=True)
                if len(text) > 100 and len(text) < 2000:
                    description = text
                    break
            if description:
                break
    
    category = "полудрагоценный"
    name_lower = name.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            category = cat
            break
    
    properties = ""
    locations = ""
    
    for label in ["Твёрдость", "Плотность", "Показатель преломления", "Месторождения", "Добыча"]:
        if label in soup.text:
            for el in soup.find_all(string=lambda text: text and label in text):
                parent = el.find_parent()
                if parent:
                    next_el = parent.find_next_sibling() or parent.find_next()
                    if next_el:
                        value = next_el.get_text(strip=True)
                        if "твёрд" in label.lower():
                            properties += f"• {label}: {value}\n"
                        elif "мест" in label.lower() or "добыч" in label.lower():
                            locations += f"• {value}\n"
    
    return {
        "name": name,
        "slug": slugify(name),
        "category": category,
        "description": description or f"{name} — минерал природного происхождения.",
        "properties": properties.strip() or None,
        "locations": locations.strip() or None,
        "facts": None,
        "zodiac": None,
        "magic_props": None,
        "image_url": image_url,
        "source_url": url,
    }


def download_image(url: str, slug: str, uploads_dir: Path) -> Optional[str]:
    if not url:
        return None
    
    try:
        time.sleep(random.uniform(1, 2))
        response = requests.get(url, timeout=15, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        
        parsed = urlparse(url)
        ext = Path(parsed.path).suffix.lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
            ext = ".jpg"
        
        filename = f"{slug}{ext}"
        filepath = uploads_dir / filename
        
        with open(filepath, "wb") as f:
            f.write(response.content)
        
        print(f"  ✓ Изображение: {filename}")
        return filename
        
    except Exception as e:
        print(f"  ⚠ Не удалось скачать изображение: {e}")
        return None


def gem_exists(db_conn: sqlite3.Connection, slug: str) -> bool:
    cursor = db_conn.cursor()
    cursor.execute("SELECT id FROM gems WHERE slug = ?", (slug,))
    return cursor.fetchone() is not None


def insert_gem(db_conn: sqlite3.Connection, gem: Dict[str, Any], image_filename: Optional[str]) -> int:
    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO gems 
        (name, slug, category, description, properties, locations, 
         facts, zodiac, magic_props, image_filename)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        gem["name"],
        gem["slug"],
        gem["category"],
        gem["description"],
        gem["properties"],
        gem["locations"],
        gem["facts"],
        gem["zodiac"],
        gem["magic_props"],
        image_filename,
    ))
    db_conn.commit()
    return cursor.lastrowid


def main():
    parser = argparse.ArgumentParser(description="Импорт случайных камней из jewellerymag.ru")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help="Количество камней")
    parser.add_argument("--dry-run", action="store_true", help="Только показать, что будет импортировано")
    args = parser.parse_args()
    
    print(f"🔍 Импорт {args.count} случайных камней из {SOURCE_URL}")
    
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    
    if not DB_PATH.exists():
        print(f"❌ База данных не найдена: {DB_PATH}")
        sys.exit(1)
    
    session = get_session()
    
    print("\n📋 Сканирую каталог...")
    index_html = fetch_page(SOURCE_URL, session)
    if not index_html:
        print("❌ Не удалось загрузить каталог")
        sys.exit(1)
    
    gem_urls = parse_gems_index(index_html, SOURCE_URL)
    if not gem_urls:
        print("❌ Не найдено ссылок на камни.")
        sys.exit(1)
    
    print(f"   Найдено камней: {len(gem_urls)}")
    
    random.shuffle(gem_urls)
    
    conn = sqlite3.connect(DB_PATH)
    
    imported = 0
    for url in gem_urls:
        if imported >= args.count:
            break
        
        print(f"\n[{imported + 1}/{args.count}] Обработка: {url}")
        
        html = fetch_page(url, session)
        if not html:
            print("  ⚠ Пропущено: не удалось загрузить страницу")
            continue
        
        gem = parse_gem_detail(html, url)
        if not gem:
            print("  ⚠ Пропущено: не удалось распарсить данные")
            continue
        
        if gem_exists(conn, gem["slug"]):
            print(f"  ⊘ Уже существует: {gem['name']}")
            continue
        
        if args.dry_run:
            print(f"  ✓ Будет добавлен: {gem['name']} ({gem['category']})")
            if gem["image_url"]:
                print(f"    Изображение: {gem['image_url']}")
            imported += 1
            continue
        
        image_filename = download_image(gem["image_url"], gem["slug"], UPLOADS_DIR)
        
        try:
            gem_id = insert_gem(conn, gem, image_filename)
            print(f"  ✓ Добавлен: {gem['name']} (ID: {gem_id})")
            imported += 1
        except sqlite3.IntegrityError as e:
            print(f"  ⚠ Ошибка БД: {e}")
    
    conn.close()
    
    print(f"\n{'='*50}")
    if args.dry_run:
        print(f"📊 Dry run: будет импортировано {imported} камней")
    else:
        print(f"✅ Готово! Импортировано: {imported}/{args.count}")
        if imported > 0:
            print(f"🌐 Проверьте: http://localhost:5000/")


if __name__ == "__main__":
    main()