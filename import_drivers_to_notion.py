#!/usr/bin/env python3
"""
Импорт водителей в Notion из candidate_analysis.json

  python3 import_drivers_to_notion.py              # импортировать всех
  python3 import_drivers_to_notion.py --batch-size 10
"""

import json
import os
import sys
import argparse
import urllib.request
import urllib.error
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv('NOTION_TOKEN')
DRIVERS_DB_ID = '2ba95810-6f37-815e-86f2-ed07436ca6b0'
CANDIDATE_ANALYSIS_FILE = 'candidate_analysis.json'
TIKTOK_DATA_FILE = 'user_data_tiktok.json'

# Кэш переписок
_chat_history_cache = None

if not NOTION_TOKEN:
    print("❌ Ошибка: переменная окружения NOTION_TOKEN не установлена")
    sys.exit(1)


def load_chat_history_cache():
    """Загружает все переписки из user_data_tiktok.json"""
    global _chat_history_cache
    if _chat_history_cache is not None:
        return _chat_history_cache
    
    if not os.path.exists(TIKTOK_DATA_FILE):
        print(f"⚠️ Файл {TIKTOK_DATA_FILE} не найден")
        _chat_history_cache = {}
        return _chat_history_cache
    
    with open(TIKTOK_DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    chat_history = data.get("Direct Message", {}).get("Direct Messages", {}).get("ChatHistory", {})
    
    _chat_history_cache = {}
    for key, messages in chat_history.items():
        if key.startswith("Chat History with ") and key.endswith(":"):
            chat_name = key[len("Chat History with "):-1]
            _chat_history_cache[chat_name] = messages
    
    return _chat_history_cache


def get_chat_text(chat_name):
    """Возвращает переписку как текст для Notion"""
    cache = load_chat_history_cache()
    messages = cache.get(chat_name, [])
    if not messages:
        return None
    
    # Сортируем по дате (старые сначала)
    sorted_msgs = sorted(messages, key=lambda m: m.get('Date', ''))
    
    lines = []
    for msg in sorted_msgs:
        date = msg.get('Date', '')
        author = msg.get('From', '')
        content = msg.get('Content', '')
        lines.append(f"[{date}] {author}: {content}")
    
    return "\n\n".join(lines)


def notion_request(method, endpoint, data=None):
    url = f"https://api.notion.com/v1{endpoint}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    json_data = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=json_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        try:
            error_data = json.loads(error_body)
            print(f"❌ Notion API Error: {error_data.get('message', error_body)}")
        except:
            print(f"❌ Notion API Error: HTTP {e.code} - {error_body}")
        return None


def get_page_blocks(page_id):
    """Получает блоки страницы"""
    result = notion_request("GET", f"/blocks/{page_id}/children?page_size=100")
    return result.get("results", []) if result else []


def delete_block(block_id):
    """Удаляет блок"""
    return notion_request("DELETE", f"/blocks/{block_id}")


def update_page_chat(page_id, chat_name):
    """Обновляет переписку на странице — удаляет старую, добавляет новую"""
    chat_text = get_chat_text(chat_name)
    if not chat_text:
        return
    
    # Удаляем старый блок переписки (ищем по заголовку)
    blocks = get_page_blocks(page_id)
    for block in blocks:
        if block.get("type") == "heading_3":
            rich_text = block.get("heading_3", {}).get("rich_text", [])
            if rich_text and rich_text[0].get("text", {}).get("content", "").startswith("💬 Переписка"):
                delete_block(block["id"])
                # Удаляем следующий блок (текст переписки)
                idx = blocks.index(block)
                if idx + 1 < len(blocks):
                    delete_block(blocks[idx + 1]["id"])
                break
    
    # Notion ограничивает текст блока до 2000 символов, разбиваем если надо
    MAX_LEN = 2000
    text_chunks = []
    if len(chat_text) <= MAX_LEN:
        text_chunks = [chat_text]
    else:
        # Разбиваем по сообщениям
        parts = chat_text.split("\n\n")
        current = ""
        for part in parts:
            if len(current) + len(part) + 2 <= MAX_LEN:
                current = current + "\n\n" + part if current else part
            else:
                if current:
                    text_chunks.append(current)
                current = part if len(part) <= MAX_LEN else part[:MAX_LEN-3] + "..."
        if current:
            text_chunks.append(current)
    
    # Создаём блоки
    children = [
        {
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"type": "text", "text": {"content": f"💬 Переписка ({len(load_chat_history_cache().get(chat_name, []))} сообщений)"}}]
            }
        }
    ]
    for chunk in text_chunks:
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": chunk}}]
            }
        })
    
    # Добавляем на страницу
    notion_request("PATCH", f"/blocks/{page_id}/children", {"children": children})


def build_page_properties(candidate, is_update=False):
    """
    Создаёт свойства для страницы.
    is_update=True: не включает поля, которые редактирует менеджер (Name, Status)
    """
    chat_name = candidate.get('chatName', '')
    file_name = candidate.get('fileName', '')
    messages_count = candidate.get('messagesCount', 0)
    checklist = candidate.get('checklist', {})
    profile = candidate.get('profile', {})
    
    tiktok_url = f"https://www.tiktok.com/@{chat_name}" if chat_name else None
    
    props = {
        "TikTok Nickname": {"rich_text": [{"text": {"content": chat_name}}]},
        "fileName": {"rich_text": [{"text": {"content": file_name}}]},
        "messagesCount": {"number": messages_count},
        "Источник": {"select": {"name": "TikTok"}},
    }
    
    if not is_update:
        props["Name"] = {"title": [{"text": {"content": chat_name}}]}
    
    if tiktok_url:
        props["TikTok URL"] = {"url": tiktok_url}
    
    props["Пожелания предоставлены"] = {"checkbox": checklist.get('preferences_provided', False)}
    props["Вакансия отправлена"] = {"checkbox": checklist.get('vacancy_offered', False)}
    props["Вакансия принята"] = {"checkbox": checklist.get('vacancy_accepted', False)}
    props["Контакт передан"] = {"checkbox": checklist.get('external_contact_shared', False)}
    
    if profile.get('work_permit_status'):
        props["Разрешение на работу"] = {"select": {"name": profile['work_permit_status']}}
    
    if profile.get('code_95_status'):
        props["Код 95"] = {"select": {"name": profile['code_95_status']}}
    
    if profile.get('adr_status'):
        props["ADR"] = {"select": {"name": profile['adr_status']}}
    
    if profile.get('driver_card_status'):
        props["Карта водителя"] = {"select": {"name": profile['driver_card_status']}}
    
    if profile.get('license_categories'):
        props["Категории прав"] = {"multi_select": [{"name": cat} for cat in profile['license_categories']]}
    
    if profile.get('experience_months') is not None:
        props["Опыт (мес.)"] = {"number": profile['experience_months']}
    
    if profile.get('polish_language'):
        props["Польский язык"] = {"select": {"name": profile['polish_language']}}
    
    if profile.get('crew_type'):
        props["Тип экипажа"] = {"select": {"name": profile['crew_type']}}
    
    if profile.get('preferred_vehicle_types'):
        props["Типы техники"] = {"multi_select": [{"name": vt} for vt in profile['preferred_vehicle_types']]}
    
    if profile.get('preferred_regions'):
        props["Регионы работы"] = {"multi_select": [{"name": r} for r in profile['preferred_regions']]}
    
    if profile.get('route_type_preference'):
        props["Тип маршрутов"] = {"select": {"name": profile['route_type_preference']}}
    
    if profile.get('avoided_regions'):
        props["Исключённые регионы"] = {"multi_select": [{"name": r} for r in profile['avoided_regions']]}
    
    if profile.get('preferred_base_cities'):
        props["Города базы"] = {"multi_select": [{"name": c} for c in profile['preferred_base_cities']]}
    
    if profile.get('min_salary_expectation') is not None:
        props["Мин. зарплата (зл/день)"] = {"number": profile['min_salary_expectation']}
    
    if profile.get('citizenship'):
        props["Гражданство"] = {"multi_select": [{"name": c} for c in profile['citizenship']]}

    if profile.get('phone_number'):
        props["Номер телефона"] = {"rich_text": [{"text": {"content": profile['phone_number']}}]}

    return props


def create_driver_page(database_id, candidate):
    props = build_page_properties(candidate)
    
    data = {
        "parent": {"database_id": database_id},
        "properties": props
    }
    
    return notion_request("POST", "/pages", data)


def update_driver_page(page_id, candidate):
    props = build_page_properties(candidate, is_update=True)
    return notion_request("PATCH", f"/pages/{page_id}", {"properties": props})


def fetch_all_drivers(database_id):
    """Загружает все записи из базы и возвращает словарь {nickname: {page_id, messagesCount}}"""
    drivers = {}
    start_cursor = None
    
    while True:
        data = {"page_size": 100}
        if start_cursor:
            data["start_cursor"] = start_cursor
        
        result = notion_request("POST", f"/databases/{database_id}/query", data)
        if not result:
            break
        
        for page in result.get("results", []):
            nickname_prop = page.get("properties", {}).get("TikTok Nickname", {}).get("rich_text", [])
            if nickname_prop:
                nickname = nickname_prop[0].get("text", {}).get("content", "")
            else:
                title_prop = page.get("properties", {}).get("Name", {}).get("title", [])
                nickname = title_prop[0].get("text", {}).get("content", "") if title_prop else ""
            
            if nickname:
                messages_count = page.get("properties", {}).get("messagesCount", {}).get("number", 0) or 0
                drivers[nickname] = {
                    "page_id": page["id"],
                    "messagesCount": messages_count
                }
        
        if not result.get("has_more"):
            break
        start_cursor = result.get("next_cursor")
    
    return drivers


def upsert_driver(database_id, candidate, existing_drivers):
    """Создаёт или обновляет запись водителя. Возвращает (result, action, info)"""
    chat_name = candidate.get('chatName', '')
    current_messages = candidate.get('messagesCount', 0)
    
    if chat_name in existing_drivers:
        existing = existing_drivers[chat_name]
        existing_messages = existing.get('messagesCount', 0)
        
        if current_messages == existing_messages:
            return None, "skipped", None
        
        result = update_driver_page(existing['page_id'], candidate)
        if result:
            update_page_chat(existing['page_id'], chat_name)
        return result, "updated", None
    else:
        result = create_driver_page(database_id, candidate)
        if result and result.get('id'):
            update_page_chat(result['id'], chat_name)
        return result, "created", None


def import_drivers(database_id, batch_size=None):
    if not os.path.exists(CANDIDATE_ANALYSIS_FILE):
        print(f"❌ Файл {CANDIDATE_ANALYSIS_FILE} не найден")
        return
    
    with open(CANDIDATE_ANALYSIS_FILE, 'r', encoding='utf-8') as f:
        candidates = json.load(f)
    
    print(f"📥 Загружено {len(candidates)} кандидатов")
    
    if batch_size:
        candidates = candidates[:batch_size]
        print(f"📦 Лимит: {batch_size}")
    
    print("🔍 Загружаем существующие записи из Notion...")
    existing_drivers = fetch_all_drivers(database_id)
    print(f"📋 Найдено {len(existing_drivers)} существующих записей")
    
    print(f"\n🚀 Импорт {len(candidates)} водителей (батчи по 10)...")
    
    created = 0
    updated = 0
    skipped = 0
    errors = 0
    total = len(candidates)
    
    for batch_start in range(0, total, 10):
        batch = candidates[batch_start:batch_start + 10]
        batch_num = batch_start // 10 + 1
        total_batches = (total + 9) // 10
        
        print(f"\n📦 Батч {batch_num}/{total_batches}...")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(upsert_driver, database_id, c, existing_drivers): c 
                for c in batch
            }
            
            for future in as_completed(futures):
                candidate = futures[future]
                chat_name = candidate.get('chatName', 'unknown')
                
                try:
                    result, action, info = future.result()
                    if action == "skipped":
                        skipped += 1
                    elif action == "created" and result:
                        print(f"  ✅ {chat_name} (создан)")
                        created += 1
                    elif action == "updated" and result:
                        print(f"  🔄 {chat_name} (обновлён)")
                        updated += 1
                    else:
                        print(f"  ❌ {chat_name}")
                        errors += 1
                except Exception as e:
                    print(f"  ❌ {chat_name}: {e}")
                    errors += 1
        
        if batch_start + 10 < total:
            time.sleep(1)
    
    print(f"\n📊 Результат: ✅ создано {created} / 🔄 обновлено {updated} / ⏭️  без изменений {skipped} / ❌ ошибок {errors}")


def main():
    parser = argparse.ArgumentParser(description='Импорт водителей в Notion')
    parser.add_argument('--batch-size', type=int, help='Количество записей для импорта')
    
    args = parser.parse_args()
    import_drivers(DRIVERS_DB_ID, args.batch_size)


if __name__ == "__main__":
    main()

