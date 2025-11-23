#!/bin/bash

# Скрипт для автоматической обработки всех вакансий через GPT-4o mini
# Обрабатывает вакансии пачками с задержкой между батчами

BATCH_SIZE=5
DELAY_SECONDS=2

# Примечание: переменные окружения загружаются автоматически из .env через python-dotenv в process_with_gpt.py
# Убедитесь, что файл .env существует и содержит OPENAI_API_KEY

# Получаем количество вакансий
TOTAL=$(python3 -c "import json; print(len(json.load(open('vacancies.json', 'r', encoding='utf-8'))))")

if [ -z "$TOTAL" ] || [ "$TOTAL" -eq 0 ]; then
    echo "❌ Не удалось определить количество вакансий"
    exit 1
fi

echo "📊 Всего вакансий: $TOTAL"
echo "📦 Размер батча: $BATCH_SIZE"
echo "⏱️  Задержка между батчами: $DELAY_SECONDS сек"
echo ""

CURRENT=0

while [ $CURRENT -lt $TOTAL ]; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔄 Обработка батча: вакансии $CURRENT - $((CURRENT + BATCH_SIZE - 1))"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    python3 process_with_gpt.py --start-from $CURRENT --batch-size $BATCH_SIZE
    
    if [ $? -ne 0 ]; then
        echo "❌ Ошибка при обработке батча"
        exit 1
    fi
    
    CURRENT=$((CURRENT + BATCH_SIZE))
    
    if [ $CURRENT -lt $TOTAL ]; then
        echo ""
        echo "⏸️  Пауза $DELAY_SECONDS сек перед следующим батчем..."
        sleep $DELAY_SECONDS
        echo ""
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Все вакансии обработаны!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

