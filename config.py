import os
from dotenv import load_dotenv


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(BASE_DIR, '.env'))

INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
os.makedirs(INSTANCE_DIR, exist_ok=True)

UPLOAD_DIR = os.path.join(BASE_DIR, 'static', 'images')
os.makedirs(UPLOAD_DIR, exist_ok=True)


class Config:

    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')

    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(INSTANCE_DIR, 'library.db')
    SQLALCHEMY_BINDS = {
        'auth': 'sqlite:///' + os.path.join(INSTANCE_DIR, 'users.db')
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = UPLOAD_DIR
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))

    DEBUG = os.getenv('FLASK_DEBUG', '0') == '1'