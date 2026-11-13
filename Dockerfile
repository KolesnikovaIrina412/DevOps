# ==========================================
# ЭТАП 1: Сборка зависимостей
# ==========================================
# Используем Python 3.11 (slim)
FROM python:3.11-slim AS builder

WORKDIR /build

# Системные зависимости для сборки psycopg2 и Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем только requirements.txt
COPY requirements.txt .
# Ставим зависимости
RUN pip install --no-cache-dir --prefix=/install \
    --index-url https://pypi-mirror.gitverse.ru/simple \
    --trusted-host pypi-mirror.gitverse.ru \
    -r requirements.txt


# ==========================================
# ЭТАП 2: Рантайм (Финальный образ)
# ==========================================
# Используем Python 3.11 (slim)
FROM python:3.11-slim

# Устанавливаем системные библиотеки для работы
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создаем непривилегированного пользователя (Пункт 3)
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Копируем библиотеки из первого этапа
COPY --from=builder /install /usr/local

# Копируем код приложения
COPY . .

# Создаем папку instance и выдаем права
RUN mkdir -p /app/instance && chown -R appuser:appuser /app

# Переключаемся на непривилегированного пользователя
USER appuser

# Переменные окружения по умолчанию
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

# Открываем порт
EXPOSE 5000

# HEALTHCHECK
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Запуск через Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "app:app"]