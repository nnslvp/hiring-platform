#!/usr/bin/env python3
"""
Скрипт для обновления свойств вакансий в Notion через API

ФУНКЦИОНАЛ:
  - Читает данные вакансии из JSON файла
  - Обновляет только указанные поля в Notion (не трогает остальные)
  - Поддерживает типы полей: multi_select, select, number (int, float и null)

ИСПОЛЬЗОВАНИЕ:
  python3 update_vacancy_from_json.py <путь_к_json_файлу>

ПРИМЕР:
  python3 update_vacancy_from_json.py vacancy-data-pogorska-wola.json

ФОРМАТ JSON ФАЙЛА:
  {
    "page_id": "27c95810-6f37-8000-ada8-db237f784232",
    "properties": {
      "Категория прав": ["CE", "BDF"],           // multi_select (массив строк)
      "Тип техники": ["BDF"],                    // multi_select (массив строк)
      "Регионы работы": ["По всей Европе"],     // multi_select (массив строк)
      "Минимальный опыт (месяцы)": 6,            // number (int или float)
      "Код 95": "Обязательно",                   // select (строка)
      "ADR": "Желательно",                       // select (строка)
      "Минимальная зарплата (нетто, /день)": 300,  // number (int или float)
      "Максимальная зарплата (нетто, /день)": 320, // number (int, float или null)
      "Валюта зарплаты": "PLN",                 // select (строка): PLN, EUR, Не указано
      "Тип договора": "UMOWA O PRACĘ",          // select (строка)
      "Карта водителя": "Обязательно"            // select (строка)
    }
  }

ВАЖНО:
  - Обновляются только поля, указанные в JSON
  - Не указанные поля остаются без изменений
  - Пустые массивы [] очистят multi_select поле
  - Для number полей можно указать null (например, для максимальной зарплаты, если указана только фиксированная сумма)
  - Токен можно задать через переменную окружения NOTION_TOKEN
"""

import json
import os
import sys
import urllib.request
import urllib.error
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

NOTION_TOKEN = os.getenv('NOTION_TOKEN')

if not NOTION_TOKEN:
    print("❌ Ошибка: переменная окружения NOTION_TOKEN не установлена")
    print("Создайте файл .env на основе .env.example и заполните ключи")
    sys.exit(1)

def update_vacancy(json_file_path):
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
            properties[key] = {"number": None}
        elif isinstance(value, str):
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
            result = json.loads(response.read().decode('utf-8'))
        print(f"✅ Вакансия {page_id} успешно обновлена")
        return True
    except urllib.error.HTTPError as e:
        print(f"❌ Ошибка: HTTP {e.code}")
        try:
            error_data = json.loads(e.read().decode('utf-8'))
            print(f"Ответ: {error_data}")
        except:
            print(f"Ответ: {e.read().decode('utf-8', errors='ignore')}")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python3 update_vacancy_from_json.py <путь_к_json_файлу>")
        sys.exit(1)
    
    json_file = sys.argv[1]
    if not os.path.exists(json_file):
        print(f"❌ Файл не найден: {json_file}")
        sys.exit(1)
    
    update_vacancy(json_file)

