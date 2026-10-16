# Электронная библиотека

Веб-приложение для учёта книг, филиалов, экземпляров и их использования.

## Стек технологий

- **Python 3.13**
- **Flask 3.0.3** — веб-фреймворк
- **Flask-SQLAlchemy 3.1.1** — ORM для работы с БД
- **Flask-Login 0.6.3** — аутентификация и сессии
- **PostgreSQL 17** — реляционная СУБД
- **psycopg2** — драйвер PostgreSQL для Python
- **gunicorn** — WSGI-сервер для продакшена
- **Alembic 1.13.3** — миграции схемы БД
- **pytest + pytest-cov** — тестирование и покрытие
- **flake8** — линтер
- **bandit** — SAST (статический анализ безопасности)
- **Jinja2** — шаблонизатор
- **Bootstrap 5** — вёрстка
- **Pillow** — обработка обложек
- **bleach + markdown** — безопасный HTML и разметка описаний

## Структура проекта
````
app/
├── instance/
│ └── .gitkeep
├── migrations/ # миграции Alembic
│ ├── versions/ # файлы миграций
│ ├── env.py # настройка окружения Alembic
│ ├── script.py.mako
│ └── README
├── scripts/
│ ├── backup.sh # резервное копирование БД
│ ├── restore.sh # восстановление БД
│ └── deploy.sh # развёртывание приложения
├── static/
│ ├── images/ # обложки и аватары
│ └── styles.css
├── templates/
│ ├── 400.html, 403.html, 404.html, 413.html, 500.html
│ ├── base.html
│ ├── book_branches.html
│ ├── book_form.html
│ ├── book_view.html
│ ├── books_list.html
│ └── login.html
├── tests/
│ ├── conftest.py # фикстуры, тестовое приложение
│ ├── test_unit.py # unit + integration
│ └── test_edge_cases.py # границы и правила
├── app.py # точка входа, маршруты, /health
├── auth.py # blueprint аутентификации
├── books.py # blueprint книг и филиалов
├── config.py # конфигурация из .env
├── models.py # модели SQLAlchemy
├── version.py # версия приложения
├── Makefile # команды управления
├── alembic.ini # конфигурация Alembic
├── pyproject.toml # конфигурация pytest + coverage
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── CONTRIBUTING.md
└── SECURITY.md
````


## Установка и запуск (локально)

### 1. Клонирование

```bash
git clone https://github.com/KolesnikovaIrina412/DevOps.git
cd DevOps
```

### 2. Установка и настройка PostgreSQL

1. Установить **PostgreSQL 17** (Windows: официальный установщик, Linux: `apt install postgresql`).
2. Создать пользователя и базы данных (под `postgres`):

   ```sql
   CREATE USER app_user WITH PASSWORD 'заменить_на_пароль';
   CREATE DATABASE library OWNER postgres;
   CREATE DATABASE users   OWNER postgres;
   GRANT CONNECT ON DATABASE library TO app_user;
   GRANT CONNECT ON DATABASE users   TO app_user;
   ```

3. Настроить права для `app_user` (под `postgres`):

   ```sql
   \c library
   GRANT USAGE, CREATE ON SCHEMA public TO app_user;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public
       GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public
       GRANT USAGE, SELECT ON SEQUENCES TO app_user;

   \c users
   GRANT USAGE ON SCHEMA public TO app_user;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public
       GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public
       GRANT USAGE, SELECT ON SEQUENCES TO app_user;
   ```

> `CREATE` на схему нужен `app_user` для применения миграций Alembic.

### 3. Виртуальное окружение и зависимости

```bash
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 4. Настройка переменных окружения

```bash
copy .env.example .env
```

Сгенерировать `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Применение миграций

```bash
alembic upgrade head
```

### 6. Запуск

```bash
python app.py
```

Приложение: <http://127.0.0.1:5000>

## Тесты и проверки

Все основные команды — через `Makefile`:

```bash
make help       # справка
make setup      # первичная настройка (venv, зависимости, .env)
make run        # локальный запуск приложения
make test       # тесты с отчётом покрытия
make quality    # линтер (flake8) + SAST (bandit)
make migrate    # применить миграции Alembic
make verify     # полный набор проверок (test + quality + migrate)
```

**Требования к качеству:**
- Покрытие тестами — **≥ 40%** (зафиксировано в `pyproject.toml`).
- `flake8` — **0 ошибок**.
- `bandit` — **0 issues**.
- `pytest` — **все тесты пройдены**.

## Миграции (Alembic)

Проект использует **Alembic** для управления схемой БД.

```bash
alembic upgrade head                              # применить все миграции
alembic current                                   # текущая версия
alembic history                                   # история миграций
alembic revision --autogenerate -m "описание"     # создать новую миграцию
alembic downgrade -1                              # откатить последнюю
```

Файлы миграций — в `migrations/versions/`.

**Список миграций:**
1. `initial schema` — начальная схема (books, covers, branches, book_copies, book_loans, genres, book_genre).
2. `add book_marks` — таблица меток пользователя (bookmark/like/read).
3. `add indexes on books` — индексы `ix_books_title`, `ix_books_author` для поиска.

## Развёртывание (продакшен)

Развёртывание на **двух серверах** (app-server + db-server) описано в [SECURITY.md](SECURITY.md).

```bash
make deploy     # развёртывание приложения (на app-server)
make backup     # резервная копия БД (на db-server)
make restore    # восстановление БД из дампа (на db-server)
```

**Требования к серверу:**
- Debian 13 без GUI.
- Пользователь `appuser` без sudo — для запуска приложения.
- Пользователь `sysadmin` с sudo — для администрирования.
- systemd-служба `library.service`.
- Firewall (`ufw`) с минимальным набором портов.

## Тестовые пользователи

| Роль | Логин | Пароль | Возможности |
| :--- | :--- | :--- | :--- |
| Администратор | `admin` | `admin123` | Полный доступ: просмотр, добавление, редактирование, удаление книг, работа с филиалами |
| Пользователь | `user` | `user123` | Просмотр книг, филиалов, а также управление личными метками (закладки/нравится/прочитано) |

⚠️ **В продакшене** эти учётные записи нужно **удалить** или **сменить пароли** сразу после развёртывания.

## Переменные окружения

Все настройки читаются из файла `.env` (см. `.env.example`).

| Переменная                                                                                         | Описание                                                                                                                                    | Значение по умолчанию                                                    |
|:---------------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------|:-------------------------------------------------------------------------|
| `SECRET_KEY`                                                                                       | Секретный ключ для сессий и CSRF                                                                                                            | `dev-secret-key-change-me`                                               |
| `DATABASE_URL`                                                                                     | Подключение к БД `library`                                                                                                                  | `postgresql+psycopg2://app_user:app_password@localhost:5432/library`     |
| `AUTH_DATABASE_URL`                                                                                | Подключение к БД `users`                                                                                                                    | `postgresql+psycopg2://app_user:app_password@localhost:5432/users`       |
| `MIGRATION_DATABASE_URL` | Подключение к БД `library` для миграций от пользователя `postgres` | `postgresql+psycopg2://postgres:postgres_password@localhost:5432/library` |
| `MAX_CONTENT_LENGTH`                                                                               | Максимальный размер загружаемого файла (байты)                                                                                              | `16777216` (16 МБ)                                                       |
| `FLASK_DEBUG`                                                                                      | Режим отладки: `1` — вкл, `0` — выкл                                                                                                        | `0`                                                                      |

## API

| Метод | Маршрут | Описание | Доступ |
| :--- | :--- | :--- | :--- |
| GET | `/` | Редирект на список книг | Все |
| GET | `/books/` | Список книг с поиском, фильтрацией и пагинацией | Все |
| GET | `/books/book/<int:book_id>` | Карточка книги | Все |
| GET | `/books/book/<int:book_id>/branches` | Статистика по филиалам для книги | Все |
| POST | `/books/book/<int:book_id>/mark` | Переключение метки (bookmark/like/read) | Авторизованные |
| GET | `/books/book/create` | Форма добавления книги | Только admin |
| POST | `/books/book/create` | Создание книги | Только admin |
| GET | `/books/book/<int:book_id>/edit` | Форма редактирования книги | Только admin |
| POST | `/books/book/<int:book_id>/edit` | Обновление книги | Только admin |
| POST | `/books/book/<int:book_id>/delete` | Удаление книги | Только admin |
| GET | `/books/init-branches` | Создание тестовых филиалов | Только admin |
| POST | `/books/book/<int:book_id>/branches/update` | Обновление статистики филиала | Только admin |
| GET | `/auth/login` | Форма входа | Все |
| POST | `/auth/login` | Аутентификация | Все |
| GET | `/auth/logout` | Выход | Авторизованные |
| GET | `/health` | Проверка работоспособности | Все |
| GET | `/version` | Версия приложения | Все |

### Параметры поиска (`/books/`)

| Параметр | Тип | Описание |
| :--- | :--- | :--- |
| `title` | string | Часть названия книги |
| `author` | string | Часть имени автора |
| `genres` | list[int] | ID жанров (можно несколько) |
| `years` | list[int] | Годы издания (можно несколько) |
| `age` | list[int] | Возрастные ограничения (можно несколько) |
| `filter` | list[str] | Метки пользователя: `bookmarks`, `likes`, `read` |
| `page` | int | Номер страницы (по умолчанию 1, размер 10) |

## Проверка работоспособности

Маршрут `/health` возвращает JSON со статусом приложения и доступностью обеих БД.

**Пример успешного ответа (HTTP 200):**

```json
{
  "status": "ok",
  "version": "0.4.2",
  "database": "ok",
  "auth_database": "ok"
}
```

**Пример ответа при недоступности БД (HTTP 503):**

```json
{
  "status": "error",
  "version": "0.4.2",
  "database": "error: ...",
  "auth_database": "ok"
}
```

## Схема данных

### `library` (основная БД)

```mermaid
erDiagram
    books ||--o| covers : "books.id → covers.book_id"
    books ||--o{ book_copies : "books.id → book_copies.book_id"
    books ||--o{ book_genre : "books.id → book_genre.book_id"
    books ||--o{ book_marks : "books.id → book_marks.book_id"
    genres ||--o{ book_genre : "genres.id → book_genre.genre_id"
    branches ||--o{ book_copies : "branches.id → book_copies.branch_id"
    book_copies ||--o{ book_loans : "book_copies.id → book_loans.copy_id"

    books {
        int id PK
        string title
        text description
        int year
        string publisher
        string author
        int age
        datetime created_at
    }

    covers {
        int id PK
        string filename
        string mime_type
        string md5_hash
        int book_id FK
    }

    genres {
        int id PK
        string name
    }

    book_genre {
        int book_id PK, FK
        int genre_id PK, FK
    }

    branches {
        int id PK
        string name
        string address
        string phone
        datetime created_at
    }

    book_copies {
        int id PK
        int book_id FK
        int branch_id FK
        string inventory_number
        string status
        datetime created_at
        datetime updated_at
    }

    book_loans {
        int id PK
        int copy_id FK
        datetime loan_date
        datetime return_date
        datetime due_date
        datetime created_at
    }

    book_marks {
        int id PK
        int user_id
        int book_id FK
        string mark_type
        datetime created_at
    }
```

**Связи:**
- `books.id` → `covers.book_id` — one-to-one.
- `books.id` → `book_copies.book_id` — one-to-many.
- `books.id` → `book_genre.book_id` — one-to-many.
- `books.id` → `book_marks.book_id` — one-to-many (CASCADE).
- `genres.id` → `book_genre.genre_id` — one-to-many.
- `branches.id` → `book_copies.branch_id` — one-to-many.
- `book_copies.id` → `book_loans.copy_id` — one-to-many.

**Индексы:**
- `ix_books_title` — на `books.title`.
- `ix_books_author` — на `books.author`.
- `uq_user_book_mark` — уникальность `(user_id, book_id, mark_type)`.

### `users` (БД пользователей)

```mermaid
erDiagram
    roles ||--o{ users : "roles.id → users.role_id"

    roles {
        int id PK
        string name
        text description
    }

    users {
        int id PK
        string login
        string password_hash
        string last_name
        string first_name
        string patronymic
        int role_id FK
    }
```

## Данные для демонстрации

Дампы БД (`*.sql`) **не хранятся в репозитории** — они содержат данные, а не код, и могут включать чувствительную информацию. Они передаются **отдельно** (через защищённый канал) или **создаются заново**.

### Как получить данные

**Вариант 1 — получить дампы у разработчика.**
Запросить `library_dump.sql` и `users_dump.sql` через защищённый канал.

**Вариант 2 — создать минимальный набор.**
Через веб-интерфейс под `admin/admin123` добавить книги, жанры, филиалы.

**Вариант 3 — заполнить через миграции + UI.**
После `alembic upgrade head`:
- `init_db()` создаст роли, пользователей, жанры.
- Книги и филиалы добавляются вручную через UI.

## Справочные правила предметной области

1. **Баланс экземпляров:** для каждого филиала сумма `available + issued` должна равняться `total`. Проверяется при обновлении статистики филиала (`branches_update`).
2. **Дедупликация обложек:** при загрузке обложки вычисляется MD5-хэш. Если такая обложка уже существует — новая запись `Cover` ссылается на тот же файл, а не создаёт дубликат.
3. **Права доступа:** редактирование и удаление книг, работа с филиалами — только для роли `admin`. Роль `user` имеет доступ только к просмотру и к управлению **своими** метками.
4. **Метки пользователя:** каждая метка (`bookmark`, `like`, `read`) уникальна для пары `(user_id, book_id, mark_type)`. Повторное нажатие удаляет метку.

## Правила внесения изменений

Правила работы с репозиторием, обязательные проверки, запрещённые действия и порядок приёмки описаны в отдельном документе — [CONTRIBUTING.md](CONTRIBUTING.md).

## Безопасность

Требования безопасности приложения (запрет запуска от root, ограничения портов, хранение секретов) описаны в отдельном документе — [SECURITY.md](SECURITY.md).

## Лицензия

Учебный проект. Лабораторные работы №1, №2, №3 по дисциплине «Методология и практики DevOps».