# Схема базы данных "Водители"

**Database ID:** `2ba95810-6f37-815e-86f2-ed07436ca6b0`

## Создание базы через MCP

```json
{
  "parent": {"type": "page_id", "page_id": "PARENT_PAGE_ID"},
  "title": [{"type": "text", "text": {"content": "Водители"}}],
  "properties": {
    "Name": {"title": {}},
    "TikTok URL": {"url": {}},
    "Гражданство": {"multi_select": {"options": []}},
    "Номер телефона": {"rich_text": {}},

    "Разрешение на работу": {"select": {"options": [
      {"name": "есть", "color": "green"},
      {"name": "в процессе", "color": "yellow"},
      {"name": "нет", "color": "red"}
    ]}},
    "Код 95": {"select": {"options": [
      {"name": "есть", "color": "green"},
      {"name": "в процессе", "color": "yellow"},
      {"name": "нет", "color": "red"}
    ]}},
    "ADR": {"select": {"options": [
      {"name": "есть", "color": "green"},
      {"name": "в процессе", "color": "yellow"},
      {"name": "нет", "color": "red"}
    ]}},
    "Карта водителя": {"select": {"options": [
      {"name": "есть", "color": "green"},
      {"name": "в процессе", "color": "yellow"},
      {"name": "нет", "color": "red"}
    ]}},
    
    "Категории прав": {"multi_select": {"options": [
      {"name": "B", "color": "blue"},
      {"name": "C", "color": "green"},
      {"name": "C1", "color": "yellow"},
      {"name": "CE", "color": "red"},
      {"name": "D", "color": "purple"},
      {"name": "D1", "color": "pink"}
    ]}},
    "Опыт (мес.)": {"number": {"format": "number"}},
    "Польский язык": {"select": {"options": [
      {"name": "свободный", "color": "green"},
      {"name": "базовый", "color": "yellow"},
      {"name": "нет", "color": "red"}
    ]}},
    
    "Тип экипажа": {"select": {"options": [
      {"name": "соло", "color": "blue"},
      {"name": "парный", "color": "green"}
    ]}},
    "Типы техники": {"multi_select": {"options": [
      {"name": "Тент", "color": "blue"},
      {"name": "Реф (рефрижератор)", "color": "purple"},
      {"name": "BDF", "color": "green"},
      {"name": "Контейнеры", "color": "orange"},
      {"name": "Цистерна", "color": "yellow"},
      {"name": "Изотерма", "color": "pink"},
      {"name": "Штора", "color": "brown"},
      {"name": "Самосвал", "color": "red"},
      {"name": "Тандем", "color": "default"},
      {"name": "Подконтейнерный прицеп", "color": "gray"}
    ]}},
    "Регионы работы": {"multi_select": {"options": []}},
    "Тип маршрутов": {"select": {"options": [
      {"name": "внутренние", "color": "blue"},
      {"name": "международные", "color": "green"}
    ]}},
    "Исключённые регионы": {"multi_select": {"options": []}},
    "Города базы": {"multi_select": {"options": []}},
    "Мин. зарплата (зл/день)": {"number": {"format": "number"}},
    
    "Пожелания предоставлены": {"checkbox": {}},
    "Вакансия отправлена": {"checkbox": {}},
    "Вакансия принята": {"checkbox": {}},
    "Контакт передан": {"checkbox": {}},
    
    "Источник": {"select": {"options": [
      {"name": "TikTok", "color": "pink"}
    ]}},
    "fileName": {"rich_text": {}},
    "messagesCount": {"number": {"format": "number"}},
    "TikTok Nickname": {"rich_text": {}},
    "Status": {"status": {"options": [
      {"name": "Масса", "color": "default"},
      {"name": "К работе", "color": "gray"},
      {"name": "Высланы вакансии", "color": "blue"},
      {"name": "Ждет новых вакансий", "color": "yellow"},
      {"name": "В процессе найма", "color": "green"},
      {"name": "Нанят", "color": "green"},
      {"name": "Нанят не нами", "color": "red"}
    ]}}
  }
}
```

## Описание полей

| Поле | Тип | Опции | Описание |
|------|-----|-------|----------|
| **Name** | title | — | TikTok username водителя |
| **TikTok URL** | url | — | Ссылка на профиль |
| **Гражданство** | multi_select | динамические | Страны гражданства |
| **Номер телефона** | rich_text | — | Контактный номер телефона |
| **Разрешение на работу** | select | есть / в процессе / нет | Статус разрешения |
| **Код 95** | select | есть / в процессе / нет | Квалификация водителя |
| **ADR** | select | есть / в процессе / нет | Сертификат опасных грузов |
| **Карта водителя** | select | есть / в процессе / нет | Карта тахографа |
| **Категории прав** | multi_select | B, C, C1, CE, D, D1 | Категории прав |
| **Опыт (мес.)** | number | — | Опыт в месяцах |
| **Польский язык** | select | свободный / базовый / нет | Уровень языка |
| **Тип экипажа** | select | соло / парный | Предпочтение по экипажу |
| **Типы техники** | multi_select | Тент, Реф, BDF... | Типы транспорта |
| **Регионы работы** | multi_select | динамические | Желаемые регионы |
| **Тип маршрутов** | select | внутренние / международные | Тип рейсов |
| **Исключённые регионы** | multi_select | динамические | Нежелательные регионы |
| **Города базы** | multi_select | динамические | Города старта |
| **Мин. зарплата (зл/день)** | number | — | Минимальная ставка |
| **Пожелания предоставлены** | checkbox | — | Чеклист: пожелания получены |
| **Вакансия отправлена** | checkbox | — | Чеклист: вакансия отправлена |
| **Вакансия принята** | checkbox | — | Чеклист: вакансия принята |
| **Контакт передан** | checkbox | — | Чеклист: контакт передан |
| **Источник** | select | TikTok | Откуда пришёл кандидат |
| **fileName** | rich_text | — | Имя файла экспорта |
| **messagesCount** | number | — | Кол-во сообщений в чате |
| **TikTok Nickname** | rich_text | — | Никнейм TikTok водителя |
| **Status** | status | Масса / К работе / Задаю вопросы / Высланы вакансии / Ждет новых вакансий / В процессе найма / Нанят / Нанят не нами | Статус обработки кандидата |

## Примечания

- Поля с `options: []` — динамические, опции создаются автоматически при добавлении записей
- Цвета: green, yellow, red, blue, purple, pink, orange, brown, default, gray

