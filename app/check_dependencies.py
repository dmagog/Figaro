#!/usr/bin/env python3
"""
Скрипт для проверки совместимости зависимостей
Проверяет версии пакетов и выявляет потенциальные конфликты
"""

import subprocess
import sys
import re
from typing import Dict, List, Tuple

def get_installed_packages() -> Dict[str, str]:
    """Получает список установленных пакетов с версиями"""
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'freeze'], 
                              capture_output=True, text=True, check=True)
        packages = {}
        for line in result.stdout.strip().split('\n'):
            if '==' in line:
                name, version = line.split('==', 1)
                packages[name.lower()] = version
        return packages
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при получении списка пакетов: {e}")
        return {}

def get_requirements_packages() -> Dict[str, str]:
    """Получает список пакетов из requirements.txt"""
    packages = {}
    try:
        with open('requirements.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '==' in line:
                    name, version = line.split('==', 1)
                    packages[name.lower()] = version
    except FileNotFoundError:
        print("Файл requirements.txt не найден")
    return packages

def check_compatibility() -> List[str]:
    """Проверяет совместимость зависимостей"""
    issues = []
    
    # Критические зависимости и их совместимые версии
    critical_deps = {
        'python': '3.11',
        'sqlmodel': '0.0.24',
        'pydantic': '1.10.13',
        'fastapi': '0.104.1',
        'sqlalchemy': '2.0.31',
        'psycopg2-binary': '2.9.10'
    }
    
    installed = get_installed_packages()
    required = get_requirements_packages()
    
    # Проверяем критические зависимости
    for dep, expected_version in critical_deps.items():
        if dep in installed:
            actual_version = installed[dep]
            if actual_version != expected_version:
                issues.append(f"КРИТИЧНО: {dep} версия {actual_version} != {expected_version}")
    
    # Проверяем отсутствующие пакеты
    for dep, version in required.items():
        if dep not in installed:
            issues.append(f"ОТСУТСТВУЕТ: {dep}=={version}")
    
    # Проверяем лишние пакеты
    for dep in installed:
        if dep not in required and not dep.startswith('pip'):
            issues.append(f"ЛИШНИЙ: {dep}=={installed[dep]}")
    
    return issues

def check_python_version():
    """Проверяет версию Python"""
    version = sys.version_info
    if version.major != 3 or version.minor != 11:
        print(f"⚠️  ВНИМАНИЕ: Python {version.major}.{version.minor} вместо 3.11")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def main():
    """Основная функция"""
    print("🔍 Проверка зависимостей...")
    print("=" * 50)
    
    # Проверяем версию Python
    python_ok = check_python_version()
    print()
    
    # Проверяем совместимость
    issues = check_compatibility()
    
    if issues:
        print("❌ Найдены проблемы:")
        for issue in issues:
            print(f"  - {issue}")
        print()
        print("💡 Рекомендации:")
        print("  1. Пересоберите Docker-образ: docker-compose build --no-cache")
        print("  2. Проверьте requirements.txt на актуальность")
        print("  3. Убедитесь, что используете Python 3.11")
        return False
    else:
        print("✅ Все зависимости совместимы!")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 