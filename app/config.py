import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def normalize_database_url(url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url

def _default_storage_dir():
    return os.environ.get("STORAGE_DIR", os.path.join(BASE_DIR, "..", "instance", "storage"))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "CHANGE_ME_IN_ENV")

    SQLALCHEMY_DATABASE_URI = normalize_database_url(os.environ.get("DATABASE_URL")) or (
        "sqlite:///" + os.path.join(BASE_DIR, "..", "instance", "app.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    WEEKLY_LIMIT = int(os.environ.get("WEEKLY_LIMIT", "1"))
    WEEKLY_LIMIT_SCOPE = os.environ.get("WEEKLY_LIMIT_SCOPE", "student")
    DEFAULT_TEST_DURATION_MIN = int(os.environ.get("DEFAULT_TEST_DURATION_MIN", "20"))

    STORAGE_DIR = _default_storage_dir()
    REPORTS_DIR = os.path.join(STORAGE_DIR, "reports")
    UPLOADS_DIR = os.path.join(STORAGE_DIR, "uploads")
    MEDIA_DIR = os.path.join(STORAGE_DIR, "media")

    BRAND_NAME = os.environ.get("BRAND_NAME", "Al Thaghr — Skill Tests")
    BRAND_TAGLINE = os.environ.get("BRAND_TAGLINE", "Skills • Timed Tests • Reports")
    BRAND_PRIMARY_COLOR = os.environ.get("BRAND_PRIMARY_COLOR", "#0b746a")
    BRAND_LOGO_PATH = os.environ.get("BRAND_LOGO_PATH", "/static/brand/logo.svg")
    BRAND_FAVICON_PATH = os.environ.get("BRAND_FAVICON_PATH", "/static/brand/favicon.svg")

    ALLOWED_UPLOAD_EXT = set(
        os.environ.get(
            "ALLOWED_UPLOAD_EXT",
            "pdf,doc,docx,ppt,pptx,xls,xlsx,png,jpg,jpeg,mp4,webm"
        ).split(",")
    )
    MEDIA_ALLOWED_EXT = set(
        os.environ.get("MEDIA_ALLOWED_EXT", "png,jpg,jpeg,mp4,webm,gif").split(",")
    )

    SMTP_HOST = os.environ.get("SMTP_HOST")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER")
    SMTP_PASS = os.environ.get("SMTP_PASS")
    SMTP_FROM = os.environ.get("SMTP_FROM")
    SMTP_TLS = os.environ.get("SMTP_TLS", "1") == "1"

    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
