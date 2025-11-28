#!/usr/bin/env python3
"""
Vacancy Matcher - матчинг кандидатов с вакансиями.

Загружает данные кандидатов из candidate_analysis.json и вакансий из patches/,
выполняет скоринг и выдаёт отсортированный список подходящих вакансий.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from field_definitions import (
    LICENSE_CATEGORIES,
    DOCUMENT_STATUS,
    REQUIREMENT_LEVEL,
    CREW_TYPE,
    POLISH_LEVEL,
    POLISH_REQUIREMENT,
    VEHICLE_TYPES,
    ROUTE_TYPE,
    validate_value,
    normalize_vehicle_type,
    normalize_region,
    normalize_crew_type,
)


def load_candidates(path: str = "candidate_analysis.json") -> list[dict]:
    """Загрузка данных кандидатов из JSON файла."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_vacancy_statuses(vacancies_json: str = "vacancies.json") -> dict:
    """Загрузка статусов вакансий из vacancies.json."""
    statuses = {}
    try:
        with open(vacancies_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                page_id = item.get("page_id")
                status = item.get("status")
                if page_id:
                    statuses[page_id] = status
    except FileNotFoundError:
        pass
    return statuses


def load_vacancies(patches_dir: str = "patches", 
                   vacancies_json: str = "vacancies.json",
                   exclude_closed: bool = True) -> list[dict]:
    """Загрузка данных вакансий из JSON патчей.
    
    Args:
        patches_dir: путь к папке с патчами
        vacancies_json: путь к файлу со статусами вакансий
        exclude_closed: исключать закрытые вакансии
    """
    vacancies = []
    patches_path = Path(patches_dir)
    
    statuses = load_vacancy_statuses(vacancies_json) if exclude_closed else {}
    closed_count = 0
    
    for file_path in patches_path.glob("vacancy-*.json"):
        with open(file_path, "r", encoding="utf-8") as f:
            vacancy = json.load(f)
            vacancy["_file"] = file_path.name
            
            page_id = vacancy.get("page_id")
            status = statuses.get(page_id, "Опубликовано")
            vacancy["_status"] = status
            
            if exclude_closed and status == "Закрыто":
                closed_count += 1
                continue
            
            vacancies.append(vacancy)
    
    if closed_count > 0:
        print(f"   Исключено закрытых: {closed_count}")
    
    return vacancies


def is_international_vacancy(vacancy_regions: list) -> bool:
    """Определяет, является ли вакансия международной по регионам работы."""
    if not vacancy_regions:
        return False  # Не указано = не блокируем
    
    # Международные маркеры
    international_markers = [
        "по всей европе", "европа", "ес", "eu", "вся европа",
        "великобритания", "uk", "англия",
        "германия", "франция", "италия", "испания", "бенилюкс",
        "скандинавия", "швеция", "норвегия", "финляндия", "дания"
    ]
    
    regions_lower = [r.lower() for r in vacancy_regions if r]
    
    # Если только Польша - внутренняя
    if len(regions_lower) == 1 and regions_lower[0] == "польша":
        return False
    
    # Если есть международные маркеры или несколько стран - международная
    for region in regions_lower:
        for marker in international_markers:
            if marker in region:
                return True
    
    # Если несколько разных стран - международная
    if len(regions_lower) > 1:
        return True
    
    return False


def validate_candidate_profile(profile: dict) -> list[str]:
    """Валидация профиля кандидата, возвращает список предупреждений."""
    warnings = []
    
    for field in ["work_permit_status", "code_95_status", "adr_status", "driver_card_status"]:
        value = profile.get(field)
        if value is not None:
            _, warn = validate_value(value, DOCUMENT_STATUS, field)
            if warn:
                warnings.append(warn)
    
    licenses = profile.get("license_categories", [])
    if licenses:
        _, warn = validate_value(licenses, LICENSE_CATEGORIES, "license_categories")
        if warn:
            warnings.extend(warn if isinstance(warn, list) else [warn])
    
    polish = profile.get("polish_language")
    if polish is not None:
        _, warn = validate_value(polish, POLISH_LEVEL, "polish_language")
        if warn:
            warnings.append(warn)
    
    crew = profile.get("crew_type")
    if crew is not None:
        _, warn = validate_value(crew, CREW_TYPE, "crew_type")
        if warn:
            warnings.append(warn)
    
    route = profile.get("route_type_preference")
    if route is not None:
        _, warn = validate_value(route, ROUTE_TYPE, "route_type_preference")
        if warn:
            warnings.append(warn)
    
    return warnings


def validate_vacancy_props(props: dict) -> list[str]:
    """Валидация свойств вакансии, возвращает список предупреждений."""
    warnings = []
    
    for field in ["Код 95", "ADR", "Карта водителя"]:
        value = props.get(field)
        if value is not None:
            _, warn = validate_value(value, REQUIREMENT_LEVEL, field)
            if warn:
                warnings.append(warn)
    
    licenses = props.get("Категория прав", [])
    if licenses:
        _, warn = validate_value(licenses, LICENSE_CATEGORIES, "Категория прав")
        if warn:
            warnings.extend(warn if isinstance(warn, list) else [warn])
    
    polish = props.get("Требование польского языка")
    if polish is not None:
        _, warn = validate_value(polish, POLISH_REQUIREMENT, "Требование польского языка")
        if warn:
            warnings.append(warn)
    
    crew = props.get("Тип экипажа")
    if crew is not None:
        _, warn = validate_value(crew, CREW_TYPE, "Тип экипажа")
        if warn:
            warnings.append(warn)
    
    vehicles = props.get("Тип техники", [])
    if vehicles:
        _, warn = validate_value(vehicles, VEHICLE_TYPES, "Тип техники")
        if warn:
            warnings.extend(warn if isinstance(warn, list) else [warn])
    
    return warnings


def has_overlap(list1: list, list2: list, normalizer=None) -> bool:
    """Проверка пересечения двух списков."""
    if not list1 or not list2:
        return False
    
    if normalizer:
        set1 = {normalizer(x) for x in list1 if x}
        set2 = {normalizer(x) for x in list2 if x}
    else:
        set1 = {x.lower() if isinstance(x, str) else x for x in list1}
        set2 = {x.lower() if isinstance(x, str) else x for x in list2}
    
    return bool(set1 & set2)


def get_intersection(list1: list, list2: list, normalizer=None) -> list:
    """Получение пересечения двух списков."""
    if not list1 or not list2:
        return []
    
    if normalizer:
        norm1 = {normalizer(x): x for x in list1 if x}
        norm2 = {normalizer(x) for x in list2 if x}
        return [v for k, v in norm1.items() if k in norm2]
    
    set2_lower = {x.lower() if isinstance(x, str) else x for x in list2}
    return [x for x in list1 if (x.lower() if isinstance(x, str) else x) in set2_lower]


def license_matches(candidate_licenses: list, vacancy_licenses: list) -> bool:
    """Проверка совпадения категорий прав."""
    if not vacancy_licenses:
        return True
    if not candidate_licenses:
        return True
    
    candidate_set = {lic.upper() for lic in candidate_licenses}
    vacancy_set = {lic.upper() for lic in vacancy_licenses}
    
    for vac_lic in vacancy_set:
        if vac_lic in candidate_set:
            return True
        if vac_lic == "CE" and "CE" in candidate_set:
            return True
        if vac_lic == "C" and ("C" in candidate_set or "CE" in candidate_set):
            return True
    
    return False


def match_candidate_to_vacancy(candidate: dict, vacancy: dict) -> dict:
    """
    Матчинг кандидата с вакансией.
    
    Returns:
        {
            "score": int,           # 0-100
            "blockers": list[str],  # причины блокировки
            "warnings": list[str],  # предупреждения
            "matches": list[str]    # что совпало
        }
    """
    profile = candidate.get("profile", {})
    props = vacancy.get("properties", {})
    
    blockers = []
    warnings = []
    matches = []
    score = 0
    
    # Валидация входных данных
    profile_warnings = validate_candidate_profile(profile)
    vacancy_warnings = validate_vacancy_props(props)
    if profile_warnings:
        warnings.extend([f"⚠️ Кандидат: {w}" for w in profile_warnings])
    if vacancy_warnings:
        warnings.extend([f"⚠️ Вакансия: {w}" for w in vacancy_warnings])
    
    # === ЖЕСТКИЕ БЛОКЕРЫ ===
    
    # 1. Разрешение на работу - блокер если нет или в процессе
    work_permit = profile.get("work_permit_status")
    if work_permit == "нет":
        blockers.append("Нет разрешения на работу в Польше")
    elif work_permit == "в процессе":
        blockers.append("ВНЖ/виза в процессе оформления")
    elif work_permit is None:
        warnings.append("Статус ВНЖ неизвестен")
    
    # 2. Категория прав - блокер если указаны и не совпадают
    candidate_licenses = profile.get("license_categories", [])
    vacancy_licenses = props.get("Категория прав", [])
    
    if candidate_licenses and vacancy_licenses:
        if not license_matches(candidate_licenses, vacancy_licenses):
            blockers.append(f"Требуется {', '.join(vacancy_licenses)}, есть {', '.join(candidate_licenses)}")
    
    # 3. Избегаемые регионы - блокер при пересечении
    avoided_regions = profile.get("avoided_regions", [])
    vacancy_regions = props.get("Регионы работы", [])
    
    if avoided_regions and vacancy_regions:
        overlap = get_intersection(avoided_regions, vacancy_regions, normalize_region)
        if overlap:
            blockers.append(f"Кандидат не хочет работать в: {', '.join(overlap)}")
    
    # 4. Тип маршрутов - блокер если кандидат хочет только внутренние, а вакансия международная
    route_preference = profile.get("route_type_preference")
    
    if route_preference == "внутренние" and is_international_vacancy(vacancy_regions):
        blockers.append("Кандидат хочет только внутренние рейсы (Польша), вакансия международная")
    elif route_preference == "международные" and vacancy_regions:
        # Если хочет международные, а вакансия только по Польше - предупреждение
        if len(vacancy_regions) == 1 and vacancy_regions[0].lower() == "польша":
            warnings.append("Кандидат предпочитает международные рейсы, вакансия только по Польше")
    
    # 5. Гражданство - блокер если не подходит по ограничениям вакансии
    candidate_citizenship = profile.get("citizenship", [])
    accepted_citizenship = props.get("Допустимое гражданство", [])
    excluded_citizenship = props.get("Исключённое гражданство", [])
    
    if candidate_citizenship:
        # Проверка допустимого гражданства (включающий список)
        if accepted_citizenship:
            candidate_set = {c.lower() for c in candidate_citizenship}
            accepted_set = {c.lower() for c in accepted_citizenship}
            if not candidate_set & accepted_set:
                warnings.append(f"Гражданство {', '.join(candidate_citizenship)} не в списке допустимых: {', '.join(accepted_citizenship)}")
        
        # Проверка исключённого гражданства
        if excluded_citizenship:
            candidate_set = {c.lower() for c in candidate_citizenship}
            excluded_set = {c.lower() for c in excluded_citizenship}
            overlap = candidate_set & excluded_set
            if overlap:
                blockers.append(f"Гражданство {', '.join(candidate_citizenship)} исключено вакансией")
    elif accepted_citizenship:
        # Гражданство кандидата неизвестно, но вакансия требует определённое
        warnings.append(f"Вакансия только для граждан: {', '.join(accepted_citizenship)}, гражданство кандидата неизвестно")
    
    # === МЯГКИЕ БЛОКЕРЫ (только при явном "нет" + обязательное требование) ===
    
    # 4. Код 95
    code_95_required = props.get("Код 95")
    code_95_status = profile.get("code_95_status")
    
    if code_95_required == "Обязательно":
        if code_95_status == "нет":
            blockers.append("Требуется Код 95, у кандидата нет")
        elif code_95_status == "в процессе":
            warnings.append("Код 95 в процессе получения")
        elif code_95_status is None:
            warnings.append("Код 95 обязателен, статус неизвестен")
    
    # 5. ADR
    adr_required = props.get("ADR")
    adr_status = profile.get("adr_status")
    
    if adr_required == "Обязательно":
        if adr_status == "нет":
            blockers.append("Требуется ADR, у кандидата нет")
        elif adr_status == "в процессе":
            warnings.append("ADR в процессе получения")
        elif adr_status is None:
            warnings.append("ADR обязателен, статус неизвестен")
    
    # 6. Карта водителя
    driver_card_required = props.get("Карта водителя")
    driver_card_status = profile.get("driver_card_status")
    
    if driver_card_required == "Обязательно":
        if driver_card_status == "нет":
            blockers.append("Требуется карта водителя, у кандидата нет")
        elif driver_card_status == "в процессе":
            warnings.append("Карта водителя в процессе получения")
        elif driver_card_status is None:
            warnings.append("Карта водителя обязательна, статус неизвестен")
    
    # 7. Польский язык
    polish_required = props.get("Требование польского языка")
    polish_level = profile.get("polish_language")
    
    if polish_required == "Обязательно":
        if polish_level == "нет":
            blockers.append("Требуется польский язык, кандидат не владеет")
        elif polish_level is None:
            warnings.append("Польский обязателен, уровень неизвестен")
    
    # Если есть блокеры - score = 0
    if blockers:
        return {
            "score": 0,
            "blockers": blockers,
            "warnings": warnings,
            "matches": []
        }
    
    # === ПРЕДУПРЕЖДЕНИЯ (не блокеры) ===
    
    # Опыт
    min_exp_months = props.get("Минимальный опыт (месяцы)")
    candidate_exp = profile.get("experience_months")
    
    if min_exp_months and candidate_exp is not None:
        if candidate_exp < min_exp_months:
            warnings.append(f"Опыт {candidate_exp} мес. < требуемых {min_exp_months} мес.")
    elif min_exp_months and candidate_exp is None:
        warnings.append(f"Требуется опыт {min_exp_months} мес., у кандидата неизвестен")
    
    # Зарплатные ожидания
    min_salary = props.get("Минимальная зарплата (нетто)")
    salary_expectation = profile.get("min_salary_expectation")
    salary_currency = props.get("Валюта зарплаты")
    payment_type = props.get("Тип оплаты")
    
    if min_salary and salary_expectation:
        if payment_type == "Поденная" and min_salary < salary_expectation:
            warnings.append(f"Ставка {min_salary} {salary_currency or ''}/день < ожидания {salary_expectation}")
    
    # === БАЛЛЫ СОВМЕСТИМОСТИ ===
    # Баллы даются ТОЛЬКО за реальные совпадения, не за "не указано"
    
    # Тип техники (+25 за совпадение)
    preferred_vehicles = profile.get("preferred_vehicle_types", [])
    vacancy_vehicles = props.get("Тип техники", [])
    
    if preferred_vehicles and vacancy_vehicles:
        if has_overlap(preferred_vehicles, vacancy_vehicles, normalize_vehicle_type):
            score += 25
            overlap = get_intersection(preferred_vehicles, vacancy_vehicles, normalize_vehicle_type)
            matches.append(f"Тип техники: {', '.join(overlap)}")
    # Не даём баллы за "любой" или "не указано"
    
    # Регион работы (+20 за совпадение)
    preferred_regions = profile.get("preferred_regions", [])
    
    if preferred_regions and vacancy_regions:
        if has_overlap(preferred_regions, vacancy_regions, normalize_region):
            score += 20
            overlap = get_intersection(preferred_regions, vacancy_regions, normalize_region)
            matches.append(f"Регион: {', '.join(overlap)}")
    # Не даём баллы за "любой" или "не указано"
    
    # Тип экипажа (+15 за совпадение)
    crew_type = profile.get("crew_type")
    vacancy_crew = props.get("Тип экипажа")
    
    normalized_crew = normalize_crew_type(crew_type) if crew_type else None
    normalized_vacancy_crew = normalize_crew_type(vacancy_crew) if vacancy_crew else None
    
    if normalized_crew and normalized_vacancy_crew:
        if normalized_vacancy_crew == normalized_crew:
            score += 15
            matches.append(f"Экипаж: {normalized_crew}")
    # Не даём баллы за "не указано"
    
    # Польский язык - бонус (+10)
    if polish_required == "Желательно" and polish_level == "свободный":
        score += 10
        matches.append("Польский: свободный")
    elif polish_required is None and polish_level in ("свободный", "базовый"):
        score += 5
        matches.append(f"Польский: {polish_level}")
    
    # Опыт выше требуемого (+10)
    if min_exp_months and candidate_exp:
        if candidate_exp >= min_exp_months * 2:
            score += 10
            matches.append(f"Опыт: {candidate_exp} мес. (в 2+ раза выше)")
        elif candidate_exp >= min_exp_months:
            score += 5
            matches.append(f"Опыт: {candidate_exp} мес.")
    
    # Все документы готовы (+10)
    docs_ready = (
        work_permit == "есть" and
        (code_95_status == "есть" or code_95_required != "Обязательно") and
        (driver_card_status == "есть" or driver_card_required != "Обязательно")
    )
    if docs_ready:
        score += 10
        matches.append("Документы: готовы")
    
    # Город базы в предпочтениях (+10 или предупреждение)
    preferred_cities = profile.get("preferred_base_cities", [])
    vacancy_city = props.get("Город базы")
    
    if preferred_cities and vacancy_city:
        city_match = any(
            city.lower() in vacancy_city.lower() or vacancy_city.lower() in city.lower() 
            for city in preferred_cities
        )
        if city_match:
            score += 10
            matches.append(f"База: {vacancy_city}")
        else:
            warnings.append(f"Кандидат хочет базу в {', '.join(preferred_cities)}, вакансия в {vacancy_city}")
    
    # Категория прав совпадает (+5 бонус)
    if candidate_licenses and vacancy_licenses:
        if license_matches(candidate_licenses, vacancy_licenses):
            score += 5
            matches.append(f"Права: {', '.join(candidate_licenses)}")
    
    # Гражданство подходит (+5 бонус)
    if candidate_citizenship and accepted_citizenship:
        candidate_set = {c.lower() for c in candidate_citizenship}
        accepted_set = {c.lower() for c in accepted_citizenship}
        if candidate_set & accepted_set:
            score += 5
            matches.append(f"Гражданство: {', '.join(candidate_citizenship)}")
    
    # ADR есть (+5 бонус если требуется или желательно)
    if adr_required in ("Обязательно", "Желательно") and adr_status == "есть":
        score += 5
        matches.append("ADR: есть")
    
    return {
        "score": score,
        "blockers": blockers,
        "warnings": warnings,
        "matches": matches
    }


def get_profile_summary(candidate: dict) -> str:
    """Краткое описание профиля кандидата."""
    profile = candidate.get("profile", {})
    parts = []
    
    licenses = profile.get("license_categories", [])
    if licenses:
        parts.append(", ".join(licenses))
    
    exp = profile.get("experience_months")
    if exp:
        if exp >= 12:
            parts.append(f"{exp // 12} лет опыта")
        else:
            parts.append(f"{exp} мес. опыта")
    
    crew = profile.get("crew_type")
    if crew:
        parts.append(crew)
    
    citizenship = profile.get("citizenship", [])
    if citizenship:
        parts.append(", ".join(citizenship))
    
    return ", ".join(parts) if parts else "профиль не заполнен"


def get_vacancy_name(vacancy: dict) -> str:
    """Получение имени вакансии из данных."""
    props = vacancy.get("properties", {})
    
    parts = []
    
    city = props.get("Город базы")
    if city:
        parts.append(city)
    
    licenses = props.get("Категория прав", [])
    if licenses:
        parts.append(", ".join(licenses))
    
    salary = props.get("Минимальная зарплата (нетто)")
    currency = props.get("Валюта зарплаты", "")
    payment = props.get("Тип оплаты", "")
    
    if salary:
        unit = "/день" if payment == "Поденная" else "/мес"
        parts.append(f"{salary} {currency}{unit}")
    
    return " • ".join(parts) if parts else vacancy.get("page_id", "Unknown")


def match_all_candidates(candidates: list[dict], vacancies: list[dict], 
                         min_score: int = 0, top_n: Optional[int] = None,
                         include_blocked: bool = False) -> list[dict]:
    """
    Матчинг всех кандидатов со всеми вакансиями.
    
    Args:
        candidates: список кандидатов
        vacancies: список вакансий
        min_score: минимальный score для включения в результаты
        top_n: максимальное количество вакансий на кандидата
        include_blocked: включать ли заблокированные вакансии (score=0 + blockers)
    
    Returns:
        список результатов с рекомендациями для каждого кандидата
    """
    results = []
    
    for candidate in candidates:
        candidate_matches = []
        
        for vacancy in vacancies:
            match_result = match_candidate_to_vacancy(candidate, vacancy)
            
            has_blockers = bool(match_result["blockers"])
            score = match_result["score"]
            
            # Включаем если: score > 0 (есть совпадения) И score >= min_score И нет блокеров
            if score > 0 and score >= min_score and (not has_blockers or include_blocked):
                candidate_matches.append({
                    "vacancy_id": vacancy.get("page_id"),
                    "vacancy_name": get_vacancy_name(vacancy),
                    **match_result
                })
        
        candidate_matches.sort(key=lambda x: x["score"], reverse=True)
        
        if top_n:
            candidate_matches = candidate_matches[:top_n]
        
        results.append({
            "candidate": candidate.get("chatName"),
            "file_name": candidate.get("fileName"),
            "messages_count": candidate.get("messagesCount", 0),
            "profile_summary": get_profile_summary(candidate),
            "total_matches": len(candidate_matches),
            "matches": candidate_matches
        })
    
    results.sort(key=lambda x: x["total_matches"], reverse=True)
    
    return results


def print_results(results: list[dict], top_vacancies: int = 5):
    """Консольный вывод результатов."""
    print("\n" + "=" * 80)
    print("РЕЗУЛЬТАТЫ МАТЧИНГА")
    print("=" * 80)
    
    for result in results:
        candidate = result["candidate"]
        summary = result["profile_summary"]
        total = result["total_matches"]
        matches = result["matches"]
        
        print(f"\n{'=' * 60}")
        print(f"👤 {candidate} ({summary})")
        print(f"   Подходящих вакансий: {total}")
        print("-" * 60)
        
        shown = 0
        for i, match in enumerate(matches[:top_vacancies], 1):
            if match["score"] == 0 and match["blockers"]:
                continue
            
            shown += 1
            score = match["score"]
            name = match["vacancy_name"]
            
            print(f"\n{i}. [{score:3d}] {name}")
            
            if match["matches"]:
                matches_str = " | ".join(match["matches"][:4])
                print(f"   ✓ {matches_str}")
            
            if match["warnings"]:
                for warn in match["warnings"][:2]:
                    print(f"   ⚠️  {warn}")
            
            if match["blockers"]:
                for block in match["blockers"]:
                    print(f"   ❌ {block}")
        
        if shown == 0:
            print("   Нет подходящих вакансий")


def save_results(results: list[dict], output_path: str = "matching_results.json",
                 total_candidates: int = 0, total_vacancies: int = 0):
    """Сохранение результатов в JSON файл."""
    output = {
        "generated_at": datetime.now().isoformat(),
        "total_candidates": total_candidates,
        "total_vacancies": total_vacancies,
        "results": results
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Результаты сохранены в {output_path}")


def main():
    """Основная функция."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Матчинг кандидатов с вакансиями")
    parser.add_argument("--candidates", default="candidate_analysis.json",
                        help="Путь к файлу кандидатов")
    parser.add_argument("--patches", default="patches",
                        help="Путь к папке с патчами вакансий")
    parser.add_argument("--output", default="matching_results.json",
                        help="Путь к выходному JSON файлу")
    parser.add_argument("--min-score", type=int, default=0,
                        help="Минимальный score для включения")
    parser.add_argument("--top", type=int, default=None,
                        help="Количество топ вакансий на кандидата (без ограничения по умолчанию)")
    parser.add_argument("--console-top", type=int, default=5,
                        help="Количество вакансий в консольном выводе")
    parser.add_argument("--include-blocked", action="store_true",
                        help="Включить заблокированные вакансии в результаты")
    parser.add_argument("--include-closed", action="store_true",
                        help="Включить закрытые вакансии")
    parser.add_argument("--quiet", action="store_true",
                        help="Без консольного вывода")
    
    args = parser.parse_args()
    
    print("📂 Загрузка данных...")
    candidates = load_candidates(args.candidates)
    vacancies = load_vacancies(args.patches, exclude_closed=not args.include_closed)
    
    print(f"   Кандидатов: {len(candidates)}")
    print(f"   Вакансий: {len(vacancies)}")
    
    print("\n🔄 Выполнение матчинга...")
    results = match_all_candidates(
        candidates, 
        vacancies,
        min_score=args.min_score,
        top_n=args.top,
        include_blocked=args.include_blocked
    )
    
    if not args.quiet:
        print_results(results, top_vacancies=args.console_top)
    
    save_results(
        results, 
        args.output,
        total_candidates=len(candidates),
        total_vacancies=len(vacancies)
    )
    
    with_matches = sum(1 for r in results if r["total_matches"] > 0)
    print(f"\n📊 Статистика:")
    print(f"   Кандидатов с подходящими вакансиями: {with_matches}/{len(candidates)}")


if __name__ == "__main__":
    main()

