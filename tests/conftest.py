import os
import sys
import base64

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'app'))

import pytest
from flask import Flask, jsonify, redirect, url_for
from flask_login import LoginManager
from models import db, Role, User, Genre, Book, Branch, BookCopy, BookLoan, book_genre
from werkzeug.security import generate_password_hash


PNG_BYTES = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
)


@pytest.fixture(scope='session')
def app():
    """Отдельное Flask-приложение только для тестов."""
    APP_DIR = os.path.join(ROOT, 'app')

    test_app = Flask(
        __name__,
        template_folder=os.path.join(APP_DIR, 'templates'),
        static_folder=os.path.join(APP_DIR, 'static'),
    )

    test_app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SECRET_KEY='test-secret',
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SQLALCHEMY_BINDS={'auth': 'sqlite:///:memory:'},
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=os.path.join(os.path.dirname(__file__), '_tmp_uploads'),
    )
    os.makedirs(test_app.config['UPLOAD_FOLDER'], exist_ok=True)

    # db.init_app вызывается один раз уже с тестовыми URI, поэтому движок будет SQLite.
    db.init_app(test_app)

    login_manager = LoginManager()
    login_manager.init_app(test_app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Для выполнения данного действия необходимо пройти процедуру аутентификации'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Регистрируем blueprints
    from books import books_bp
    from auth import auth_bp
    test_app.register_blueprint(books_bp)
    test_app.register_blueprint(auth_bp)

    # Простые обработчики ошибок
    @test_app.errorhandler(400)
    def bad_request(e):
        return '', 400

    @test_app.errorhandler(403)
    def forbidden(e):
        return '', 403

    @test_app.errorhandler(404)
    def page_not_found(e):
        return '404', 404

    @test_app.errorhandler(413)
    def too_large(e):
        return '', 413

    @test_app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return '', 500

    @test_app.route('/health')
    def health():
        return jsonify({'status': 'ok', 'version': 'test'}), 200

    @test_app.route('/')
    def index():
        return redirect(url_for('books.index'))

    with test_app.app_context():
        db.create_all()
        _seed()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture(autouse=True)
def _clean_tables(app):
    """После каждого теста чистим все пользовательские данные."""
    yield
    with app.app_context():
        # Сначала ассоциативная таблица
        db.session.execute(book_genre.delete())
        BookLoan.query.delete() if 'BookLoan' in globals() else None
        BookCopy.query.delete()
        Book.query.delete()
        Branch.query.delete()
        db.session.commit()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin_client(client):
    client.post('/auth/login',
                data={'login': 'admin', 'password': 'admin123'},
                follow_redirects=True)
    return client


@pytest.fixture()
def user_client(client):
    client.post('/auth/login',
                data={'login': 'user', 'password': 'user123'},
                follow_redirects=True)
    return client


@pytest.fixture()
def sample_book(app):
    with app.app_context():
        genre = Genre.query.first()
        book = Book(title='Тестовая книга', description='Описание',
                    year=2020, publisher='Изд', author='Автор', age=12)
        book.genres.append(genre)
        db.session.add(book)

        branch = Branch(name=f'Филиал-{book.title}', address='ул. Тест, 1',
                        phone='+7 000 000-00-00')
        db.session.add(branch)
        db.session.commit()

        copy = BookCopy(book_id=book.id, branch_id=branch.id,
                        inventory_number=f'INV-{book.id}-{branch.id}-1',
                        status='available')
        db.session.add(copy)
        db.session.commit()

        return {'book_id': book.id, 'branch_id': branch.id, 'genre_id': genre.id}


@pytest.fixture()
def books_dataset(app):
    with app.app_context():
        g1 = Genre.query.filter_by(name='Фэнтези').first()
        g2 = Genre.query.filter_by(name='Детектив').first()

        books = [
            Book(title='Властелин колец', description='d', year=1954,
                 publisher='p', author='Толкин', age=12),
            Book(title='Шерлок Холмс', description='d', year=1892,
                 publisher='p', author='Дойл', age=16),
            Book(title='Хоббит', description='d', year=1937,
                 publisher='p', author='Толкин', age=6),
        ]
        books[0].genres.append(g1)
        books[1].genres.append(g2)
        books[2].genres.append(g1)
        db.session.add_all(books)
        db.session.commit()
        return [b.id for b in books]


def _seed():
    """Роли, пользователи, жанры."""
    admin_role = Role(name='admin', description='Администратор')
    user_role = Role(name='user', description='Пользователь')
    db.session.add_all([admin_role, user_role])
    db.session.commit()

    db.session.add_all([
        User(login='admin',
             password_hash=generate_password_hash('admin123'),
             last_name='Админ', first_name='Главный',
             role_id=admin_role.id),
        User(login='user',
             password_hash=generate_password_hash('user123'),
             last_name='Пользователь', first_name='Тестовый',
             role_id=user_role.id),
    ])

    for name in ['Фэнтези', 'Детектив', 'Фантастика']:
        db.session.add(Genre(name=name))

    db.session.commit()