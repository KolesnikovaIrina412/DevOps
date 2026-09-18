from flask import jsonify
from sqlalchemy import text
from version import __version__
import os
from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager
from werkzeug.security import generate_password_hash

from config import Config
from models import db, User, Genre, Role
from books import books_bp
from auth import auth_bp

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Для выполнения данного действия необходимо пройти процедуру аутентификации'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


app.register_blueprint(books_bp)
app.register_blueprint(auth_bp)


@app.route('/')
def index():
    return redirect(url_for('books.index'))

@app.route('/health')
def health():

    status = {
        'status': 'ok',
        'version': __version__,
        'database': 'ok',
        'auth_database': 'ok',
    }
    http_code = 200

    try:
        db.session.execute(text('SELECT 1'))
    except Exception as e:
        status['database'] = f'error: {str(e)}'
        status['status'] = 'error'
        http_code = 503

    try:
        db.session.execute(
            text('SELECT 1').execution_options(bind_key='auth')
        )
    except Exception as e:
        status['auth_database'] = f'error: {str(e)}'
        status['status'] = 'error'
        http_code = 503

    return jsonify(status), http_code


@app.errorhandler(400)
def bad_request(e):
    return render_template('400.html'), 400


@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(413)
def request_entity_too_large(e):
    return render_template('413.html'), 413


@app.errorhandler(500)
def internal_server_error(e):
    db.session.rollback()
    return render_template('500.html'), 500


def init_db():
    with app.app_context():
        db.create_all()

        if Role.query.first() is None:
            roles = [
                Role(name='admin', description='Администратор (полный доступ)'),
                Role(name='user', description='Пользователь (только просмотр)'),
            ]
            db.session.add_all(roles)
            db.session.commit()

        if User.query.first() is None:
            admin_role = Role.query.filter_by(name='admin').first()
            user_role = Role.query.filter_by(name='user').first()

            admin = User(
                login='admin',
                password_hash=generate_password_hash('admin123'),
                last_name='Администратор',
                first_name='',
                patronymic='',
                role_id=admin_role.id,
            )
            user = User(
                login='user',
                password_hash=generate_password_hash('user123'),
                last_name='Тестовый',
                first_name='Пользователь',
                patronymic='',
                role_id=user_role.id,
            )
            db.session.add_all([admin, user])
            db.session.commit()

        if Genre.query.first() is None:
            genres = [
                'Фэнтези', 'Детектив', 'Повседневность',
                'Научная литература', 'Приключения', 'Триллер',
                'Исторический', 'Фантастика', 'Комедия'
            ]
            for genre_name in genres:
                db.session.add(Genre(name=genre_name))
            db.session.commit()


if __name__ == '__main__':
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], '..'), exist_ok=True)
    os.makedirs('instance', exist_ok=True)
    init_db()
    app.run(debug=app.config['DEBUG'])