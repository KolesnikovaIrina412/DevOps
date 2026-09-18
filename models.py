from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import check_password_hash

db = SQLAlchemy()



class Role(db.Model):
    __tablename__ = 'roles'
    __bind_key__ = 'auth'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text)
    users = db.relationship('User', back_populates='role')


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    __bind_key__ = 'auth'
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    patronymic = db.Column(db.String(100))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    role = db.relationship('Role', back_populates='users')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        parts = [self.last_name, self.first_name, self.patronymic]
        return ' '.join([p for p in parts if p]) or self.login

    def has_permission(self, action):
        role_name = self.role.name if self.role else 'user'
        if role_name == 'admin':
            return True
        if role_name == 'user':
            return action == 'view'
        return False



book_genre = db.Table(
    'book_genre',
    db.Column('book_id', db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), primary_key=True),
    db.Column('genre_id', db.Integer, db.ForeignKey('genres.id', ondelete='CASCADE'), primary_key=True)
)


class Genre(db.Model):
    __tablename__ = 'genres'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)


class Cover(db.Model):
    __tablename__ = 'covers'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    md5_hash = db.Column(db.String(32), nullable=False, unique=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), nullable=False)
    book = db.relationship('Book', back_populates='cover', foreign_keys=[book_id])


class Branch(db.Model):
    __tablename__ = 'branches'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    address = db.Column(db.String(300), nullable=False)
    phone = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.now)


class BookCopy(db.Model):
    __tablename__ = 'book_copies'
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id', ondelete='CASCADE'), nullable=False)
    inventory_number = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), default='available')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    book = db.relationship('Book', back_populates='copies', foreign_keys=[book_id])
    branch = db.relationship('Branch', back_populates='copies', foreign_keys=[branch_id])
    loans = db.relationship('BookLoan', back_populates='copy', cascade='all, delete-orphan')


class BookLoan(db.Model):
    __tablename__ = 'book_loans'
    id = db.Column(db.Integer, primary_key=True)
    copy_id = db.Column(db.Integer, db.ForeignKey('book_copies.id', ondelete='CASCADE'), nullable=False)
    loan_date = db.Column(db.DateTime, default=datetime.now, nullable=False)
    return_date = db.Column(db.DateTime)
    due_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    copy = db.relationship('BookCopy', back_populates='loans', foreign_keys=[copy_id])


class Book(db.Model):
    __tablename__ = 'books'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    publisher = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    genres = db.relationship('Genre', secondary=book_genre, lazy='subquery',
                             backref=db.backref('books', lazy=True))
    cover = db.relationship('Cover', back_populates='book', uselist=False,
                            cascade='all, delete-orphan', foreign_keys=[Cover.book_id])
    copies = db.relationship('BookCopy', back_populates='book',
                             cascade='all, delete-orphan', foreign_keys=[BookCopy.book_id])

    def get_branch_stats(self, branch_id):
        copies = BookCopy.query.filter_by(book_id=self.id, branch_id=branch_id).all()
        total = len(copies)
        available = sum(1 for c in copies if c.status == 'available')
        issued = sum(1 for c in copies if c.status == 'issued')

        popularity = BookLoan.query.join(BookCopy).filter(
            BookCopy.book_id == self.id,
            BookCopy.branch_id == branch_id
        ).count()

        return {
            'total': total,
            'available': available,
            'issued': issued,
            'popularity': popularity
        }

    def set_branch_stats(self, branch_id, total, available, issued, popularity):
        copies = BookCopy.query.filter_by(book_id=self.id, branch_id=branch_id).all()
        current_total = len(copies)

        if total > current_total:
            for i in range(total - current_total):
                inv = f"INV-{self.id}-{branch_id}-{current_total + i + 1}"
                while BookCopy.query.filter_by(inventory_number=inv).first():
                    inv += "x"
                db.session.add(BookCopy(
                    book_id=self.id,
                    branch_id=branch_id,
                    inventory_number=inv,
                    status='available'
                ))
            db.session.flush()
            copies = BookCopy.query.filter_by(book_id=self.id, branch_id=branch_id).all()
        elif total < current_total:
            to_remove = current_total - total
            free = [c for c in copies if c.status == 'available']
            other = [c for c in copies if c.status != 'available']
            for c in (free + other)[:to_remove]:
                db.session.delete(c)
            db.session.flush()
            copies = BookCopy.query.filter_by(book_id=self.id, branch_id=branch_id).all()

        for i, c in enumerate(copies):
            c.status = 'available' if i < available else 'issued'

        current_pop = BookLoan.query.join(BookCopy).filter(
            BookCopy.book_id == self.id,
            BookCopy.branch_id == branch_id
        ).count()

        if popularity > current_pop:
            issued_copies = [c for c in copies if c.status == 'issued'] or copies
            for i in range(popularity - current_pop):
                c = issued_copies[i % len(issued_copies)]
                db.session.add(BookLoan(
                    copy_id=c.id,
                    due_date=datetime.now(),
                    return_date=datetime.now(),
                ))
        elif popularity < current_pop:
            loans = BookLoan.query.join(BookCopy).filter(
                BookCopy.book_id == self.id,
                BookCopy.branch_id == branch_id
            ).order_by(BookLoan.id.desc()).limit(current_pop - popularity).all()
            for l in loans:
                db.session.delete(l)

        db.session.commit()

    def get_all_branches_stats(self):
        branches = Branch.query.all()
        stats = {}
        for branch in branches:
            stats[branch] = self.get_branch_stats(branch.id)
        return stats


Branch.copies = db.relationship('BookCopy', back_populates='branch',
                                cascade='all, delete-orphan',
                                foreign_keys=[BookCopy.branch_id])