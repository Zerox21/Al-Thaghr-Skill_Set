from __future__ import annotations
import csv, io
from werkzeug.security import generate_password_hash
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from .. import db
from ..models import User, Skill, StudentSkill, Attempt, Question

bp = Blueprint("chairman", __name__)

def _ensure_admin():
    if current_user.role != "chairman":
        flash("Chairman access only.", "error")
        return False
    return True

@bp.get("/dashboard")
@login_required
def dashboard():
    if not _ensure_admin():
        return redirect(url_for('auth.home'))

    teachers = User.query.filter_by(role="teacher").all()
    students = User.query.filter_by(role="student").all()
    skills = Skill.query.filter_by(is_active=True).order_by(Skill.order_index.asc()).all()
    attempts = Attempt.query.filter(Attempt.finished_at.isnot(None)).all()

    perf = []
    for t in teachers:
        t_attempts = [a for a in attempts if a.teacher_id == t.id]
        avg = round(100 * (sum([a.score or 0 for a in t_attempts]) / len(t_attempts)), 2) if t_attempts else 0.0
        perf.append({"teacher": t, "attempts": len(t_attempts), "avg": avg})
    perf.sort(key=lambda x: x["avg"], reverse=True)

    sperf = []
    for s in students:
        s_attempts = [a for a in attempts if a.student_id == s.id]
        avg = round(100 * (sum([a.score or 0 for a in s_attempts]) / len(s_attempts)), 2) if s_attempts else 0.0
        sperf.append({"student": s, "attempts": len(s_attempts), "avg": avg})
    sperf.sort(key=lambda x: x["avg"])

    return render_template("chairman_dashboard.html", teachers=teachers, students=students, skills=skills, perf=perf, sperf=sperf)

@bp.get("/users")
@login_required
def users():
    if not _ensure_admin():
        return redirect(url_for('auth.home'))

    teachers = User.query.filter_by(role="teacher").order_by(User.name.asc()).all()
    students = User.query.filter_by(role="student").order_by(User.name.asc()).all()
    return render_template("chairman_users.html", teachers=teachers, students=students)

@bp.post("/users/add_teacher")
@login_required
def add_teacher():
    if not _ensure_admin():
        return redirect(url_for('auth.home'))

    tid = (request.form.get("tid") or "").strip()
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip()
    pin = (request.form.get("pin") or "1234").strip()

    if not tid or not name:
        flash("Teacher ID and name required.", "error")
        return redirect(url_for("chairman.users"))

    if User.query.filter_by(id=tid).first():
        flash("ID already exists.", "error")
        return redirect(url_for("chairman.users"))

    db.session.add(User(
        id=tid,
        role="teacher",
        name=name,
        email=email or None,
        pin_hash=generate_password_hash(pin),
    ))
    db.session.commit()
    flash("Teacher added.", "ok")
    return redirect(url_for("chairman.users"))

@bp.post("/users/import_students")
@login_required
def import_students():
    if not _ensure_admin():
        return redirect(url_for('auth.home'))

    f = request.files.get("csv_file")
    if not f or not f.filename:
        flash("Upload CSV file.", "error")
        return redirect(url_for("chairman.users"))

    content = f.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    created, updated = 0, 0

    skills = Skill.query.filter_by(is_active=True).order_by(Skill.order_index.asc()).all()

    for row in reader:
        sid = (row.get("student_id") or "").strip()
        name = (row.get("name") or "").strip()
        pin = (row.get("pin") or "1234").strip()
        teacher_id = (row.get("teacher_id") or "").strip()

        if not sid or not name:
            continue

        u = User.query.filter_by(id=sid, role="student").first()
        if not u:
            u = User(
                id=sid,
                role="student",
                name=name,
                teacher_id=teacher_id or None,
                pin_hash=generate_password_hash(pin),
            )
            db.session.add(u)
            created += 1
        else:
            u.name = name
            u.teacher_id = teacher_id or u.teacher_id
            updated += 1

        db.session.flush()

        for sk in skills:
            perm = StudentSkill.query.filter_by(student_id=u.id, skill_id=sk.id).first()
            if not perm:
                allowed = (sk.order_index == 1)
                db.session.add(StudentSkill(student_id=u.id, skill_id=sk.id, allowed=allowed))

    db.session.commit()
    flash(f"Students imported. Created: {created}, Updated: {updated}.", "ok")
    return redirect(url_for("chairman.users"))

@bp.get("/skills")
@login_required
def skills():
    if not _ensure_admin():
        return redirect(url_for('auth.home'))

    skills = Skill.query.order_by(Skill.order_index.asc()).all()
    return render_template("chairman_skills.html", skills=skills)

@bp.post("/skills/add")
@login_required
def add_skill():
    if not _ensure_admin():
        return redirect(url_for('auth.home'))

    name = (request.form.get("name") or "").strip()
    order_index = int(request.form.get("order_index") or "0")
    duration_min = int(request.form.get("duration_min") or "0") or None

    if not name:
        flash("Skill name required.", "error")
        return redirect(url_for("chairman.skills"))

    sk = Skill(name=name, order_index=order_index, duration_min=duration_min, is_active=True)
    db.session.add(sk)
    db.session.commit()

    students = User.query.filter_by(role="student").all()
    for stu in students:
        db.session.add(StudentSkill(student_id=stu.id, skill_id=sk.id, allowed=False))
    db.session.commit()

    flash("Skill added.", "ok")
    return redirect(url_for("chairman.skills"))

@bp.get("/question_tool")
@login_required
def question_tool():
    if not _ensure_admin():
        return redirect(url_for('auth.home'))

    skills = Skill.query.filter_by(is_active=True).order_by(Skill.order_index.asc()).all()
    questions = Question.query.order_by(Question.id.desc()).limit(500).all()
    return render_template("question_tool.html", skills=skills, questions=questions, role=current_user.role)

@bp.post("/question_tool/add")
@login_required
def add_question():
    # reuse teacher handler logic
    from ..routes.teacher import add_question as teacher_add_question
    if not _ensure_admin():
        return redirect(url_for('auth.home'))
    return teacher_add_question()

@bp.get("/attempts")
@login_required
def attempts():
    if not _ensure_admin():
        return redirect(url_for('auth.home'))

    attempts = Attempt.query.filter(Attempt.finished_at.isnot(None)).order_by(Attempt.finished_at.desc()).limit(500).all()
    return render_template("chairman_attempts.html", attempts=attempts)
