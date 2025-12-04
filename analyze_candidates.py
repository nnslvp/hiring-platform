#!/usr/bin/env python3
"""
Анализатор профилей кандидатов из переписок TikTok

ИСПОЛЬЗОВАНИЕ:
  python3 analyze_candidates.py [--batch-size N] [--start-from N] [--parallel N] [--messages-dir DIR] [--output FILE]
  python3 analyze_candidates.py --tiktok-export FILE [--batch-size N] [--start-from N] [--parallel N] [--output FILE] [--fresh]

ПАРАМЕТРЫ:
  --batch-size N       Количество чатов для обработки за раз (по умолчанию: 50)
  --start-from N       Начать с чата номер N (по умолчанию: 0)
  --parallel N         Количество параллельных запросов (по умолчанию: 5)
  --messages-dir DIR   Папка с переписками (по умолчанию: TickTokDMParser/exported_messages)
  --tiktok-export FILE Файл экспорта данных TikTok (user_data_tiktok.json)
  --output FILE        Выходной файл (по умолчанию: candidate_analysis.json)
  --fresh              Начать анализ с нуля, игнорируя существующие результаты

ПРИМЕР:
  python3 analyze_candidates.py --batch-size 100 --parallel 5
  python3 analyze_candidates.py --tiktok-export user_data_tiktok.json --fresh --batch-size 100
"""

import json
import os
import sys
import argparse
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv

from field_definitions import (
    LICENSE_CATEGORIES,
    DOCUMENT_STATUS,
    CREW_TYPE,
    POLISH_LEVEL,
    VEHICLE_TYPES,
    ROUTE_TYPE,
)

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
RECRUITER_ACCOUNT = 'rabotazarulem'

if not OPENAI_API_KEY:
    print("❌ Ошибка: переменная окружения OPENAI_API_KEY не установлена")
    sys.exit(1)

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "checklist": {
            "type": "object",
            "description": "Чек-лист работы менеджера с лидом",
            "properties": {
                "has_work_permit_in_poland": {
                    "type": "boolean",
                    "description": "У кандидата есть разрешение на работу в Польше (виза/ВНЖ)"
                },
                "preferences_provided": {
                    "type": "boolean",
                    "description": "Кандидат описал свои пожелания по работе"
                },
                "vacancy_offered": {
                    "type": "boolean",
                    "description": "Менеджер отправил полную вакансию с деталями"
                },
                "vacancy_accepted": {
                    "type": "boolean",
                    "description": "Кандидат явно согласился на вакансию"
                },
                "external_contact_shared": {
                    "type": "boolean",
                    "description": "Был передан реальный контакт (номер/username)"
                }
            },
            "required": [
                "has_work_permit_in_poland",
                "preferences_provided",
                "vacancy_offered",
                "vacancy_accepted",
                "external_contact_shared"
            ],
            "additionalProperties": False
        },
        "profile": {
            "type": "object",
            "description": "Профиль кандидата для матчинга с вакансиями",
            "properties": {
                "work_permit_status": {
                    "type": ["string", "null"],
                    "enum": DOCUMENT_STATUS + [None],
                    "description": "Статус разрешения на работу в Польше"
                },
                "code_95_status": {
                    "type": ["string", "null"],
                    "enum": DOCUMENT_STATUS + [None],
                    "description": "Статус свидетельства квалификации (код 95)"
                },
                "adr_status": {
                    "type": ["string", "null"],
                    "enum": DOCUMENT_STATUS + [None],
                    "description": "Статус ADR (опасные грузы)"
                },
                "driver_card_status": {
                    "type": ["string", "null"],
                    "enum": DOCUMENT_STATUS + [None],
                    "description": "Статус карты водителя для тахографа"
                },
                "license_categories": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": LICENSE_CATEGORIES
                    },
                    "description": "Категории водительских прав"
                },
                "experience_months": {
                    "type": ["integer", "null"],
                    "description": "Опыт работы в месяцах"
                },
                "polish_language": {
                    "type": ["string", "null"],
                    "enum": POLISH_LEVEL + [None],
                    "description": "Уровень владения польским языком"
                },
                "crew_type": {
                    "type": ["string", "null"],
                    "enum": CREW_TYPE + [None],
                    "description": "Предпочитаемый тип экипажа"
                },
                "preferred_vehicle_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": VEHICLE_TYPES
                    },
                    "description": "Предпочитаемые типы техники"
                },
                "preferred_regions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Желаемые регионы работы"
                },
                "route_type_preference": {
                    "type": ["string", "null"],
                    "enum": ROUTE_TYPE + [None],
                    "description": "Предпочтение по типу маршрутов: внутренние (только Польша) или международные"
                },
                "avoided_regions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Исключённые регионы"
                },
                "preferred_base_cities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Предпочтения по локации базы"
                },
                "min_salary_expectation": {
                    "type": ["integer", "null"],
                    "description": "Минимальная ожидаемая ставка (злотых/день)"
                },
                "citizenship": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Гражданство кандидата (страны)"
                }
            },
            "required": [
                "work_permit_status",
                "code_95_status",
                "adr_status",
                "driver_card_status",
                "license_categories",
                "experience_months",
                "polish_language",
                "crew_type",
                "preferred_vehicle_types",
                "preferred_regions",
                "route_type_preference",
                "avoided_regions",
                "preferred_base_cities",
                "min_salary_expectation",
                "citizenship"
            ],
            "additionalProperties": False
        }
    },
    "required": ["checklist", "profile"],
    "additionalProperties": False
}

SYSTEM_PROMPT = f"""Ты эксперт по анализу переписок в рекрутинге водителей на польский рынок.

Рекрутер = аккаунт "{RECRUITER_ACCOUNT}". Все сообщения от этого автора — это менеджер.
Все остальные авторы — кандидат (водитель).

Твоя задача — извлечь два блока данных:

═══════════════════════════════════════════════════════════════════════════════
БЛОК 1: CHECKLIST (работа менеджера с лидом)
═══════════════════════════════════════════════════════════════════════════════

Для каждого события ставь true или false:

1. has_work_permit_in_poland — у кандидата есть разрешение на работу в ПОЛЬШЕ
   ✅ true если:
      - Прямо: "У меня польская виза", "Есть ВНЖ Польши", "Карта побыту", "сталый побыт"
      - Косвенно: "Работаю в Польше 6 лет", "В Польше уже", "Живу в Польше"
      - География: "В близи Белостока", "Возле Варшавы", живёт в польском городе
   ❌ false если:
      - Виза ДРУГОЙ страны: "латвийская виза", "литовская виза", "чешская виза"
      - Из СНГ без упоминания польских документов
   
   ВАЖНО: Виза другой страны ЕС (Латвия, Литва, Чехия) НЕ даёт права работать в Польше!

2. preferences_provided — кандидат описал пожелания по работе
   ✅ true если:
      - Тип работы: "Ищу работу на тент", "на шторе", "реф"
      - Зарплата: "Зарплата от 400", "ищу зарплату"
      - Регионы: "Не хочу в Англию", "только по Европе"
      - График: "график 3/1", "хочу домой раз в месяц"
   ❌ false если: только общий вопрос "какие условия?" без уточнений

3. vacancy_offered — менеджер отправил ПОЛНУЮ вакансию с детальным описанием
   ✅ true если (минимум 2-3 параметра):
      - "Вакансия в городе Łódź, Renault Master, график 4/1"
      - "В Познани, Daf XF (тент), 100€/день"
   ❌ false если: "Стартует от 95€" (мало деталей), "Могу выслать варианты"

4. vacancy_accepted — кандидат явно согласился на вакансию
   ✅ true если: "Готов", "Давайте попробуем", "Меня устраивает"
   ❌ false если: "Да вышлите" (просьба, а не согласие)

5. external_contact_shared — кто-то дал РЕАЛЬНЫЙ контакт
   ✅ true если: "+48 573 899 403", "@username"
   ❌ false если: "Могу дать контакт Игоря" (нет самого контакта)

═══════════════════════════════════════════════════════════════════════════════
БЛОК 2: PROFILE (данные кандидата для матчинга)
═══════════════════════════════════════════════════════════════════════════════

Извлеки данные ТОЛЬКО из того, что ЯВНО сказал или подтвердил КАНДИДАТ.
Если информация не упоминается — ставь null для строк/чисел, [] для массивов.

═══ ДОКУМЕНТЫ (статус: "есть" / "в процессе" / "нет" / null) ═══

1. work_permit_status — разрешение на работу в ПОЛЬШЕ
   • "есть": ТОЛЬКО польская виза/ВНЖ/карта побыту, "работаю в Польше X лет",
     "сталый побыт", "польская виза", живёт в польском городе (Варшава, Лодзь и т.д.)
   • "в процессе": "подал на польскую визу", "жду польскую визу", "оформляю документы в Польшу"
   • "нет": виза ДРУГОЙ страны (латвийская, литовская, чешская и т.д.),
     явно говорит что нет польской визы, из СНГ без упоминания польских документов
   • null: не упоминается
   
   ВАЖНО: Виза другой страны ЕС (Латвия, Литва, Чехия) НЕ даёт права работать в Польше!
   "латвийская виза", "литовская виза", "чешская виза" → "нет"

2. code_95_status — код 95 (свидетельство квалификации)
   • "есть": "код 95 есть"
   • "в процессе": "делаю код 95", "код 95 в конце месяца"
   • "нет": "кода 95 нет"
   • null: не упоминается

3. adr_status — ADR (опасные грузы)
   • "есть": "ADR есть"
   • "в процессе": "ADR делаю", "ADR будет"
   • "нет": "ADR нет", отказ от вакансии из-за ADR
   • null: не упоминается

4. driver_card_status — карта водителя (чип для тахографа)
   • "есть": "чип есть", "карта водителя есть"
   • "в процессе": "чип делаю"
   • "нет": "нет карты"
   • null: не упоминается

═══ КВАЛИФИКАЦИЯ ═══

5. license_categories — категории прав (массив)
   • Допустимые значения: {', '.join(LICENSE_CATEGORIES)}
   
   КРИТИЧЕСКИ ВАЖНО — КИРИЛЛИЦА vs ЛАТИНИЦА:
   Водители часто пишут категории КИРИЛЛИЦЕЙ (русскими буквами):
   • В (кириллица) = B (латиница)
   • С (кириллица) = C (латиница)
   • Е (кириллица) = E (латиница)
   
   СЛИТНОЕ НАПИСАНИЕ — РАЗДЕЛЯЙ НА ОТДЕЛЬНЫЕ КАТЕГОРИИ:
   • "ВС", "BC", "вс", "bc" → ["B", "C"] (ДВЕ категории!)
   • "СЕ", "CE", "се", "ce", "C+E", "С+Е" → ["CE"] (одна категория CE)
   • "ВСЕ", "BCE" → ["B", "CE"] (B + CE, не три буквы!)
   • "всд", "BCD" → ["B", "C", "D"]
   
   ДРУГИЕ ФОРМАТЫ:
   • "категория CE" → ["CE"]
   • "C и CE", "С и СЕ" → ["C", "CE"]
   • "права C" → ["C"]
   • [] если не указано
   
   ВАЖНО: Всегда возвращай латинские буквы в результате!

6. experience_months — опыт работы (число или null)
   • "6 лет" → 72
   • "полтора года" → 18
   • "7 лет стажа" → 84
   • null если не указано

7. polish_language — владение польским
   • "свободный": "польский в совершенстве", "свободно говорю по-польски"
   • "базовый": "базовый польский", "на коммуникативном уровне"
   • "нет": "не говорю по-польски"
   • null: не упоминается

═══ ПРЕДПОЧТЕНИЯ ПО РАБОТЕ ═══

8. crew_type — тип экипажа
   • "парный": "парный экипаж", "в двойке", "семейный экипаж", "я и жена", "муж и жена"
   • "соло": явно говорит что предпочитает один
   • null: не указано
   ВАЖНО: "семейный экипаж" = "парный" (два водителя)

9. preferred_vehicle_types — тип техники (массив)
   Допустимые значения: {', '.join(VEHICLE_TYPES)}
   • тент, штора, firanka → "Тент"
   • реф, рефрижератор, холодильник, chłodnia → "Реф (рефрижератор)"
   • [] если не указано или "без разницы"

10. preferred_regions — желаемые регионы (массив)
    • "по Европе", "вся Европа" → ["По всей Европе"]
    • "Германия, Франция" → ["Германия", "Франция"]
    • "внутри Польши" → ["Польша"]
    • [] если не указано
    ВАЖНО: Используй точные названия стран на русском

11. route_type_preference — предпочтение по типу маршрутов
    • "внутренние": "только по Польше", "не международный", "внутри страны", "край", "хочу быть чаще дома"
    • "международные": "по Европе", "международные рейсы", "по ЕС"
    • null: не указано или "без разницы"
    ВАЖНО: Если кандидат явно говорит "не хочу международку" или "только Польша" → "внутренние"

12. avoided_regions — исключённые регионы (массив)
    • "без Англии", "не хочу в UK" → ["Англия"]
    • [] если нет исключений

13. preferred_base_cities — предпочтения по базе (массив)
    • "Варшава или Познань" → ["Варшава", "Познань"]
    • [] если не указано

═══ ОЖИДАНИЯ ПО ОПЛАТЕ ═══

14. min_salary_expectation — минимальная ставка (число или null)
    • "от 400 злотых" → 400
    • null если не указано

═══ ГРАЖДАНСТВО ═══

15. citizenship — гражданство кандидата (массив)
    • "украинец", "гражданин Украины" → ["Украина"]
    • "белорус" → ["Беларусь"]
    • "из России", "россиянин" → ["Россия"]
    • "молдаванин" → ["Молдова"]
    • "грузин" → ["Грузия"]
    • "казах" → ["Казахстан"]
    • "узбек" → ["Узбекистан"]
    • "таджик" → ["Таджикистан"]
    • "азербайджанец" → ["Азербайджан"]
    • двойное гражданство → ["Украина", "Польша"]
    • [] если не упоминается
    ВАЖНО: Полное название страны на русском языке
"""


def read_chat_files(messages_dir):
    """Читает все файлы переписок из директории"""
    files = []
    for filename in sorted(os.listdir(messages_dir)):
        if filename.endswith('.json') and filename != 'export_summary.json':
            filepath = os.path.join(messages_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    files.append({
                        'fileName': filename,
                        'chatName': content.get('chatName', filename.replace('.json', '')),
                        'messages': content.get('messages', [])
                    })
            except (json.JSONDecodeError, IOError) as e:
                print(f"  ⚠️  Ошибка чтения {filename}: {e}")
    return files


def read_tiktok_export(filepath):
    """Читает файл экспорта TikTok и преобразует в формат чатов"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    chat_history = data.get('Direct Message', {}).get('Direct Messages', {}).get('ChatHistory', {})
    
    chats = []
    for chat_key, messages in chat_history.items():
        chat_name = chat_key.replace('Chat History with ', '').rstrip(':')
        
        converted_messages = []
        for msg in reversed(messages):
            converted_messages.append({
                'time': msg.get('Date', ''),
                'author': msg.get('From', ''),
                'text': msg.get('Content', '')
            })
        
        chats.append({
            'fileName': f"{chat_name}.json",
            'chatName': chat_name,
            'messages': converted_messages
        })
    
    chats.sort(key=lambda x: x['chatName'].lower())
    return chats


def format_messages(messages):
    """Форматирует сообщения для анализа"""
    formatted = []
    for idx, msg in enumerate(messages, 1):
        time_str = msg.get('time', 'no time')
        author = msg.get('author', 'unknown')
        text = msg.get('text', '')
        formatted.append(f"#{idx} [{time_str}] {author}: {text}")
    return '\n'.join(formatted)


async def analyze_chat_async(chat_name, messages_text):
    """Асинхронно вызывает GPT API для анализа переписки"""
    user_message = f"Переписка с кандидатом {chat_name}:\n\n{messages_text}"

    try:
        response = await client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "candidate_analysis",
                    "strict": True,
                    "schema": RESPONSE_SCHEMA
                }
            }
        )

        content = response.choices[0].message.content
        return json.loads(content)

    except Exception as e:
        return {'error': str(e)}


async def process_batch(chats_batch, total_chats, start_offset):
    """Обрабатывает батч чатов параллельно"""
    tasks = []
    valid_chats = []

    for idx, chat in enumerate(chats_batch):
        if len(chat['messages']) < 2:
            print(f"  ⚠️  {start_offset + idx + 1}/{total_chats}: {chat['chatName']} — мало сообщений")
            continue
        
        messages_text = format_messages(chat['messages'])
        tasks.append(analyze_chat_async(chat['chatName'], messages_text))
        valid_chats.append((idx, chat))

    if not tasks:
        return []

    results = await asyncio.gather(*tasks)
    
    processed = []
    for (idx, chat), analysis in zip(valid_chats, results):
        if 'error' in analysis:
            print(f"  ❌ {start_offset + idx + 1}/{total_chats}: {chat['chatName']} — {analysis['error']}")
            continue
            
        result = {
            'chatName': chat['chatName'],
            'fileName': chat['fileName'],
            'messagesCount': len(chat['messages']),
            'checklist': analysis.get('checklist', {}),
            'profile': analysis.get('profile', {})
        }
        
        checklist_true = sum(1 for v in result['checklist'].values() if v is True)
        profile_filled = sum(1 for v in result['profile'].values() if v is not None and v != [])
        print(f"  ✅ {start_offset + idx + 1}/{total_chats}: {chat['chatName']} — checklist: {checklist_true}/5, profile: {profile_filled}/13")
        
        processed.append(result)
    
    return processed


async def main_async(args):
    if args.tiktok_export:
        if not os.path.exists(args.tiktok_export):
            print(f"❌ Файл {args.tiktok_export} не найден")
            sys.exit(1)
        print(f"📥 Загрузка переписок из TikTok экспорта {args.tiktok_export}...")
        chats = read_tiktok_export(args.tiktok_export)
    else:
        if not os.path.exists(args.messages_dir):
            print(f"❌ Папка {args.messages_dir} не найдена")
            sys.exit(1)
        print(f"📥 Загрузка переписок из {args.messages_dir}...")
        chats = read_chat_files(args.messages_dir)
    
    total_chats = len(chats)
    print(f"✅ Найдено {total_chats} переписок")

    existing_results = {}
    if not args.fresh and os.path.exists(args.output):
        try:
            with open(args.output, 'r', encoding='utf-8') as f:
                existing = json.load(f)
                for item in existing:
                    existing_results[item['fileName']] = item
            print(f"📂 Загружено {len(existing_results)} существующих результатов")
        except:
            pass
    elif args.fresh:
        print("🔄 Режим --fresh: начинаем анализ с нуля")

    start_idx = args.start_from
    end_idx = min(start_idx + args.batch_size, total_chats)

    if start_idx >= total_chats:
        print(f"❌ Индекс начала ({start_idx}) >= количества чатов ({total_chats})")
        sys.exit(1)

    # Фильтруем уже обработанные (пропускаем если нет новых сообщений)
    chats_to_process = []
    for idx in range(start_idx, end_idx):
        chat = chats[idx]
        current_count = len(chat['messages'])
        
        if chat['fileName'] in existing_results:
            existing = existing_results[chat['fileName']]
            existing_count = existing.get('messagesCount', 0)
            
            if current_count <= existing_count:
                print(f"⏭️  {idx + 1}/{total_chats}: {chat['chatName']} — нет новых сообщений ({current_count})")
                continue
            else:
                print(f"🔄 {idx + 1}/{total_chats}: {chat['chatName']} — новые сообщения ({existing_count} → {current_count})")
        
        chats_to_process.append((idx, chat))

    if not chats_to_process:
        print("\n✅ Все чаты в диапазоне уже обработаны")
        return

    print(f"\n🔄 Обработка {len(chats_to_process)} чатов (параллельно по {args.parallel})")
    print(f"📂 Результаты: {args.output}\n")

    results = list(existing_results.values())
    success_count = 0
    error_count = 0

    # Обрабатываем параллельными батчами
    for i in range(0, len(chats_to_process), args.parallel):
        batch_items = chats_to_process[i:i + args.parallel]
        batch_chats = [chat for _, chat in batch_items]
        batch_start = batch_items[0][0]
        
        batch_results = await process_batch(batch_chats, total_chats, batch_start)
        
        for result in batch_results:
            results.append(result)
            existing_results[result['fileName']] = result
            success_count += 1
        
        error_count += len(batch_chats) - len(batch_results)
        
        # Сохраняем после каждого батча
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # Задержка между батчами для rate limit
        if i + args.parallel < len(chats_to_process):
            await asyncio.sleep(5)

    print(f"\n📊 Статистика:")
    print(f"  ✅ Успешно: {success_count}")
    print(f"  ❌ Ошибок: {error_count}")
    print(f"  📦 Всего в файле: {len(results)}")

    if end_idx < total_chats:
        print(f"\n💡 Следующий батч:")
        print(f"   python3 analyze_candidates.py --start-from {end_idx} --batch-size {args.batch_size}")
    else:
        print(f"\n🎉 Все переписки обработаны!")


def main():
    parser = argparse.ArgumentParser(description='Анализатор профилей кандидатов')
    parser.add_argument('--batch-size', type=int, default=50, help='Количество чатов для обработки за раз')
    parser.add_argument('--start-from', type=int, default=0, help='Начать с чата номер N')
    parser.add_argument('--parallel', type=int, default=5, help='Количество параллельных запросов')
    parser.add_argument('--messages-dir', default='TickTokDMParser/exported_messages', help='Папка с переписками')
    parser.add_argument('--tiktok-export', help='Файл экспорта данных TikTok (user_data_tiktok.json)')
    parser.add_argument('--output', default='candidate_analysis.json', help='Выходной файл')
    parser.add_argument('--fresh', action='store_true', help='Начать анализ с нуля, игнорируя существующие результаты')

    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
