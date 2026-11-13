# ==========================================
# ЭТАП 1: Сборка зависимостей
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Обновляем ТОЛЬКО setuptools и wheel (pip не трогаем, чтобы не сломать сборку)
RUN pip install --no-cache-dir --prefix=/install \
    --index-url https://pypi-mirror.gitverse.ru/simple \
    --trusted-host pypi-mirror.gitverse.ru \
    --upgrade setuptools wheel

# Ставим основные зависимости (используя системный pip)
RUN pip install --no-cache-dir --prefix=/install \
    --index-url https://pypi-mirror.gitverse.ru/simple \
    --trusted-host pypi-mirror.gitverse.ru \
    -r requirements.txt

# УДАЛЯЕМ уязвимые вендорные пакеты из setuptools (они нужны только для сборки, а не для работы приложения)
RUN rm -rf /install/lib/python3.11/site-packages/setuptools/_vendor

# Удаляем сам pip из финального образа, так как он не нужен для работы приложения
RUN rm -rf /install/lib/python3.11/site-packages/pip* /install/bin/pip*


# ==========================================
# ЭТАП 2: Рантайм (Финальный образ)
# ==========================================
FROM python:3.11-slim

# Обновляем системные пакеты (лечит zlib1g и др.)
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Копируем библиотеки из первого этапа (уже без _vendor и pip)
COPY --from=builder /install /usr/local
COPY . .

RUN mkdir -p /app/instance && chown -R appuser:appuser /app

USER appuser

ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "app:app"]