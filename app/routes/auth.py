from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from ..models import User
from .. import db

bp = Blueprint("auth", __name__)

@bp.get("/")
def home():
    if current_user.is_authenticated:
        if current_user.role == "student":
            return redirect(url_for("student.dashboard"))
        if current_user.role == "teacher":
            return redirect(url_for("teacher.dashboard"))
        if current_user.role == "chairman":
            return redirect(url_for("chairman.dashboard"))
    return redirect(url_for("auth.login"))

@bp.route("/login", methods=["GET", "POST"])
def login():
    teachers = User.query.filter_by(role="teacher").order_by(User.name.asc()).all()

    if request.method == "POST":
        role = request.form.get("role")
        user_id = (request.form.get("user_id") or "").strip()
        pin = (request.form.get("pin") or "").strip()
        teacher_id = request.form.get("teacher_id")

        if role not in {"student","teacher","chairman"}:
            flash("Invalid role.", "error")
            return render_template("login.html", teachers=teachers)

        user = User.query.filter_by(id=user_id, role=role).first()
        if not user:
            flash("Access denied: ID not found for this role.", "error")
            return render_template("login.html", teachers=teachers)

        if not user.check_pin(pin):
            flash("Wrong PIN.", "error")
            return render_template("login.html", teachers=teachers)

        if role == "student":
            if not teacher_id:
                flash("Select your teacher.", "error")
                return render_template("login.html", teachers=teachers)
            teacher = User.query.filter_by(id=teacher_id, role="teacher").first()
            if not teacher:
                flash("Teacher not found.", "error")
                return render_template("login.html", teachers=teachers)
            user.teacher_id = teacher.id
            db.session.commit()

        login_user(user)

        if role == "student":
            return redirect(url_for("student.dashboard"))
        if role == "teacher":
            return redirect(url_for("teacher.dashboard"))
        return redirect(url_for("chairman.dashboard"))

    return render_template("login.html", teachers=teachers)

@bp.get("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
