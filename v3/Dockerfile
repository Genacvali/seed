# =============================================================================
# SEED Agent Dockerfile
# =============================================================================

# Используем локальный Python образ (должен быть загружен через docker load)
FROM python:3.11-slim

# Рабочая директория
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копируем требования и устанавливаем Python пакеты
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Создаем пользователя для безопасности
RUN useradd -r -s /bin/false seed && \
    mkdir -p logs && \
    chown -R seed:seed /app

# Переключаемся на пользователя
USER seed

# Переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Порт
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Запуск
CMD ["python", "seed-agent.py", "--mode", "both", "--host", "0.0.0.0", "--port", "8080"]