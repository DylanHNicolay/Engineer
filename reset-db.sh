#!/bin/bash
set -e

echo "Stopping containers..."
docker-compose down

echo "Removing PostgreSQL volume..."
docker volume rm engineer_postgres_data || true

echo "Starting containers..."
docker-compose up -d

echo "Database has been reset. Watching logs..."
docker-compose logs -f
