# Notion Util

Утилиты для работы с вакансиями в Notion.

## Установка

1. Установите зависимости:
```bash
pip3 install -r requirements.txt
```

2. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

3. Заполните `.env` файл своими ключами:
```
NOTION_TOKEN=your_notion_token_here
OPENAI_API_KEY=your_openai_api_key_here
```

## Использование

### Получение вакансий
```bash
python3 fetch_vacancies.py
```

### Обработка вакансий через GPT
```bash
python3 process_with_gpt.py --batch-size 5
```

### Обработка всех вакансий автоматически
```bash
./process_all_vacancies.sh
```

### Применение патчей
```bash
python3 apply_patches.py
```

## Важно

- Файл `.env` добавлен в `.gitignore` и не должен попадать в git
- Используйте `.env.example` как шаблон
- Никогда не коммитьте секретные ключи в репозиторий
- Все скрипты автоматически загружают переменные из `.env` через python-dotenv

