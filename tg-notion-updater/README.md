# TikTok Notion Updater Bot

Telegram бот на Cloudflare Workers для обновления статусов записей в Notion по ссылкам TikTok.

## Функционал

- Принимает ссылку TikTok или username
- Ищет запись в базе Notion по username
- Проверяет текущий статус (FSM-логика)
- Обновляет статус только если он соответствует разрешённому
- Возвращает ссылку на обновлённую запись

## Установка

### 1. Установка Wrangler CLI

```bash
npm install -g wrangler
```

### 2. Авторизация в Cloudflare

```bash
wrangler login
```

### 3. Установка зависимостей

```bash
cd tg-notion-updater
npm install
```

### 4. Настройка секретов

```bash
# Токен Telegram бота (получить у @BotFather)
wrangler secret put TG_BOT_TOKEN

# API ключ Notion (https://www.notion.so/my-integrations)
wrangler secret put NOTION_SECRET
```

### 5. Деплой

```bash
wrangler deploy
```

После деплоя вы получите URL вида:
```
https://tg-notion-updater.<your-subdomain>.workers.dev
```

### 6. Регистрация Webhook в Telegram

Замените `<BOT_TOKEN>` и `<WORKER_URL>` на свои значения:

```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=<WORKER_URL>"
```

Пример:
```bash
curl "https://api.telegram.org/bot123456:ABC-DEF/setWebhook?url=https://tg-notion-updater.example.workers.dev"
```

## Конфигурация

Переменные настраиваются в `wrangler.toml`:

| Переменная | Описание | Значение по умолчанию |
|------------|----------|----------------------|
| `NOTION_DB_ID` | ID базы данных Notion | `2ba95810-6f37-815e-86f2-ed07436ca6b0` |
| `COL_SEARCH` | Поле для поиска | `Name` |
| `COL_STATUS` | Поле статуса | `Status` |
| `STATUS_FROM` | Разрешённый начальный статус | `Масса` |
| `STATUS_TO` | Целевой статус | `К работе` |

## Использование

Отправьте боту ссылку TikTok:
- `https://tiktok.com/@username`
- `tiktok.com/@username`
- Или просто username: `@username` или `username`

### Примеры ответов

**Успех:**
```
✅ Статус обновлен на "К работе"!

Вот запись:
https://www.notion.so/username-abc123...
```

**Запись не найдена:**
```
❌ Запись с username "unknown_user" не найдена в базе данных.
```

**Неверный статус (FSM-блок):**
```
⛔️ Не могу обновить.

Запись в статусе "К работе", а нужен "Масса".

Изменения отклонены.
```

**Некорректная ссылка:**
```
⚠️ Не удалось извлечь username из ссылки.

Отправьте ссылку в формате:
• tiktok.com/@username
• vm.tiktok.com/...
```

## Разработка

Локальный запуск для тестирования:

```bash
wrangler dev
```

## Notion Integration

Для работы бота необходимо:

1. Создать интеграцию на https://www.notion.so/my-integrations
2. Дать интеграции доступ к базе данных "Водители(переписки)"
3. Скопировать API ключ (начинается с `secret_` или `ntn_`)

## Лицензия

MIT

