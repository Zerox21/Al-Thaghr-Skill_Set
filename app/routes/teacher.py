from __future__ import annotations
import os, json
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from .. import db
from ..models import User, Skill, StudentSkill, Attempt, RemediationUpload, Question
from ..utils import safe_filename

bp = Blueprint("teacher", __name__)

def _ensure_teacher():
    if current_user.role != "teacher":
        flash("Teacher access only.", "error")
        return False
    return True

@bp.get("/dashboard")
@login_required
def dashboard():
    if not _ensure_teacher():
        return redirect(url_for('auth.home'))

    students = User.query.filter_by(role="student", teacher_id=current_user.id).order_by(User.name.asc()).all()
    skills = Skill.query.filter_by(is_active=True).order_by(Skill.order_index.asc()).all()
    attempts = Attempt.query.filter_by(teacher_id=current_user.id).filter(Attempt.finished_at.isnot(None)).all()
    avg_score = round(100 * (sum([a.score or 0 for a in attempts]) / len(attempts)), 2) if attempts else 0.0

    student_rows = []
    for s in students:
        s_attempts = [a for a in attempts if a.student_id == s.id]
        student_rows.append({
            "student": s,
            "attempts": len(s_attempts),
            "avg": round(100 * (sum([a.score or 0 for a in s_attempts]) / len(s_attempts)), 1) if s_attempts else 0
        })
    return render_template("teacher_dashboard.html", students=students, skills=skills, avg_score=avg_score, student_rows=student_rows)

@bp.get("/students/<student_id>")
@login_required
def student_detail(student_id: str):
    if not _ensure_teacher():
        return redirect(url_for('auth.home'))

    student = User.query.filter_by(id=student_id, role="student", teacher_id=current_user.id).first()
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("teacher.dashboard"))

    skills = Skill.query.filter_by(is_active=True).order_by(Skill.order_index.asc()).all()
    perms = {p.skill_id: p for p in StudentSkill.query.filter_by(student_id=student.id).all()}
    attempts = Attempt.query.filter_by(student_id=student.id, teacher_id=current_user.id).order_by(Attempt.started_at.desc()).all()
    rem_files = RemediationUpload.query.filter_by(student_id=student.id, teacher_id=current_user.id).order_by(RemediationUpload.uploaded_at.desc()).all()
    return render_template("teacher_student.html", student=student, skills=skills, perms=perms, attempts=attempts, rem_files=rem_files)

@bp.post("/students/<student_id>/toggle_skill")
@login_required
def toggle_skill(student_id: str):
    if not _ensure_teacher():
        return redirect(url_for('auth.home'))

    student = User.query.filter_by(id=student_id, role="student", teacher_id=current_user.id).first()
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("teacher.dashboard"))

    skill_id = int(request.form.get("skill_id"))
    allowed = (request.form.get("allowed") == "1")

    perm = StudentSkill.query.filter_by(student_id=student.id, skill_id=skill_id).first()
    if not perm:
        perm = StudentSkill(student_id=student.id, skill_id=skill_id, allowed=allowed, unlocked_at=datetime.utcnow() if allowed else None)
        db.session.add(perm)
    else:
        perm.allowed = allowed
        if allowed and perm.unlocked_at is None:
            perm.unlocked_at = datetime.utcnow()
    db.session.commit()

    flash("Updated skill permission.", "ok")
    return redirect(url_for("teacher.student_detail", student_id=student.id))

@bp.post("/students/<student_id>/upload_remediation")
@login_required
def upload_remediation(student_id: str):
    if not _ensure_teacher():
        return redirect(url_for('auth.home'))

    student = User.query.filter_by(id=student_id, role="student", teacher_id=current_user.id).first()
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("teacher.dashboard"))

    skill_id = int(request.form.get("skill_id"))
    note = (request.form.get("note") or "").strip()

    f = request.files.get("file")
    if not f or not f.filename:
        flash("Select a file.", "error")
        return redirect(url_for("teacher.student_detail", student_id=student.id))

    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in current_app.config["ALLOWED_UPLOAD_EXT"]:
        flash("File type not allowed.", "error")
        return redirect(url_for("teacher.student_detail", student_id=student.id))

    safe = safe_filename(f.filename)
    stored_dir = os.path.join(current_app.config['UPLOADS_DIR'], 'teacher', current_user.id, student.id, str(skill_id))
    os.makedirs(stored_dir, exist_ok=True)
    stored_path = os.path.join(stored_dir, safe)
    f.save(stored_path)

    rel = os.path.relpath(stored_path, current_app.config['UPLOADS_DIR'])
    up = RemediationUpload(
        teacher_id=current_user.id,
        student_id=student.id,
        skill_id=skill_id,
        filename=safe,
        stored_path=rel,
        note=note or None
    )
    db.session.add(up)
    db.session.commit()

    flash("Uploaded successfully.", "ok")
    return redirect(url_for("teacher.student_detail", student_id=student.id))

@bp.get("/reports")
@login_required
def reports():
    if not _ensure_teacher():
        return redirect(url_for('auth.home'))

    attempts = Attempt.query.filter_by(teacher_id=current_user.id).filter(Attempt.finished_at.isnot(None)).order_by(Attempt.finished_at.desc()).limit(200).all()
    return render_template("teacher_reports.html", attempts=attempts)

@bp.get("/download_report/<int:attempt_id>")
@login_required
def download_report(attempt_id: int):
    if not _ensure_teacher():
        return redirect(url_for('auth.home'))
    return redirect(url_for('files.report', attempt_id=attempt_id))

@bp.get("/question_tool")
@login_required
def question_tool():
    if not _ensure_teacher():
        return redirect(url_for('auth.home'))

    skills = Skill.query.filter_by(is_active=True).order_by(Skill.order_index.asc()).all()
    questions = Question.query.order_by(Question.id.desc()).limit(200).all()
    return render_template("question_tool.html", skills=skills, questions=questions, role=current_user.role)

@bp.post("/question_tool/add")
@login_required
def add_question():
    if not _ensure_teacher():
        return redirect(url_for('auth.home'))

    skill_id = int(request.form.get("skill_id"))
    qtype = request.form.get("qtype")
    prompt = (request.form.get("prompt") or "").strip()
    options = (request.form.get("options") or "").strip()
    answer = (request.form.get("answer") or "").strip()
    meta = (request.form.get("meta") or "").strip()

    if not prompt:
        flash("Prompt required.", "error")
        return redirect(url_for("teacher.question_tool"))

    # options list
    options_json = None
    if options:
        opts = [x.strip() for x in options.split("\n") if x.strip()]
        options_json = json.dumps(opts, ensure_ascii=False)

    # answer
    answer_json = None
    try:
        if qtype == "mcq_multi":
            answer_json = json.dumps([int(x.strip()) for x in answer.split(",") if x.strip()], ensure_ascii=False)
        elif qtype == "short_text":
            answer_json = json.dumps(answer, ensure_ascii=False)
        else:
            answer_json = json.dumps(int(answer), ensure_ascii=False) if answer != "" else None
    except Exception:
        answer_json = None

    # meta
    meta_json = None
    if meta:
        try:
            meta_json = meta if (meta.strip().startswith("{") or meta.strip().startswith("[")) else json.dumps(meta, ensure_ascii=False)
        except Exception:
            meta_json = None

    q = Question(skill_id=skill_id, qtype=qtype, prompt=prompt, options_json=options_json, answer_json=answer_json, meta_json=meta_json)
    db.session.add(q)
    db.session.commit()

    flash("Question added.", "ok")
    return redirect(url_for("teacher.question_tool"))
