#!/usr/bin/env python3
"""
Скрипт для применения всех патчей из папки patches/

ИСПОЛЬЗОВАНИЕ:
  python3 apply_patches.py [patch_file.json]

ФУНКЦИОНАЛ:
  - Без аргументов: применяет все JSON файлы из папки patches/
  - С аргументом: применяет указанный JSON файл
  - Показывает прогресс и статистику
"""

import json
import os
import sys
import glob
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv('NOTION_TOKEN')

if not NOTION_TOKEN:
    print("❌ Ошибка: переменная окружения NOTION_TOKEN не установлена")
    print("Создайте файл .env на основе .env.example и заполните ключи")
    sys.exit(1)

TEXT_FIELDS = {"Город базы"}

NUMBER_FIELDS = {
    "Минимальный опыт (месяцы)",
    "Минимальная зарплата (нетто)",
    "Максимальная зарплата (нетто)"
}

MULTI_SELECT_FIELDS = {
    "Категория прав",
    "Тип техники",
    "Регионы работы",
    "Допустимое гражданство",
    "Исключённое гражданство"
}


def update_vacancy(json_file_path, silent=False):
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    page_id = data['page_id']
    props = data['properties']

    properties = {}
    for key, value in props.items():
        if isinstance(value, list):
            properties[key] = {
                "multi_select": [{"name": v} for v in value]
            }
        elif isinstance(value, (int, float)):
            properties[key] = {"number": value}
        elif value is None:
            if key in NUMBER_FIELDS:
                properties[key] = {"number": None}
            elif key in TEXT_FIELDS:
                properties[key] = {"rich_text": []}
            else:
                properties[key] = {"select": None}
        elif isinstance(value, str):
            if key in TEXT_FIELDS:
                properties[key] = {
                    "rich_text": [{"type": "text", "text": {"content": value}}]
                }
            else:
                properties[key] = {"select": {"name": value}}

    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    request_data = {"properties": properties}
    json_data = json.dumps(request_data, ensure_ascii=False).encode('utf-8')

    req = urllib.request.Request(url, data=json_data, headers=headers, method='PATCH')

    try:
        with urllib.request.urlopen(req) as response:
            json.loads(response.read().decode('utf-8'))
        if not silent:
            print(f"✅ Вакансия {page_id} успешно обновлена")
        return True, None
    except urllib.error.HTTPError as e:
        error_msg = f"HTTP {e.code}"
        try:
            error_data = json.loads(e.read().decode('utf-8'))
            error_msg += f": {error_data}"
        except:
            error_msg += f": {e.read().decode('utf-8', errors='ignore')}"
        if not silent:
            print(f"❌ Ошибка: {error_msg}")
        return False, error_msg
    except Exception as e:
        if not silent:
            print(f"❌ Ошибка: {e}")
        return False, str(e)


def apply_patches():
    patches_dir = Path(__file__).parent / "patches"
    
    if not patches_dir.exists():
        print(f"❌ Папка patches/ не найдена: {patches_dir}")
        return False
    
    json_files = sorted(glob.glob(str(patches_dir / "*.json")))
    
    if not json_files:
        print("⚠️  Папка patches/ пуста")
        return True
    
    print(f"📦 Найдено патчей: {len(json_files)}\n")
    
    success_count = 0
    error_count = 0
    errors = []
    
    for i, json_file in enumerate(json_files, 1):
        filename = os.path.basename(json_file)
        print(f"[{i}/{len(json_files)}] Применяю {filename}...", end=" ")
        
        success, error = update_vacancy(json_file, silent=True)
        
        if success:
            print("✅")
            success_count += 1
        else:
            print("❌")
            error_count += 1
            errors.append((filename, error))
    
    print(f"\n📊 Результаты:")
    print(f"  ✅ Успешно: {success_count}")
    print(f"  ❌ Ошибок: {error_count}")
    
    if errors:
        print(f"\n❌ Детали ошибок:")
        for filename, error in errors:
            print(f"  {filename}:")
            print(f"    {error}")
    
    return error_count == 0


if __name__ == "__main__":
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
        if not os.path.exists(json_file):
            print(f"❌ Файл не найден: {json_file}")
            sys.exit(1)
        success, _ = update_vacancy(json_file)
        sys.exit(0 if success else 1)
    else:
        success = apply_patches()
        sys.exit(0 if success else 1)
