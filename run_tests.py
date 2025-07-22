#!/usr/bin/env python3
"""
Скрипт для запуска тестов Figaro Bot API
"""

import sys
import subprocess
import argparse
import os
from pathlib import Path

def run_command(command, description):
    """Запускает команду и выводит результат"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Запуск тестов Figaro Bot API")
    parser.add_argument(
        "--type", 
        choices=["all", "auth", "user", "purchase", "home", "tickets"],
        default="all",
        help="Тип тестов для запуска"
    )
    parser.add_argument(
        "--coverage", 
        action="store_true",
        help="Запустить с покрытием кода"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Подробный вывод"
    )
    parser.add_argument(
        "--parallel", 
        action="store_true",
        help="Параллельное выполнение тестов"
    )
    parser.add_argument(
        "--install-deps", 
        action="store_true",
        help="Установить зависимости для тестов"
    )
    
    args = parser.parse_args()
    
    # Проверяем, что мы в правильной директории
    if not Path("app").exists():
        print("❌ Ошибка: Запустите скрипт из корневой директории проекта")
        sys.exit(1)
    
    # Устанавливаем зависимости если нужно
    if args.install_deps:
        print("📦 Установка зависимостей для тестов...")
        if not run_command("pip install -r tests/requirements-test.txt", "Установка зависимостей"):
            sys.exit(1)
    
    # Формируем команду pytest
    pytest_cmd = ["pytest"]
    
    # Выбираем тесты
    if args.type == "all":
        pytest_cmd.append("tests/")
    else:
        pytest_cmd.append(f"tests/test_{args.type}.py")
    
    # Добавляем флаги
    if args.verbose:
        pytest_cmd.append("-v")
    
    if args.coverage:
        pytest_cmd.append("--cov=app")
        pytest_cmd.append("--cov-report=html")
        pytest_cmd.append("--cov-report=term-missing")
    
    if args.parallel:
        pytest_cmd.append("-n")
        pytest_cmd.append("auto")
    
    # Запускаем тесты
    command = " ".join(pytest_cmd)
    
    print(f"\n🎯 Запуск тестов типа: {args.type}")
    if args.coverage:
        print("📊 С покрытием кода")
    if args.verbose:
        print("🔍 Подробный вывод")
    if args.parallel:
        print("⚡ Параллельное выполнение")
    
    success = run_command(command, "Выполнение тестов")
    
    if success:
        print("\n✅ Все тесты прошли успешно!")
        if args.coverage:
            print("📊 Отчет о покрытии создан в htmlcov/index.html")
    else:
        print("\n❌ Некоторые тесты не прошли")
        sys.exit(1)

if __name__ == "__main__":
    main() 