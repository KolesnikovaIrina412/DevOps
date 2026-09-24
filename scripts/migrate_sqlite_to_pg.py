import os
import sqlite3
import psycopg2
from psycopg2.extras import execute_values

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SQLITE_LIBRARY = os.path.join(BASE_DIR, 'instance', 'library.db')
SQLITE_USERS   = os.path.join(BASE_DIR, 'instance', 'users.db')

PG_HOST = 'localhost'
PG_PORT = 5432
PG_USER = 'postgres'
PG_PASSWORD = 'DoDo2207'


def get_sqlite_conn(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def get_pg_conn(dbname):
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT,
        user=PG_USER, password=PG_PASSWORD,
        dbname=dbname
    )


def migrate_library():
    print('Миграция library.db → library')
    sqlite_conn = get_sqlite_conn(SQLITE_LIBRARY)
    pg_conn = get_pg_conn('library')
    sc = sqlite_conn.cursor()
    pc = pg_conn.cursor()

    rows = sc.execute('SELECT id, name FROM genres').fetchall()
    if rows:
        execute_values(pc,
            'INSERT INTO genres (id, name) VALUES %s ON CONFLICT (id) DO NOTHING',
            [(r['id'], r['name']) for r in rows])
        print(f'  genres: {len(rows)}')

    rows = sc.execute(
        'SELECT id, title, description, year, publisher, author, age, created_at FROM books'
    ).fetchall()
    if rows:
        execute_values(pc,
            'INSERT INTO books (id, title, description, year, publisher, author, age, created_at) '
            'VALUES %s ON CONFLICT (id) DO NOTHING',
            [(r['id'], r['title'], r['description'], r['year'],
              r['publisher'], r['author'], r['age'], r['created_at']) for r in rows])
        print(f'  books: {len(rows)}')

    rows = sc.execute('SELECT book_id, genre_id FROM book_genre').fetchall()
    if rows:
        execute_values(pc,
            'INSERT INTO book_genre (book_id, genre_id) VALUES %s ON CONFLICT DO NOTHING',
            [(r['book_id'], r['genre_id']) for r in rows])
        print(f'  book_genre: {len(rows)}')

    rows = sc.execute(
        'SELECT id, filename, mime_type, md5_hash, book_id FROM covers'
    ).fetchall()
    if rows:
        execute_values(pc,
            'INSERT INTO covers (id, filename, mime_type, md5_hash, book_id) '
            'VALUES %s ON CONFLICT (id) DO NOTHING',
            [(r['id'], r['filename'], r['mime_type'], r['md5_hash'], r['book_id']) for r in rows])
        print(f'  covers: {len(rows)}')

    rows = sc.execute(
        'SELECT id, name, address, phone, created_at FROM branches'
    ).fetchall()
    if rows:
        execute_values(pc,
            'INSERT INTO branches (id, name, address, phone, created_at) '
            'VALUES %s ON CONFLICT (id) DO NOTHING',
            [(r['id'], r['name'], r['address'], r['phone'], r['created_at']) for r in rows])
        print(f'  branches: {len(rows)}')

    rows = sc.execute(
        'SELECT id, book_id, branch_id, inventory_number, status, created_at, updated_at '
        'FROM book_copies'
    ).fetchall()
    if rows:
        execute_values(pc,
            'INSERT INTO book_copies (id, book_id, branch_id, inventory_number, status, created_at, updated_at) '
            'VALUES %s ON CONFLICT (id) DO NOTHING',
            [(r['id'], r['book_id'], r['branch_id'], r['inventory_number'],
              r['status'], r['created_at'], r['updated_at']) for r in rows])
        print(f'  book_copies: {len(rows)}')

    rows = sc.execute(
        'SELECT id, copy_id, loan_date, return_date, due_date, created_at FROM book_loans'
    ).fetchall()
    if rows:
        execute_values(pc,
            'INSERT INTO book_loans (id, copy_id, loan_date, return_date, due_date, created_at) '
            'VALUES %s ON CONFLICT (id) DO NOTHING',
            [(r['id'], r['copy_id'], r['loan_date'], r['return_date'],
              r['due_date'], r['created_at']) for r in rows])
        print(f'  book_loans: {len(rows)}')

    pg_conn.commit()

    print('  Синхронизация sequences...')
    for table in ['books', 'genres', 'covers', 'branches', 'book_copies', 'book_loans']:
        pc.execute(
            f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {table}), 1))"
        )
    pg_conn.commit()

    sc.close()
    pc.close()
    sqlite_conn.close()
    pg_conn.close()


def migrate_users():
    print('Миграция users.db → users')
    sqlite_conn = get_sqlite_conn(SQLITE_USERS)
    pg_conn = get_pg_conn('users')
    sc = sqlite_conn.cursor()
    pc = pg_conn.cursor()

    rows = sc.execute('SELECT id, name, description FROM roles').fetchall()
    if rows:
        execute_values(pc,
            'INSERT INTO roles (id, name, description) VALUES %s ON CONFLICT (id) DO NOTHING',
            [(r['id'], r['name'], r['description']) for r in rows])
        print(f'  roles: {len(rows)}')

    rows = sc.execute(
        'SELECT id, login, password_hash, last_name, first_name, patronymic, role_id FROM users'
    ).fetchall()
    if rows:
        execute_values(pc,
            'INSERT INTO users (id, login, password_hash, last_name, first_name, patronymic, role_id) '
            'VALUES %s ON CONFLICT (id) DO NOTHING',
            [(r['id'], r['login'], r['password_hash'], r['last_name'],
              r['first_name'], r['patronymic'], r['role_id']) for r in rows])
        print(f'  users: {len(rows)}')

    pg_conn.commit()

    for table in ['roles', 'users']:
        pc.execute(
            f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {table}), 1))"
        )
    pg_conn.commit()

    sc.close()
    pc.close()
    sqlite_conn.close()
    pg_conn.close()


if __name__ == '__main__':
    if not os.path.exists(SQLITE_LIBRARY):
        print(f'[!] Не найдена SQLite-БД: {SQLITE_LIBRARY}')
    elif not os.path.exists(SQLITE_USERS):
        print(f'[!] Не найдена SQLite-БД: {SQLITE_USERS}')
    else:
        migrate_library()
        migrate_users()
        print()
        print('Готово. Проверить данные в pgAdmin / psql.')