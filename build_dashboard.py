#!/usr/bin/env python3
"""
Билд-скрипт для создания автономного dashboard HTML файла.

Встраивает JSON данные прямо в HTML, чтобы файл можно было
открыть без сервера или расшарить.

Использование:
    python3 build_dashboard.py
    python3 build_dashboard.py --output my-dashboard.html
"""

import json
import re
import argparse
from pathlib import Path


def load_json(path: str):
    """Загрузка JSON файла."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_standalone_dashboard(
    template_path: str = "TickTokDMParser/dashboard.html",
    candidates_path: str = "candidate_analysis.json",
    matching_path: str = "matching_results.json",
    output_path: str = "dashboard-standalone.html"
) -> None:
    """
    Создаёт автономный HTML файл со встроенными данными.
    """
    print("📦 Сборка автономного dashboard...")
    
    # Загружаем шаблон
    print(f"   Читаю шаблон: {template_path}")
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    
    # Загружаем данные
    print(f"   Читаю данные кандидатов: {candidates_path}")
    candidates_data = load_json(candidates_path)
    
    print(f"   Читаю результаты матчинга: {matching_path}")
    matching_data = load_json(matching_path)
    
    # Создаём JavaScript код с встроенными данными
    embedded_data = f"""
        // ═══════════════════════════════════════════════════════════════
        // ВСТРОЕННЫЕ ДАННЫЕ (автоматически сгенерировано build_dashboard.py)
        // ═══════════════════════════════════════════════════════════════
        const EMBEDDED_CANDIDATES = {json.dumps(candidates_data, ensure_ascii=False)};
        const EMBEDDED_MATCHING = {json.dumps(matching_data, ensure_ascii=False)};
"""
    
    # Заменяем placeholder на реальные данные
    placeholder = """        // ═══════════════════════════════════════════════════════════════
        // PLACEHOLDER: Данные будут встроены сюда скриптом build_dashboard.py
        // ═══════════════════════════════════════════════════════════════
        // const EMBEDDED_CANDIDATES = [...];
        // const EMBEDDED_MATCHING = {...};"""
    
    html = html.replace(placeholder, embedded_data)
    
    # Обновляем заголовок
    html = html.replace(
        "<title>Dashboard - Анализ чатов TikTok</title>",
        "<title>Dashboard - Анализ чатов TikTok (Standalone)</title>"
    )
    
    # Добавляем метку standalone в header
    html = html.replace(
        '<p>Воронка рекрутинга водителей в Польше</p>',
        '<p>Воронка рекрутинга водителей в Польше <span style="background:#10b981;color:white;padding:2px 8px;border-radius:10px;font-size:0.8em;margin-left:10px;">Standalone</span></p>'
    )
    
    # Сохраняем результат
    print(f"   Сохраняю: {output_path}")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    # Статистика
    file_size = Path(output_path).stat().st_size
    size_mb = file_size / (1024 * 1024)
    
    print(f"\n✅ Готово!")
    print(f"   Файл: {output_path}")
    print(f"   Размер: {size_mb:.2f} MB")
    print(f"   Кандидатов: {len(candidates_data)}")
    print(f"   Вакансий: {matching_data.get('total_vacancies', 'N/A')}")
    print(f"\n💡 Открой файл в браузере или отправь коллеге!")


def main():
    parser = argparse.ArgumentParser(
        description="Создаёт автономный dashboard HTML файл"
    )
    parser.add_argument(
        "--template", 
        default="TickTokDMParser/dashboard.html",
        help="Путь к шаблону dashboard.html"
    )
    parser.add_argument(
        "--candidates",
        default="candidate_analysis.json",
        help="Путь к JSON файлу с кандидатами"
    )
    parser.add_argument(
        "--matching",
        default="matching_results.json", 
        help="Путь к JSON файлу с результатами матчинга"
    )
    parser.add_argument(
        "--output", "-o",
        default="dashboard-standalone.html",
        help="Путь к выходному файлу"
    )
    
    args = parser.parse_args()
    
    build_standalone_dashboard(
        template_path=args.template,
        candidates_path=args.candidates,
        matching_path=args.matching,
        output_path=args.output
    )


if __name__ == "__main__":
    main()

