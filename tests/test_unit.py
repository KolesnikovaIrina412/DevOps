"""Unit-тесты основной логики и интеграционные тесты работы с БД."""
import hashlib
import io
from models import db, User, Book, Genre
from books import compute_md5, sanitize_html, markdown_to_html
from conftest import PNG_BYTES


# ============================================================
# UNIT: модели
# ============================================================

class TestUserModel:
    def test_full_name(self, app):
        with app.app_context():
            u = User.query.filter_by(login='admin').first()
            assert u.full_name == 'Админ Главный'

    def test_check_password_ok(self, app):
        with app.app_context():
            u = User.query.filter_by(login='admin').first()
            assert u.check_password('admin123') is True

    def test_check_password_fail(self, app):
        with app.app_context():
            u = User.query.filter_by(login='admin').first()
            assert u.check_password('wrong') is False

    def test_admin_permissions(self, app):
        with app.app_context():
            u = User.query.filter_by(login='admin').first()
            assert u.has_permission('view') is True
            assert u.has_permission('edit') is True

    def test_user_permissions(self, app):
        with app.app_context():
            u = User.query.filter_by(login='user').first()
            assert u.has_permission('view') is True
            assert u.has_permission('edit') is False


class TestHelpers:
    def test_compute_md5_stable(self):
        assert compute_md5(b'x') == hashlib.md5(b'x').hexdigest()

    def test_compute_md5_differs(self):
        assert compute_md5(b'a') != compute_md5(b'b')

    def test_sanitize_html_strips_scripts(self):
        dirty = '<script>alert(1)</script><p>ok</p>'
        clean = sanitize_html(dirty)
        assert '<script>' not in clean
        assert '<p>ok</p>' in clean

    def test_markdown_to_html_bold(self):
        html = markdown_to_html('**жирный**')
        assert '<strong>жирный</strong>' in html


class TestBranchStatsModel:
    def test_get_stats_empty(self, app, sample_book):
        with app.app_context():
            b = db.session.get(Book, sample_book['book_id'])
            stats = b.get_branch_stats(sample_book['branch_id'])
            assert stats == {'total': 1, 'available': 1, 'issued': 0, 'popularity': 0}

    def test_set_stats_increase(self, app, sample_book):
        with app.app_context():
            b = db.session.get(Book, sample_book['book_id'])
            b.set_branch_stats(sample_book['branch_id'],
                               total=3, available=2, issued=1, popularity=0)
            stats = b.get_branch_stats(sample_book['branch_id'])
            assert stats['total'] == 3
            assert stats['available'] == 2
            assert stats['issued'] == 1

    def test_set_stats_decrease(self, app, sample_book):
        with app.app_context():
            b = db.session.get(Book, sample_book['book_id'])
            b.set_branch_stats(sample_book['branch_id'],
                               total=0, available=0, issued=0, popularity=0)
            assert b.get_branch_stats(sample_book['branch_id'])['total'] == 0

    def test_set_stats_popularity(self, app, sample_book):
        with app.app_context():
            b = db.session.get(Book, sample_book['book_id'])
            b.set_branch_stats(sample_book['branch_id'],
                               total=1, available=1, issued=0, popularity=3)
            assert b.get_branch_stats(sample_book['branch_id'])['popularity'] == 3


# ============================================================
# INTEGRATION: авторизация
# ============================================================

class TestAuth:
    def test_login_page(self, client):
        assert client.get('/auth/login').status_code == 200

    def test_login_success(self, client):
        r = client.post('/auth/login',
                        data={'login': 'admin', 'password': 'admin123'},
                        follow_redirects=True)
        assert r.status_code == 200

    def test_login_wrong_password(self, client):
        r = client.post('/auth/login',
                        data={'login': 'admin', 'password': 'no'},
                        follow_redirects=True)
        assert 'Невозможно аутентифицироваться'.encode() in r.data

    def test_logout_requires_login(self, client):
        r = client.get('/auth/logout', follow_redirects=False)
        print('Location:', r.headers.get('Location'))
        assert r.status_code == 302

    def test_logout_works(self, admin_client):
        r = admin_client.get('/auth/logout', follow_redirects=True)
        assert r.status_code == 200


# ============================================================
# INTEGRATION: просмотр книг
# ============================================================

class TestBookView:
    def test_view_existing(self, client, sample_book):
        r = client.get(f"/book/{sample_book['book_id']}")
        assert r.status_code == 200
        assert 'Тестовая книга'.encode() in r.data

    def test_view_missing_404(self, client):
        assert client.get('/book/999999').status_code == 404


# ============================================================
# INTEGRATION: поиск (ТЗ 4.1.1)
# ============================================================

class TestSearch:
    def test_by_title(self, client, books_dataset):
        r = client.get('/?title=Хоббит')
        assert 'Хоббит'.encode() in r.data
        assert 'Шерлок'.encode() not in r.data

    def test_by_author(self, client, books_dataset):
        r = client.get('/?author=Толкин')
        assert 'Властелин'.encode() in r.data
        assert 'Хоббит'.encode() in r.data

    def test_by_genre(self, client, books_dataset, app):
        with app.app_context():
            gid = Genre.query.filter_by(name='Детектив').first().id
        r = client.get(f'/?genres={gid}')
        assert 'Шерлок'.encode() in r.data
        assert 'Хоббит'.encode() not in r.data

    def test_by_year(self, client, books_dataset):
        r = client.get('/?years=1954')
        assert 'Властелин'.encode() in r.data
        assert 'Хоббит'.encode() not in r.data

    def test_by_age(self, client, books_dataset):
        r = client.get('/?age=6')
        assert 'Хоббит'.encode() in r.data
        assert 'Шерлок'.encode() not in r.data

    def test_no_results(self, client, books_dataset):
        r = client.get('/?title=НесуществующаяКнига')
        assert 'Книги не найдены'.encode() in r.data


# ============================================================
# INTEGRATION: пагинация
# ============================================================

class TestPagination:
    def test_two_pages(self, client, app):
        with app.app_context():
            g = Genre.query.first()
            for i in range(15):
                b = Book(title=f'К{i}', description='d', year=2000,
                         publisher='p', author='a', age=6)
                b.genres.append(g)
                db.session.add(b)
            db.session.commit()
        assert client.get('/?page=1').status_code == 200
        assert client.get('/?page=2').status_code == 200


# ============================================================
# INTEGRATION: CRUD книг (ТЗ 4.1.1)
# ============================================================

class TestCreateBook:
    def test_create_requires_login(self, client):
        r = client.get('/book/create', follow_redirects=False)
        assert r.status_code == 302
        assert '/auth/login' in r.headers['Location']

    def test_create_forbidden_for_user(self, user_client):
        r = user_client.get('/book/create', follow_redirects=True)
        assert 'недостаточно прав'.encode() in r.data

    def test_create_success(self, admin_client, app):
        with app.app_context():
            gid = Genre.query.first().id
        data = {
            'title': 'Новая', 'description': 'd', 'year': 2020,
            'publisher': 'p', 'author': 'a', 'age': '12',
            'genres': [str(gid)],
            'cover': (io.BytesIO(PNG_BYTES), 'c.png'),
        }
        r = admin_client.post('/book/create', data=data,
                              content_type='multipart/form-data',
                              follow_redirects=True)
        assert r.status_code == 200
        with app.app_context():
            assert Book.query.filter_by(title='Новая').first() is not None


class TestEditBook:
    def test_edit_forbidden_for_user(self, user_client, sample_book):
        r = user_client.get(f"/book/{sample_book['book_id']}/edit",
                            follow_redirects=True)
        assert 'недостаточно прав'.encode() in r.data

    def test_edit_changes_title(self, admin_client, app, sample_book):
        data = {'title': 'НовоеИмя', 'description': 'd', 'year': 2020,
                'publisher': 'p', 'author': 'a', 'age': '12'}
        r = admin_client.post(f"/book/{sample_book['book_id']}/edit",
                              data=data, follow_redirects=True)
        assert r.status_code == 200
        with app.app_context():
            assert db.session.get(Book, sample_book['book_id']).title == 'НовоеИмя'


class TestDeleteBook:
    def test_delete_forbidden_for_user(self, user_client, sample_book):
        r = user_client.post(f"/book/{sample_book['book_id']}/delete",
                             follow_redirects=True)
        assert 'недостаточно прав'.encode() in r.data

    def test_delete_success(self, admin_client, app, sample_book):
        admin_client.post(f"/book/{sample_book['book_id']}/delete",
                          follow_redirects=True)
        with app.app_context():
            assert db.session.get(Book, sample_book['book_id']) is None


# ============================================================
# INTEGRATION: филиалы (ТЗ 4.1.1)
# ============================================================

class TestBranches:
    def test_branches_page(self, client, sample_book):
        r = client.get(f"/book/{sample_book['book_id']}/branches")
        assert r.status_code == 200

    def test_branches_missing_404(self, client):
        assert client.get('/book/999999/branches').status_code == 404

    def test_update_requires_admin(self, user_client, sample_book):
        r = user_client.post(
            f"/book/{sample_book['book_id']}/branches/update",
            data={'branch_id': sample_book['branch_id'],
                  'total': 2, 'available': 1, 'issued': 1, 'popularity': 0},
            follow_redirects=True)
        assert 'недостаточно прав'.encode() in r.data

    def test_update_success(self, admin_client, app, sample_book):
        admin_client.post(
            f"/book/{sample_book['book_id']}/branches/update",
            data={'branch_id': sample_book['branch_id'],
                  'total': 3, 'available': 2, 'issued': 1, 'popularity': 1},
            follow_redirects=True)
        with app.app_context():
            b = db.session.get(Book, sample_book['book_id'])
            stats = b.get_branch_stats(sample_book['branch_id'])
            assert stats['total'] == 3
            assert stats['popularity'] == 1


# ============================================================
# INTEGRATION: health
# ============================================================

class TestHealth:
    def test_health(self, client):
        r = client.get('/health')
        assert r.status_code in (200, 503)
        data = r.get_json()
        assert 'status' in data and 'version' in data
