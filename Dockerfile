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

# Обновляем setuptools и wheel для сборки
RUN pip install --no-cache-dir --prefix=/install \
    --index-url https://pypi-mirror.gitverse.ru/simple \
    --trusted-host pypi-mirror.gitverse.ru \
    --upgrade setuptools wheel

# Ставим основные зависимости
RUN pip install --no-cache-dir --prefix=/install \
    --index-url https://pypi-mirror.gitverse.ru/simple \
    --trusted-host pypi-mirror.gitverse.ru \
    -r requirements.txt


# ==========================================
# ЭТАП 2: Рантайм (Финальный образ)
# ==========================================
FROM python:3.11-slim

# Обновляем системные пакеты
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Копируем библиотеки из первого этапа
COPY --from=builder /install /usr/local
COPY . .

# Создаем папку instance и выдаем права
RUN mkdir -p /app/instance && chown -R appuser:appuser /app

# ФИНАЛЬНАЯ ЗАЧИСТКА: удаляем setuptools, pip и их уязвимые вендорные пакеты.
# Для работы Gunicorn они не нужны.
RUN rm -rf /usr/local/lib/python3.11/site-packages/setuptools \
           /usr/local/lib/python3.11/site-packages/setuptools-* \
           /usr/local/lib/python3.11/site-packages/pip \
           /usr/local/lib/python3.11/site-packages/pip-* \
           /usr/local/lib/python3.11/site-packages/wheel \
           /usr/local/lib/python3.11/site-packages/wheel-* \
           /usr/local/lib/python3.11/site-packages/jaraco* \
           /usr/local/lib/python3.11/site-packages/backports* \
           /usr/local/lib/python3.11/site-packages/pkg_resources* \
           /usr/local/bin/pip* \
           /usr/local/bin/easy_install*

USER appuser

ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "app:app"]