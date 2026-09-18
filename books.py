from flask import render_template, request, redirect, url_for, flash, Blueprint
from flask_login import login_required, current_user
from models import db, Book, Genre, Cover, Branch
import hashlib
import bleach
from markdown import markdown
import os
from PIL import Image
from io import BytesIO

books_bp = Blueprint('books', __name__)

ALLOWED_TAGS = ['p', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                'ul', 'ol', 'li', 'a', 'code', 'pre', 'blockquote', 'img']


def sanitize_html(text):
    return bleach.clean(text, tags=ALLOWED_TAGS, strip=True)


def markdown_to_html(text):
    safe_text = sanitize_html(text)
    return markdown(safe_text, extensions=['fenced_code', 'tables'])


def compute_md5(file_data):
    return hashlib.md5(file_data).hexdigest()


@books_bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    search_title = request.args.get('title', '').strip()
    search_author = request.args.get('author', '').strip()
    search_genres = request.args.getlist('genres')
    search_years = request.args.getlist('years')
    search_ages = request.args.getlist('age')

    query = Book.query

    if search_title:
        query = query.filter(Book.title.ilike(f'%{search_title}%'))
    if search_author:
        query = query.filter(Book.author.ilike(f'%{search_author}%'))
    if search_genres:
        query = query.filter(Book.genres.any(Genre.id.in_(search_genres)))
    if search_years:
        query = query.filter(Book.year.in_(search_years))
    if search_ages:
        query = query.filter(Book.age.in_(search_ages))

    query = query.order_by(Book.year.desc(), Book.id.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    all_years = db.session.query(Book.year).distinct().order_by(Book.year.desc()).all()
    all_years = [y[0] for y in all_years if y[0]]

    all_genres = Genre.query.order_by(Genre.name).all()

    all_ages = db.session.query(Book.age).distinct().order_by(Book.age.desc()).all()
    all_ages = [y[0] for y in all_ages if y[0]]

    return render_template('books_list.html',
                           books=pagination.items,
                           pagination=pagination,
                           search_title=search_title,
                           search_author=search_author,
                           search_genres=search_genres,
                           search_years=search_years,
                           search_ages=search_ages,
                           all_genres=all_genres,
                           all_years=all_years,
                           all_ages=all_ages)


@books_bp.route('/book/<int:book_id>')
def view(book_id):
    book = Book.query.get_or_404(book_id)
    book.description_html = markdown_to_html(book.description)
    return render_template('book_view.html', book=book)


@books_bp.route('/book/<int:book_id>/branches')
def branches(book_id):
    book = Book.query.get_or_404(book_id)
    branches = Branch.query.order_by(Branch.name).all()

    branches_stats = []
    for branch in branches:
        stats = book.get_branch_stats(branch.id)
        branches_stats.append({
            'branch': branch,
            'stats': stats
        })

    return render_template('book_branches.html', book=book, branches_stats=branches_stats)



@books_bp.route('/book/create', methods=['GET', 'POST'])
@login_required
def create():
    if current_user.role.name != 'admin':
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('books.index'))

    genres = Genre.query.order_by(Genre.name).all()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        year = request.form.get('year', type=int)
        publisher = request.form.get('publisher', '').strip()
        author = request.form.get('author', '').strip()
        selected_genres = request.form.getlist('genres')
        age = request.form.get('age', '').strip()
        cover_file = request.files.get('cover')

        errors = {}

        if not title:
            errors['title'] = 'Название обязательно'
        if not description:
            errors['description'] = 'Описание обязательно'
        if not year or year < 0 or year > 2026:
            errors['year'] = 'Укажите корректный год (0-2026)'
        if not publisher:
            errors['publisher'] = 'Издательство обязательно'
        if not author:
            errors['author'] = 'Автор обязателен'
        if not age:
            errors['age'] = 'Возрастное ограничение обязательно'
        if not cover_file or cover_file.filename == '':
            errors['cover'] = 'Обложка обязательна'

        if errors:
            return render_template('book_form.html', title='Добавить книгу',
                                   book=None, genres=genres, errors=errors,
                                   form_data=request.form), 400

        book = Book(
            title=title,
            description=sanitize_html(description),
            year=year,
            publisher=publisher,
            author=author,
            age=age
        )
        db.session.add(book)
        db.session.flush()

        for gid in selected_genres:
            genre = Genre.query.get(gid)
            if genre:
                book.genres.append(genre)

        img_data = cover_file.read()
        md5_hash = compute_md5(img_data)

        existing_cover = Cover.query.filter_by(md5_hash=md5_hash).first()
        if existing_cover:
            cover = Cover(
                filename=existing_cover.filename,
                mime_type=existing_cover.mime_type,
                md5_hash=md5_hash,
                book_id=book.id
            )
            db.session.add(cover)
        else:
            ext = cover_file.filename.rsplit('.', 1)[-1].lower()
            if ext not in ['jpg', 'jpeg', 'png', 'gif']:
                flash('Неподдерживаемый формат изображения', 'danger')
                db.session.rollback()
                return redirect(url_for('books.create'))

            new_filename = f'cover_{book.id}.{ext}'
            save_path = os.path.join('static', 'images', new_filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            img = Image.open(BytesIO(img_data))
            img.thumbnail((500, 500))
            img.save(save_path, optimize=True, quality=85)

            cover = Cover(
                filename=new_filename,
                mime_type=cover_file.mimetype,
                md5_hash=md5_hash,
                book_id=book.id
            )
            db.session.add(cover)

        db.session.commit()
        flash(f'Книга "{book.title}" успешно добавлена', 'success')
        return redirect(url_for('books.view', book_id=book.id))

    return render_template('book_form.html', title='Добавить книгу',
                           book=None, genres=genres, errors={}, form_data={})


@books_bp.route('/book/<int:book_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(book_id):
    if current_user.role.name != 'admin':
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('books.index'))

    book = Book.query.get_or_404(book_id)
    genres = Genre.query.order_by(Genre.name).all()

    if request.method == 'POST':
        book.title = request.form.get('title', '').strip()
        book.description = sanitize_html(request.form.get('description', '').strip())
        book.year = request.form.get('year', type=int)
        book.publisher = request.form.get('publisher', '').strip()
        book.author = request.form.get('author', '').strip()
        book.age = request.form.get('age', '').strip()
        selected_genres = request.form.getlist('genres')

        book.genres.clear()
        for gid in selected_genres:
            genre = Genre.query.get(gid)
            if genre:
                book.genres.append(genre)

        db.session.commit()
        flash(f'Книга "{book.title}" успешно обновлена', 'success')
        return redirect(url_for('books.view', book_id=book.id))

    form_data = {
        'title': book.title,
        'description': book.description,
        'year': book.year,
        'publisher': book.publisher,
        'author': book.author,
        'age': book.age,
        'genres': [g.id for g in book.genres],
    }
    return render_template('book_form.html', title='Редактировать книгу',
                           book=book, genres=genres, errors={}, form_data=form_data)


@books_bp.route('/book/<int:book_id>/delete', methods=['POST'])
@login_required
def delete(book_id):
    if current_user.role.name != 'admin':
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('books.index'))

    book = Book.query.get_or_404(book_id)
    title = book.title

    if book.cover:
        cover_path = os.path.join('static', 'images', book.cover.filename)
        if os.path.exists(cover_path):
            try:
                os.remove(cover_path)
            except:
                pass

    db.session.delete(book)
    db.session.commit()

    flash(f'Книга "{title}" успешно удалена', 'success')
    return redirect(url_for('books.index'))


@books_bp.route('/init-branches')
@login_required
def init_branches():
    if current_user.role.name != 'admin':
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('books.index'))

    if Branch.query.first():
        flash('Филиалы уже существуют', 'info')
        return redirect(url_for('books.index'))

    branches = [
        ('Центральная библиотека', 'ул. Ленина, 1', '+7 (123) 456-78-90'),
        ('Филиал №1', 'ул. Гагарина, 15', '+7 (123) 456-78-91'),
        ('Филиал №2', 'пр. Победы, 78', '+7 (123) 456-78-92'),
        ('Детская библиотека', 'ул. Пушкина, 10', '+7 (123) 456-78-93'),
    ]

    for name, address, phone in branches:
        branch = Branch(name=name, address=address, phone=phone)
        db.session.add(branch)

    db.session.commit()
    flash('Тестовые филиалы добавлены', 'success')
    return redirect(url_for('books.index'))


@books_bp.route('/book/<int:book_id>/branches/update', methods=['POST'])
@login_required
def branches_update(book_id):
    if current_user.role.name != 'admin':
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('books.index'))

    book = Book.query.get_or_404(book_id)
    branch_id = request.form.get('branch_id', type=int)

    if not branch_id:
        flash('Выберите филиал', 'danger')
        return redirect(url_for('books.branches', book_id=book.id))

    try:
        total = max(0, int(request.form.get('total', 0)))
        available = max(0, int(request.form.get('available', 0)))
        issued = max(0, int(request.form.get('issued', 0)))
        popularity = max(0, int(request.form.get('popularity', 0)))
    except (TypeError, ValueError):
        flash('Все значения должны быть целыми числами', 'danger')
        return redirect(url_for('books.branches', book_id=book.id))

    if available + issued != total:
        flash('Сумма "В наличии" и "Выдано" должна равняться "Всего экземпляров"', 'danger')
        return redirect(url_for('books.branches', book_id=book.id))

    book.set_branch_stats(branch_id, total, available, issued, popularity)
    flash('Данные филиала обновлены', 'success')
    return redirect(url_for('books.branches', book_id=book.id))