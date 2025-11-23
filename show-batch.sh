#!/bin/bash

# Вспомогательный скрипт для вывода конкретного батча вакансий
# Использование: ./show-batch.sh [номер_батча] [размер_батча]
#
# Параметры:
#   номер_батча - номер батча для вывода (начиная с 1, по умолчанию: 1)
#   размер_батча - количество вакансий в батче (по умолчанию: 5)
#
# Примеры:
#   ./show-batch.sh --total   # показать общее количество вакансий
#   ./show-batch.sh           # показать первый батч (5 вакансий)
#   ./show-batch.sh 3         # показать третий батч (5 вакансий)
#   ./show-batch.sh 2 10      # показать второй батч (10 вакансий)

# Если передан параметр --total, показать только общее количество
if [ "$1" = "--total" ]; then
    TOTAL=$(jq 'length' vacancies.json 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "Всего вакансий: $TOTAL"
    else
        echo "Ошибка: не удалось прочитать файл vacancies.json"
        exit 1
    fi
    exit 0
fi

# Параметры по умолчанию
BATCH_NUM=${1:-1}  # номер батча (по умолчанию 1)
BATCH_SIZE=${2:-5} # размер батча (по умолчанию 5)

# Проверка наличия файла vacancies.json
if [ ! -f "vacancies.json" ]; then
    echo "Ошибка: файл vacancies.json не найден"
    exit 1
fi

# Получение общего количества вакансий
TOTAL=$(jq 'length' vacancies.json 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "Ошибка: не удалось прочитать файл vacancies.json"
    exit 1
fi

# Проверка корректности входных данных
if ! [[ "$BATCH_NUM" =~ ^[0-9]+$ ]] || [ "$BATCH_NUM" -lt 1 ]; then
    echo "Ошибка: номер батча должен быть положительным числом"
    exit 1
fi

if ! [[ "$BATCH_SIZE" =~ ^[0-9]+$ ]] || [ "$BATCH_SIZE" -lt 1 ]; then
    echo "Ошибка: размер батча должен быть положительным числом"
    exit 1
fi

# Расчет общего количества батчей
TOTAL_BATCHES=$(( (TOTAL + BATCH_SIZE - 1) / BATCH_SIZE ))

# Проверка существования батча
if [ $BATCH_NUM -gt $TOTAL_BATCHES ]; then
    echo "Батч $BATCH_NUM не существует. Всего батчей: $TOTAL_BATCHES (из $TOTAL вакансий)"
    exit 1
fi

# Расчет индексов
START_IDX=$(( (BATCH_NUM - 1) * BATCH_SIZE ))
END_IDX=$(( START_IDX + BATCH_SIZE ))

# Вывод информации о батче
ACTUAL_SIZE=$(jq ".[$START_IDX:$END_IDX] | length" vacancies.json)
echo "Батч $BATCH_NUM: $ACTUAL_SIZE вакансий (индексы $START_IDX-$((END_IDX-1)), всего вакансий: $TOTAL)"
echo "Общее количество батчей: $TOTAL_BATCHES"
echo

# Вывод полного содержимого вакансий в батче
echo "Вакансии в батче $BATCH_NUM:"
jq -r ".[$START_IDX:$END_IDX][] | \"=== ВАКАНСИЯ: \(.page_id) ===\\n\(. | tostring)\\n\"" vacancies.json
