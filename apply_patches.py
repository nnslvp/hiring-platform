#!/usr/bin/env python3
"""
Скрипт для применения всех патчей из папки patches/

ИСПОЛЬЗОВАНИЕ:
  python3 apply_patches.py

ФУНКЦИОНАЛ:
  - Находит все JSON файлы в папке patches/
  - Применяет каждый патч через update_vacancy_from_json.py
  - Показывает прогресс и статистику
"""

import os
import sys
import subprocess
import glob
from pathlib import Path

def apply_patches():
    patches_dir = Path(__file__).parent / "patches"
    
    if not patches_dir.exists():
        print(f"❌ Папка patches/ не найдена: {patches_dir}")
        return False
    
    json_files = sorted(glob.glob(str(patches_dir / "*.json")))
    
    if not json_files:
        print("⚠️  Папка patches/ пуста")
        return True
    
    print(f"📦 Найдено патчей: {len(json_files)}\n")
    
    script_path = Path(__file__).parent / "update_vacancy_from_json.py"
    success_count = 0
    error_count = 0
    errors = []
    
    for i, json_file in enumerate(json_files, 1):
        filename = os.path.basename(json_file)
        print(f"[{i}/{len(json_files)}] Применяю {filename}...", end=" ")
        
        try:
            result = subprocess.run(
                [sys.executable, str(script_path), json_file],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                print("✅")
                success_count += 1
            else:
                print("❌")
                error_count += 1
                errors.append((filename, result.stderr or result.stdout))
        except Exception as e:
            print(f"❌ Ошибка выполнения: {e}")
            error_count += 1
            errors.append((filename, str(e)))
    
    print(f"\n📊 Результаты:")
    print(f"  ✅ Успешно: {success_count}")
    print(f"  ❌ Ошибок: {error_count}")
    
    if errors:
        print(f"\n❌ Детали ошибок:")
        for filename, error in errors:
            print(f"  {filename}:")
            print(f"    {error}")
    
    return error_count == 0

if __name__ == "__main__":
    success = apply_patches()
    sys.exit(0 if success else 1)

