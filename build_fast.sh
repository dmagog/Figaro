#!/bin/bash

echo "🚀 Быстрая сборка с базовым образом..."

# Сначала собираем базовый образ
echo "📦 Сборка базового образа..."
docker-compose build base

# Затем собираем остальные сервисы
echo "🔨 Сборка app..."
docker-compose build app

echo "🔨 Сборка worker..."
docker-compose build worker

echo "🔨 Сборка bot..."
docker-compose build bot

echo "✅ Все образы собраны!"
echo "🚀 Запуск сервисов..."
docker-compose up -d

echo "📊 Статус сервисов:"
docker-compose ps 