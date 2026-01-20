import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from .config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure folders exist (SQLite + persistent storage)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.makedirs(os.path.join(project_root, "instance"), exist_ok=True)

    for p in [
        app.config.get("STORAGE_DIR"),
        app.config.get("REPORTS_DIR"),
        app.config.get("UPLOADS_DIR"),
        app.config.get("MEDIA_DIR"),
    ]:
        if p:
            os.makedirs(p, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(user_id)

    # Jinja helpers
    from .filters import bp as filters_bp
    app.register_blueprint(filters_bp)

    from .routes.auth import bp as auth_bp
    from .routes.student import bp as student_bp
    from .routes.teacher import bp as teacher_bp
    from .routes.chairman import bp as chairman_bp
    from .routes.files import bp as files_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp, url_prefix="/student")
    app.register_blueprint(teacher_bp, url_prefix="/teacher")
    app.register_blueprint(chairman_bp, url_prefix="/chairman")
    app.register_blueprint(files_bp, url_prefix="/files")

    with app.app_context():
        db.create_all()
        from .seed import ensure_seed_data
        ensure_seed_data()

    return app
