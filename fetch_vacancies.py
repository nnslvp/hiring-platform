#!/usr/bin/env python3
"""
Скрипт для получения ID всех вакансий и содержимого их вложенных документов из Notion

ИСПОЛЬЗОВАНИЕ:
  python3 fetch_vacancies.py [output_file.json]

ПО УМОЛЧАНИЮ:
  Сохраняет данные в файл vacancies.json в текущей директории
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
DATABASE_ID = '27c95810-6f37-8024-b175-d15ffe28f383'

if not NOTION_TOKEN:
    print("❌ Ошибка: переменная окружения NOTION_TOKEN не установлена")
    print("Создайте файл .env на основе .env.example и заполните ключи")
    sys.exit(1)

def get_child_pages(page_id):
    """Получает ID всех вложенных страниц (child_page) для указанной страницы"""
    child_page_ids = []
    start_cursor = None
    
    while True:
        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        params = {"page_size": 100}
        if start_cursor:
            params["start_cursor"] = start_cursor
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{url}?{query_string}" if query_string else url
        
        req = urllib.request.Request(full_url, headers=headers, method='GET')
        
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
            
            blocks = result.get('results', [])
            
            for block in blocks:
                if block.get('type') == 'child_page':
                    child_page_ids.append(block.get('id'))
            
            has_more = result.get('has_more', False)
            if has_more:
                start_cursor = result.get('next_cursor')
            else:
                break
                
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return []
            print(f"⚠️  Ошибка при получении дочерних страниц для {page_id}: HTTP {e.code}")
            return []
        except Exception as e:
            print(f"⚠️  Ошибка при получении дочерних страниц для {page_id}: {e}")
            return []
    
    return child_page_ids

def get_block_children(block_id):
    """Получает дочерние блоки для указанного блока с пагинацией"""
    all_blocks = []
    start_cursor = None
    
    while True:
        url = f"https://api.notion.com/v1/blocks/{block_id}/children"
        headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        params = {"page_size": 100}
        if start_cursor:
            params["start_cursor"] = start_cursor
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{url}?{query_string}" if query_string else url
        
        req = urllib.request.Request(full_url, headers=headers, method='GET')
        
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
            
            blocks = result.get('results', [])
            all_blocks.extend(blocks)
            
            has_more = result.get('has_more', False)
            if has_more:
                start_cursor = result.get('next_cursor')
            else:
                break
                
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return []
            return []
        except Exception as e:
            return []
    
    return all_blocks

def get_page_content(page_id):
    """Получает все блоки страницы с пагинацией"""
    all_blocks = []
    start_cursor = None
    
    while True:
        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        params = {"page_size": 100}
        if start_cursor:
            params["start_cursor"] = start_cursor
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{url}?{query_string}" if query_string else url
        
        req = urllib.request.Request(full_url, headers=headers, method='GET')
        
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
            
            blocks = result.get('results', [])
            all_blocks.extend(blocks)
            
            has_more = result.get('has_more', False)
            if has_more:
                start_cursor = result.get('next_cursor')
            else:
                break
                
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return []
            print(f"⚠️  Ошибка при получении содержимого страницы {page_id}: HTTP {e.code}")
            return []
        except Exception as e:
            print(f"⚠️  Ошибка при получении содержимого страницы {page_id}: {e}")
            return []
    
    return all_blocks

def extract_text_from_blocks(blocks):
    """Извлекает чистый текст из блоков Notion с рекурсивной обработкой"""
    text_lines = []
    
    for block in blocks:
        block_type = block.get('type')
        if not block_type:
            continue
        
        block_id = block.get('id')
        block_data = block.get(block_type, {})
        
        if block_type == 'table':
            child_blocks = get_block_children(block_id)
            table_rows = []
            for row_block in child_blocks:
                if row_block.get('type') == 'table_row':
                    row_data = row_block.get('table_row', {})
                    cells = row_data.get('cells', [])
                    row_texts = []
                    for cell in cells:
                        cell_text = ''.join([rt.get('plain_text', '') for rt in cell if rt.get('type') == 'text'])
                        row_texts.append(cell_text)
                    table_rows.append(' | '.join(row_texts))
            if table_rows:
                text_lines.append('\n'.join(table_rows))
        elif block_type in ['bulleted_list_item', 'numbered_list_item', 'to_do', 'toggle']:
            rich_text = block_data.get('rich_text', [])
            block_text = ''.join([rt.get('plain_text', '') for rt in rich_text if rt.get('type') == 'text'])
            if block_text:
                text_lines.append(block_text)
            
            has_children = block.get('has_children', False)
            if has_children:
                child_blocks = get_block_children(block_id)
                child_text = extract_text_from_blocks(child_blocks)
                if child_text:
                    text_lines.append(child_text)
        else:
            rich_text = block_data.get('rich_text', [])
            if rich_text:
                block_text = ''.join([rt.get('plain_text', '') for rt in rich_text if rt.get('type') == 'text'])
                if block_text:
                    text_lines.append(block_text)
            
            has_children = block.get('has_children', False)
            if has_children:
                child_blocks = get_block_children(block_id)
                child_text = extract_text_from_blocks(child_blocks)
                if child_text:
                    text_lines.append(child_text)
    
    return '\n'.join(text_lines)

def extract_status(page):
    """Извлекает статус из свойств страницы"""
    properties = page.get('properties', {})
    status_prop = properties.get('Status', {})
    if status_prop.get('type') == 'status':
        status_data = status_prop.get('status')
        if status_data:
            return status_data.get('name')
    return None

def fetch_all_vacancies():
    """Получает все вакансии из базы данных с пагинацией"""
    all_pages = []
    start_cursor = None
    
    while True:
        url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
        headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        request_data = {
            "page_size": 100
        }
        
        if start_cursor:
            request_data["start_cursor"] = start_cursor
        
        json_data = json.dumps(request_data).encode('utf-8')
        req = urllib.request.Request(url, data=json_data, headers=headers, method='POST')
        
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
            
            results = result.get('results', [])
            
            for page in results:
                all_pages.append({
                    'id': page.get('id'),
                    'status': extract_status(page)
                })
            
            has_more = result.get('has_more', False)
            if has_more:
                start_cursor = result.get('next_cursor')
            else:
                break
                
        except urllib.error.HTTPError as e:
            print(f"❌ Ошибка HTTP {e.code}")
            try:
                error_data = json.loads(e.read().decode('utf-8'))
                print(f"Ответ: {error_data}")
            except:
                print(f"Ответ: {e.read().decode('utf-8', errors='ignore')}")
            return None
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None
    
    return all_pages

def main():
    output_file = sys.argv[1] if len(sys.argv) > 1 else 'vacancies.json'
    
    print(f"📥 Получение вакансий из Notion...")
    pages = fetch_all_vacancies()
    
    if pages is None:
        print("❌ Не удалось получить вакансии")
        sys.exit(1)
    
    print(f"✅ Получено {len(pages)} вакансий")
    print(f"📥 Получение вложенных документов и их содержимого...")
    
    vacancies_data = []
    
    for i, page_info in enumerate(pages, 1):
        page_id = page_info['id']
        status = page_info['status']
        print(f"  Обработка {i}/{len(pages)}: {page_id[:8]}... (статус: {status})")
        child_page_ids = get_child_pages(page_id)
        
        child_pages_content = []
        for child_page_id in child_page_ids:
            print(f"    Получение содержимого вложенного документа {child_page_id[:8]}...")
            blocks = get_page_content(child_page_id)
            text_content = extract_text_from_blocks(blocks)
            child_pages_content.append({
                "page_id": child_page_id,
                "content": text_content
            })
        
        vacancy = {
            "page_id": page_id,
            "status": status,
            "child_pages": child_pages_content
        }
        
        vacancies_data.append(vacancy)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(vacancies_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Данные сохранены в файл: {output_file}")
    
    total_child_pages = sum(len(v.get('child_pages', [])) for v in vacancies_data)
    status_counts = {}
    for v in vacancies_data:
        status = v.get('status') or 'Не указан'
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print(f"\n📊 Статистика:")
    print(f"  Всего вакансий: {len(vacancies_data)}")
    print(f"  Всего вложенных документов: {total_child_pages}")
    print(f"  Вакансий с вложенными документами: {sum(1 for v in vacancies_data if v.get('child_pages'))}")
    print(f"\n📋 По статусам:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

if __name__ == "__main__":
    main()

