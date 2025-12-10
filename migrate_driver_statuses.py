#!/usr/bin/env python3
"""
Скрипт для миграции статусов водителей из старой базы "Водители из тиктока"
в новую базу "Водители(переписки)" по TikTok username.

ИСПОЛЬЗОВАНИЕ:
  python3 migrate_driver_statuses.py [--dry-run]

ОПЦИИ:
  --dry-run  Показать что будет обновлено, но не вносить изменения
"""

import json
import os
import sys
import re
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv('NOTION_TOKEN')

OLD_DATABASE_ID = '2b895810-6f37-80e2-9d13-eb9ab88cb9c7'
NEW_DATABASE_ID = '2ba95810-6f37-815e-86f2-ed07436ca6b0'

STATUS_MAPPING = {
    'К работе': 'К работе',
    'Ждет новые вакансии': 'Ждет новых вакансий',
    'Высланы вакансии': 'Высланы вакансии',
    'В процесе найма': 'В процессе найма',
    'Нанят': 'Нанят',
    'Не отвечает': 'Не отвечает',
}

# Notion API rate limits: 3 requests/sec average
MAX_WORKERS = 3
RATE_LIMIT_DELAY = 0.35  # секунд между запросами (чуть больше 1/3 для запаса)
MAX_RETRIES = 3
RETRY_BACKOFF = 1.0  # начальная задержка при retry (секунды)

# Для thread-safe вывода
print_lock = Lock()

if not NOTION_TOKEN:
    print("❌ Ошибка: переменная окружения NOTION_TOKEN не установлена")
    print("Создайте файл .env и добавьте NOTION_TOKEN=your_token")
    sys.exit(1)


def extract_tiktok_username(url):
    """Извлекает username из TikTok URL"""
    if not url:
        return None
    match = re.search(r'tiktok\.com/@([^?/]+)', url)
    if match:
        return match.group(1).lower()
    return None


def fetch_all_pages(database_id, url_field, nickname_field=None):
    """Получает все страницы из базы данных с пагинацией"""
    all_pages = []
    start_cursor = None
    
    while True:
        url = f"https://api.notion.com/v1/databases/{database_id}/query"
        headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        request_data = {"page_size": 100}
        if start_cursor:
            request_data["start_cursor"] = start_cursor
        
        json_data = json.dumps(request_data).encode('utf-8')
        req = urllib.request.Request(url, data=json_data, headers=headers, method='POST')
        
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
            
            for page in result.get('results', []):
                page_id = page.get('id')
                properties = page.get('properties', {})
                
                username = None
                if nickname_field:
                    nickname_prop = properties.get(nickname_field, {}).get('rich_text', [])
                    if nickname_prop:
                        username = nickname_prop[0].get('text', {}).get('content', '').lower()
                
                if not username:
                    url_prop = properties.get(url_field, {})
                    tiktok_url = url_prop.get('url')
                    username = extract_tiktok_username(tiktok_url)
                
                status_prop = properties.get('Status', {})
                status_data = status_prop.get('status')
                status_name = status_data.get('name') if status_data else None
                
                url_prop = properties.get(url_field, {})
                tiktok_url = url_prop.get('url')
                
                if username:
                    all_pages.append({
                        'page_id': page_id,
                        'username': username,
                        'status': status_name,
                        'url': tiktok_url
                    })
            
            if result.get('has_more'):
                start_cursor = result.get('next_cursor')
            else:
                break
                
        except urllib.error.HTTPError as e:
            print(f"❌ Ошибка HTTP {e.code}")
            try:
                error_data = json.loads(e.read().decode('utf-8'))
                print(f"Ответ: {error_data}")
            except:
                pass
            return None
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None
    
    return all_pages


def update_page_status(page_id, new_status, retries=MAX_RETRIES):
    """Обновляет статус страницы с retry логикой для rate limits"""
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    request_data = {
        "properties": {
            "Status": {
                "status": {
                    "name": new_status
                }
            }
        }
    }
    
    json_data = json.dumps(request_data).encode('utf-8')
    
    for attempt in range(retries):
        req = urllib.request.Request(url, data=json_data, headers=headers, method='PATCH')
        
        try:
            with urllib.request.urlopen(req) as response:
                return {'success': True, 'page_id': page_id}
        except urllib.error.HTTPError as e:
            if e.code == 429:
                # Rate limit - ждём и пробуем снова
                retry_after = e.headers.get('Retry-After', RETRY_BACKOFF * (attempt + 1))
                try:
                    retry_after = float(retry_after)
                except:
                    retry_after = RETRY_BACKOFF * (attempt + 1)
                
                if attempt < retries - 1:
                    time.sleep(retry_after)
                    continue
            
            error_msg = ''
            try:
                error_data = json.loads(e.read().decode('utf-8'))
                error_msg = error_data.get('message', '')
            except:
                pass
            return {'success': False, 'page_id': page_id, 'error': f"HTTP {e.code}: {error_msg}"}
        except Exception as e:
            return {'success': False, 'page_id': page_id, 'error': str(e)}
    
    return {'success': False, 'page_id': page_id, 'error': 'Max retries exceeded'}


def main():
    dry_run = '--dry-run' in sys.argv
    
    if dry_run:
        print("🔍 Режим просмотра (--dry-run): изменения не будут внесены\n")
    
    print("📥 Загрузка данных из старой базы 'Водители из тиктока'...")
    old_pages = fetch_all_pages(OLD_DATABASE_ID, 'URL')
    if old_pages is None:
        print("❌ Не удалось загрузить данные из старой базы")
        sys.exit(1)
    print(f"✅ Загружено {len(old_pages)} записей\n")
    
    print("📥 Загрузка данных из новой базы 'Водители(переписки)'...")
    new_pages = fetch_all_pages(NEW_DATABASE_ID, 'TikTok URL', 'TikTok Nickname')
    if new_pages is None:
        print("❌ Не удалось загрузить данные из новой базы")
        sys.exit(1)
    print(f"✅ Загружено {len(new_pages)} записей\n")
    
    new_pages_map = {p['username']: p for p in new_pages}
    
    updates = []
    not_found = []
    no_mapping = []
    
    for old_page in old_pages:
        username = old_page['username']
        old_status = old_page['status']
        
        if username not in new_pages_map:
            not_found.append(old_page)
            continue
        
        new_page = new_pages_map[username]
        
        if old_status not in STATUS_MAPPING:
            no_mapping.append({
                'username': username,
                'old_status': old_status
            })
            continue
        
        new_status = STATUS_MAPPING[old_status]
        current_new_status = new_page['status']
        
        if current_new_status != new_status:
            updates.append({
                'page_id': new_page['page_id'],
                'username': username,
                'old_status': old_status,
                'new_status': new_status,
                'current_status': current_new_status
            })
    
    print(f"📊 Результаты анализа:")
    print(f"  Найдено совпадений: {len(old_pages) - len(not_found)}")
    print(f"  Требуется обновить: {len(updates)}")
    print(f"  Не найдено в новой базе: {len(not_found)}")
    if no_mapping:
        print(f"  Неизвестные статусы: {len(no_mapping)}")
    print()
    
    if updates:
        print("📝 Обновления статусов:")
        for u in updates:
            print(f"  @{u['username']}: '{u['current_status']}' → '{u['new_status']}' (было в старой: '{u['old_status']}')")
        print()
    
    if not_found:
        print("⚠️  Не найдены в новой базе:")
        for p in not_found[:10]:
            print(f"  @{p['username']} (статус: {p['status']})")
        if len(not_found) > 10:
            print(f"  ... и ещё {len(not_found) - 10}")
        print()
    
    if no_mapping:
        print("⚠️  Неизвестные статусы (нет маппинга):")
        for item in no_mapping:
            print(f"  @{item['username']}: '{item['old_status']}'")
        print()
    
    if not updates:
        print("✅ Нет изменений для применения")
        return
    
    if dry_run:
        print("ℹ️  Запустите без --dry-run для применения изменений")
        return
    
    print(f"🔄 Применение {len(updates)} обновлений (батчинг: {MAX_WORKERS} потоков, ~3 req/sec)...")
    success_count = 0
    error_count = 0
    errors = []
    
    # Создаём словарь для быстрого поиска username по page_id
    page_to_user = {u['page_id']: u['username'] for u in updates}
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        
        # Отправляем задачи с задержкой для соблюдения rate limit
        for i, u in enumerate(updates):
            future = executor.submit(update_page_status, u['page_id'], u['new_status'])
            futures[future] = u
            
            # Задержка между отправками (кроме последней)
            if i < len(updates) - 1:
                time.sleep(RATE_LIMIT_DELAY)
        
        # Собираем результаты
        completed = 0
        for future in as_completed(futures):
            completed += 1
            u = futures[future]
            result = future.result()
            
            with print_lock:
                if result['success']:
                    print(f"  [{completed}/{len(updates)}] @{u['username']} ✅")
                    success_count += 1
                else:
                    print(f"  [{completed}/{len(updates)}] @{u['username']} ❌ {result.get('error', '')}")
                    error_count += 1
                    errors.append({'username': u['username'], 'error': result.get('error', '')})
    
    elapsed = time.time() - start_time
    
    print(f"\n📊 Итоги:")
    print(f"  Успешно обновлено: {success_count}")
    if error_count:
        print(f"  Ошибки: {error_count}")
    print(f"  Время выполнения: {elapsed:.1f} сек ({len(updates)/elapsed:.1f} req/sec)")
    
    if errors:
        print(f"\n⚠️  Ошибки при обновлении:")
        for err in errors[:10]:
            print(f"  @{err['username']}: {err['error']}")
        if len(errors) > 10:
            print(f"  ... и ещё {len(errors) - 10}")


if __name__ == "__main__":
    main()

