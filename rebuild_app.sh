#!/bin/bash

echo "🚀 Быстрая пересборка только app сервиса..."

# Останавливаем только app
docker-compose stop app

# Пересобираем только app с кэшем базового образа
docker-compose build app

# Запускаем только app
docker-compose up app -d

echo "✅ App пересобран и запущен!"
echo "📊 Логи app:"
docker-compose logs app --tail=10 