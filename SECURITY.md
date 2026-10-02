# Политика безопасности

Документ описывает требования безопасности приложения «Электронная библиотека» и правила их соблюдения.

## 1. Пользователи и права доступа

### 1.1. Системные пользователи

| Пользователь | Роль | sudo | Назначение |
| :--- | :--- | :--- | :--- |
| **root** | Суперпользователь | — | Только для системных операций. **Логин запрещён.** |
| **sysadmin** | Администратор | ✅ Да | Установка ПО, управление systemd, firewall |
| **appuser** | Пользователь приложения | ❌ Нет | Запуск Flask-приложения через systemd |

### 1.2. Запрет входа под root

⚠️ В `/etc/ssh/sshd_config` установлено:

```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
```

⚠️ **Вход под root по SSH — запрещён.** Вход по паролю — **запрещён.** Только по SSH-ключу.

## 2. Запуск приложения

### 2.1. Приложение НЕ запускается от root

⚠️ Приложение работает **только** от пользователя **`appuser`**.

**systemd unit** (`/etc/systemd/system/library.service`):

```ini
[Service]
User=appuser
Group=appuser
WorkingDirectory=/home/appuser/DevOps
```

⚠️ Если приложение **запускается вручную**, это делается **только** от `appuser`:

```bash
sudo -u appuser bash
cd /home/appuser/DevOps
source .venv/bin/activate
gunicorn --bind 0.0.0.0:5000 app:app
```

⚠️ **Запуск от root запрещён** — приложение получит **избыточные права**, что **небезопасно**.

### 2.2. Единый способ запуска — systemd

⚠️ В продакшене приложение **управляется только через systemd**:

```bash
sudo systemctl start library.service
sudo systemctl stop library.service
sudo systemctl restart library.service
sudo systemctl status library.service
```

## 3. Сетевые порты

### 3.1. Открытые порты

⚠️ **Принцип минимальных привилегий.** Открыты **только необходимые порты**.

| Сервер | Порт | Кому открыт |
| :--- | :--- | :--- |
| **app-server** (10.0.0.10) | `22/tcp` (SSH) | Всем (через NAT) |
| **app-server** | `5000/tcp` (Web) | Всем (через NAT) |
| **db-server** (10.0.0.20) | `22/tcp` (SSH) | Всем (через NAT) |
| **db-server** | `5432/tcp` (PostgreSQL) | **Только `10.0.0.10`** (app-server) |

### 3.2. Firewall (ufw)

⚠️ На **обеих VM** включён `ufw` (`default deny incoming`).

**app-server:**

```bash
sudo ufw allow 22/tcp
sudo ufw allow 5000/tcp
sudo ufw enable
```

**db-server:**

```bash
sudo ufw allow 22/tcp
sudo ufw allow from 10.0.0.10 to any port 5432 proto tcp
sudo ufw enable
```

⚠️ PostgreSQL **не доступен** ни с хоста, ни с других машин — **только с app-server**.

## 4. Секреты

### 4.1. Что НЕ хранится в репозитории

| Файл | Причина |
| :--- | :--- |
| `.env` | Секреты: `SECRET_KEY`, пароли PostgreSQL |
| `instance/*.db` | SQLite-БД (устаревшие) |
| `instance/*.sql` | Дампы БД (содержат данные) |
| `*.backup` | Резервные копии |

⚠️ Все перечисленные файлы в `.gitignore`.

### 4.2. Где хранятся секреты

⚠️ **`.env`** — только **на сервере** (`/home/appuser/DevOps/.env`), права **`600`** (только владелец).

⚠️ **`.env.example`** — в репозитории, **только плейсхолдеры**, **без реальных паролей**.

### 4.3. Пароли пользователей

⚠️ Пароли хранятся в БД **в хэшированном виде** (`werkzeug.security.generate_password_hash`, алгоритм `scrypt`).

⚠️ **В открытом виде** — **никогда**.

## 5. Требования к развёртыванию

⚠️ **При развёртывании на новой VM обязательно:**

1. **Не запускать приложение от root.**
2. **Запретить root-логин по SSH.**
3. **Включить firewall (`ufw`).**
4. **Ограничить доступ к порту `5432`** — только для app-server.
5. **Установить права `600`** на `.env`.
6. **Не коммитить `.env`, дампы, БД.**

## 6. Что делать при утечке секретов

⚠️ **Если `.env` попал в git:**

1. **Сменить все пароли** — `SECRET_KEY`, пароли PostgreSQL, пароли пользователей.
2. **Удалить файл из истории git** (`git filter-branch` или `BFG Repo-Cleaner`).
3. **Уведомить** ответственных.

⚠️ **Если пароль от БД утёк:**

1. **Сменить пароль** `app_user`:
   ```sql
   ALTER USER app_user WITH PASSWORD 'новый_пароль';
   ```
2. **Обновить `.env`** на app-server.
3. **Перезапустить** приложение.

## 7. Контрольный список при приёмке

- [ ] Приложение запускается **от `appuser`**, не от root.
- [ ] SSH: `PermitRootLogin no`, `PasswordAuthentication no`.
- [ ] Firewall (`ufw`) активен на обеих VM.
- [ ] Порт `5432` доступен **только** с `10.0.0.10`.
- [ ] `.env` — права `600`, в `.gitignore`.
- [ ] В репозитории **нет** паролей, дампов, `.env`.
- [ ] Пароли в БД — **хэшированы**.