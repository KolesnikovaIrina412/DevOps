"""Ошибочные данные, граничные случаи и обязательные правила."""
import io
from models import Book
from conftest import PNG_BYTES


def _form(**overrides):
    """Базовые валидные данные формы + переопределения."""
    data = {
        'title': 'Книга',
        'description': 'Описание',
        'year': 2020,
        'publisher': 'Изд',
        'author': 'Автор',
        'age': '12',
        'cover': (io.BytesIO(PNG_BYTES), 'c.png'),
    }
    data.update(overrides)
    return data


# ============================================================
# ПРАВИЛА ДОСТУПА (роль user/admin)
# ============================================================

class TestAccessRules:
    def test_anonymous_cannot_create(self, app):
        fresh_client = app.test_client()
        r = fresh_client.get('/book/create', follow_redirects=False)
        assert r.status_code == 302
        assert '/auth/login' in r.headers['Location']

    def test_user_cannot_create(self, user_client):
        r = user_client.get('/book/create', follow_redirects=True)
        assert 'недостаточно прав'.encode() in r.data

    def test_user_cannot_edit(self, user_client, sample_book):
        r = user_client.get(f"/book/{sample_book['book_id']}/edit",
                            follow_redirects=True)
        assert 'недостаточно прав'.encode() in r.data

    def test_user_cannot_delete(self, user_client, sample_book):
        r = user_client.post(f"/book/{sample_book['book_id']}/delete",
                             follow_redirects=True)
        assert 'недостаточно прав'.encode() in r.data

    def test_user_cannot_update_branches(self, user_client, sample_book):
        r = user_client.post(
            f"/book/{sample_book['book_id']}/branches/update",
            data={'branch_id': sample_book['branch_id'],
                  'total': 1, 'available': 1, 'issued': 0, 'popularity': 0},
            follow_redirects=True)
        assert 'недостаточно прав'.encode() in r.data


# ============================================================
# ОБЯЗАТЕЛЬНЫЕ ПОЛЯ (ТЗ 4.1.1 + 4.1.2)
# ============================================================

class TestRequiredFields:
    def test_missing_title(self, admin_client):
        r = admin_client.post('/book/create', data=_form(title=''),
                              content_type='multipart/form-data')
        assert r.status_code == 400

    def test_missing_description(self, admin_client):
        r = admin_client.post('/book/create', data=_form(description=''),
                              content_type='multipart/form-data')
        assert r.status_code == 400

    def test_missing_publisher(self, admin_client):
        r = admin_client.post('/book/create', data=_form(publisher=''),
                              content_type='multipart/form-data')
        assert r.status_code == 400

    def test_missing_author(self, admin_client):
        r = admin_client.post('/book/create', data=_form(author=''),
                              content_type='multipart/form-data')
        assert r.status_code == 400

    def test_missing_age(self, admin_client):
        r = admin_client.post('/book/create', data=_form(age=''),
                              content_type='multipart/form-data')
        assert r.status_code == 400

    def test_missing_cover(self, admin_client):
        data = _form()
        data.pop('cover')
        r = admin_client.post('/book/create', data=data,
                              content_type='multipart/form-data')
        assert r.status_code == 400


# ============================================================
# ГРАНИЧНЫЕ ЗНАЧЕНИЯ ГОДА (в books.py: 0 <= year <= 2026)
# ============================================================

class TestYearBoundaries:
    def test_year_zero_rejected(self, admin_client):
        r = admin_client.post('/book/create', data=_form(year=0),
                              content_type='multipart/form-data',
                              follow_redirects=False)
        assert r.status_code == 400

    def test_year_2026_allowed(self, admin_client):
        r = admin_client.post('/book/create', data=_form(year=2026),
                              content_type='multipart/form-data',
                              follow_redirects=False)
        assert r.status_code in (200, 302)

    def test_year_2027_rejected(self, admin_client):
        r = admin_client.post('/book/create', data=_form(year=2027),
                              content_type='multipart/form-data')
        assert r.status_code == 400

    def test_year_negative_rejected(self, admin_client):
        r = admin_client.post('/book/create', data=_form(year=-1),
                              content_type='multipart/form-data')
        assert r.status_code == 400


# ============================================================
# ФОРМАТ ОБЛОЖКИ
# ============================================================

class TestCoverFormat:
    def test_wrong_extension_rejected(self, admin_client):
        r = admin_client.post(
            '/book/create',
            data=_form(cover=(io.BytesIO(b'not an image'), 'file.txt')),
            content_type='multipart/form-data',
            follow_redirects=True)
        # либо 400, либо flash об ошибке
        assert r.status_code in (200, 400, 302)
        assert 'формат'.encode() in r.data or r.status_code == 400


# ============================================================
# ФИЛИАЛЫ: обязательные правила
# ============================================================

class TestBranchesRules:
    def test_sum_mismatch_rejected(self, admin_client, sample_book):
        """available + issued != total → отказ."""
        r = admin_client.post(
            f"/book/{sample_book['book_id']}/branches/update",
            data={'branch_id': sample_book['branch_id'],
                  'total': 5, 'available': 1, 'issued': 1, 'popularity': 0},
            follow_redirects=True)
        assert 'Сумма'.encode() in r.data

    def test_missing_branch_id(self, admin_client, sample_book):
        r = admin_client.post(
            f"/book/{sample_book['book_id']}/branches/update",
            data={'total': 1, 'available': 1, 'issued': 0, 'popularity': 0},
            follow_redirects=True)
        assert 'Выберите филиал'.encode() in r.data

    def test_non_integer_values(self, admin_client, sample_book):
        r = admin_client.post(
            f"/book/{sample_book['book_id']}/branches/update",
            data={'branch_id': sample_book['branch_id'],
                  'total': 'abc', 'available': 0, 'issued': 0, 'popularity': 0},
            follow_redirects=True)
        assert 'целыми числами'.encode() in r.data

    def test_negative_values_clamped(self, admin_client, app, sample_book):
        admin_client.post(
            f"/book/{sample_book['book_id']}/branches/update",
            data={'branch_id': sample_book['branch_id'],
                  'total': -5, 'available': -5, 'issued': 0, 'popularity': -3},
            follow_redirects=True)
        with app.app_context():
            b = Book.query.get(sample_book['book_id'])
            stats = b.get_branch_stats(sample_book['branch_id'])
            assert stats['total'] == 0
            assert stats['popularity'] == 0


# ============================================================
# 404 / обработчики ошибок
# ============================================================

class TestErrorHandlers:
    def test_unknown_route_404(self, client):
        r = client.get('/no-such-page-xyz')
        assert r.status_code == 404

    def test_missing_book_404(self, client):
        assert client.get('/book/999999').status_code == 404

    def test_missing_book_branches_404(self, client):
        assert client.get('/book/999999/branches').status_code == 404

    def test_error_handlers_registered(self, app):
        spec = app.error_handler_spec[None]
        for code in (400, 403, 404, 413, 500):
            assert code in spec, f'Handler {code} не зарегистрирован'
