# =============================================================================
# SEED Agent Dockerfile
# =============================================================================

# Используем локальный Python образ (должен быть загружен через docker load)
FROM python:3.11-slim

# Рабочая директория
WORKDIR /app

# НЕ устанавливаем curl для offline режима - используем python для health check

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

# Health check без curl - используем python
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Запуск
CMD ["python", "seed-agent.py", "--mode", "both", "--host", "0.0.0.0", "--port", "8080"]