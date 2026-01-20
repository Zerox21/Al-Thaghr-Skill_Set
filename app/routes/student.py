from __future__ import annotations
import os, json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from .. import db
from ..models import User, Skill, StudentSkill, Question, Attempt, RemediationUpload
from ..utils import iso_year_week, generate_attempt_pdf, try_email_pdf

bp = Blueprint("student", __name__)

def _ensure_student():
    if current_user.role != "student":
        flash("Student access only.", "error")
        return False
    return True

@bp.get("/dashboard")
@login_required
def dashboard():
    if not _ensure_student():
        return redirect(url_for("auth.home"))

    teacher = User.query.filter_by(id=current_user.teacher_id, role="teacher").first()
    skills = Skill.query.filter_by(is_active=True).order_by(Skill.order_index.asc()).all()
    perms = {p.skill_id: p for p in StudentSkill.query.filter_by(student_id=current_user.id).all()}
    attempts = Attempt.query.filter_by(student_id=current_user.id).order_by(Attempt.started_at.desc()).all()

    progress = []
    for sk in skills:
        sk_attempts = [a for a in attempts if a.skill_id == sk.id and a.finished_at is not None]
        progress.append({
            "skill": sk,
            "allowed": bool(perms.get(sk.id).allowed) if perms.get(sk.id) else False,
            "times": len(sk_attempts),
            "best": int(round(max([a.score or 0 for a in sk_attempts], default=0)*100)),
            "last": sk_attempts[0].finished_at if sk_attempts else None
        })

    rem_files = RemediationUpload.query.filter_by(student_id=current_user.id).order_by(RemediationUpload.uploaded_at.desc()).all()
    return render_template("student_dashboard.html", teacher=teacher, progress=progress, attempts=attempts[:10], rem_files=rem_files)

def _weekly_limit_reached(skill_id: int) -> bool:
    now = datetime.utcnow()
    y, w = iso_year_week(now)
    q = Attempt.query.filter_by(student_id=current_user.id, iso_year=y, iso_week=w)
    if current_app.config["WEEKLY_LIMIT_SCOPE"] == "student_skill":
        q = q.filter_by(skill_id=skill_id)
    return q.count() >= current_app.config["WEEKLY_LIMIT"]

@bp.get("/start/<int:skill_id>")
@login_required
def start(skill_id: int):
    if not _ensure_student():
        return redirect(url_for("auth.home"))

    if not current_user.teacher_id:
        flash("No teacher selected. Log out and choose your teacher.", "error")
        return redirect(url_for("student.dashboard"))

    perm = StudentSkill.query.filter_by(student_id=current_user.id, skill_id=skill_id).first()
    if not perm or not perm.allowed:
        flash("This skill is locked. Your teacher must allow it.", "error")
        return redirect(url_for("student.dashboard"))

    if _weekly_limit_reached(skill_id):
        flash("Weekly access limit reached (1 attempt per week).", "error")
        return redirect(url_for("student.dashboard"))

    skill = Skill.query.get(skill_id)
    if not skill or not skill.is_active:
        flash("Skill not found.", "error")
        return redirect(url_for("student.dashboard"))

    questions = Question.query.filter_by(skill_id=skill_id).all()
    if not questions:
        flash("No questions yet for this skill (admin will add later).", "error")
        return redirect(url_for("student.dashboard"))

    now = datetime.utcnow()
    y, w = iso_year_week(now)
    attempt = Attempt(
        student_id=current_user.id,
        teacher_id=current_user.teacher_id,
        skill_id=skill_id,
        iso_year=y,
        iso_week=w,
        started_at=now
    )
    db.session.add(attempt)
    db.session.commit()

    duration_min = skill.duration_min or current_app.config["DEFAULT_TEST_DURATION_MIN"]
    return render_template("test.html", attempt=attempt, skill=skill, duration_min=duration_min, questions=questions)

@bp.post("/submit/<int:attempt_id>")
@login_required
def submit(attempt_id: int):
    if not _ensure_student():
        return redirect(url_for("auth.home"))

    attempt = Attempt.query.get(attempt_id)
    if not attempt or attempt.student_id != current_user.id:
        flash("Attempt not found.", "error")
        return redirect(url_for("student.dashboard"))
    if attempt.finished_at is not None:
        return redirect(url_for("student.result", attempt_id=attempt.id))

    skill = Skill.query.get(attempt.skill_id)
    questions = Question.query.filter_by(skill_id=attempt.skill_id).all()
    duration_min = skill.duration_min or current_app.config["DEFAULT_TEST_DURATION_MIN"]

    now = datetime.utcnow()
    max_end = attempt.started_at + timedelta(minutes=duration_min)
    finished_at = min(now, max_end)

    answers_payload = []
    correct, total = 0, 0

    for q in questions:
        total += 1
        key = f"q_{q.id}"
        raw = request.form.getlist(key) if q.qtype == "mcq_multi" else request.form.get(key)

        try:
            correct_answer = json.loads(q.answer_json) if q.answer_json else None
        except Exception:
            correct_answer = None

        is_correct = False

        if q.qtype in {"mcq_single","true_false","image_mcq_single","video_cued_mcq_single"}:
            try:
                is_correct = (raw is not None and correct_answer is not None and int(raw) == int(correct_answer))
            except Exception:
                is_correct = False
            student_disp = raw if raw is not None else "-"
            correct_disp = str(correct_answer) if correct_answer is not None else "-"

        elif q.qtype == "mcq_multi":
            try:
                chosen = sorted([int(x) for x in raw])
                corr = sorted([int(x) for x in (correct_answer or [])])
                is_correct = (chosen == corr)
                student_disp = ",".join(map(str, chosen)) if chosen else "-"
                correct_disp = ",".join(map(str, corr)) if corr else "-"
            except Exception:
                is_correct = False
                student_disp, correct_disp = "-", "-"

        elif q.qtype == "short_text":
            target = str(correct_answer or "").strip().lower()
            given = (raw or "").strip().lower()
            is_correct = bool(target) and (given == target)
            student_disp = raw or "-"
            correct_disp = str(correct_answer or "-")

        else:
            student_disp = str(raw) if raw is not None else "-"
            correct_disp = str(correct_answer) if correct_answer is not None else "-"
            is_correct = False

        if is_correct:
            correct += 1

        answers_payload.append({
            "question_id": q.id,
            "prompt": q.prompt,
            "qtype": q.qtype,
            "student_answer": student_disp,
            "correct_answer": correct_disp,
            "is_correct": is_correct
        })

    score = correct / total if total else 0.0
    attempt.finished_at = finished_at
    attempt.duration_sec = int((finished_at - attempt.started_at).total_seconds())
    attempt.score = score
    attempt.correct_count = correct
    attempt.total_count = total
    attempt.answers_json = json.dumps(answers_payload, ensure_ascii=False)

    lacking = _compute_lacking_skills(current_user.id)

    pdf_filename = f"attempt_{attempt.id}.pdf"
    pdf_abs = os.path.join(current_app.config['REPORTS_DIR'], pdf_filename)
    teacher = User.query.filter_by(id=attempt.teacher_id, role="teacher").first()

    generate_attempt_pdf(
        pdf_abs,
        school_name="Al Thaghr School",
        student_id=current_user.id,
        student_name=current_user.name,
        teacher_name=teacher.name if teacher else "-",
        skill_name=skill.name if skill else "-",
        started_at=attempt.started_at,
        finished_at=attempt.finished_at,
        duration_sec=attempt.duration_sec,
        answers=answers_payload,
        summary={
            "score_pct": int(round(score*100)),
            "correct": correct,
            "total": total,
            "lacking_skills": lacking
        }
    )
    attempt.pdf_path = pdf_filename
    db.session.commit()

    # optional email
    if teacher and teacher.email:
        try_email_pdf(
            teacher.email,
            subject=f"Student test report — {current_user.name} — {skill.name}",
            body="Attached is the PDF report for the completed test.",
            pdf_path=pdf_abs
        )

    return redirect(url_for("student.result", attempt_id=attempt.id))

def _compute_lacking_skills(student_id: str):
    rows = Attempt.query.filter_by(student_id=student_id).filter(Attempt.finished_at.isnot(None)).all()
    by_skill = {}
    for a in rows:
        by_skill.setdefault(a.skill_id, []).append(a.score or 0)
    avgs = []
    for sid, vals in by_skill.items():
        avg = sum(vals)/len(vals) if vals else 0
        avgs.append((avg, sid))
    avgs.sort(key=lambda x: x[0])
    out = []
    from ..models import Skill
    for avg, sid in avgs[:3]:
        sk = Skill.query.get(sid)
        if sk:
            out.append(sk.name)
    return out

@bp.get("/result/<int:attempt_id>")
@login_required
def result(attempt_id: int):
    if not _ensure_student():
        return redirect(url_for("auth.home"))

    attempt = Attempt.query.get(attempt_id)
    if not attempt or attempt.student_id != current_user.id:
        flash("Attempt not found.", "error")
        return redirect(url_for("student.dashboard"))

    answers = json.loads(attempt.answers_json) if attempt.answers_json else []
    skill = Skill.query.get(attempt.skill_id)
    return render_template("student_result.html", attempt=attempt, skill=skill, answers=answers)

@bp.get("/download_report/<int:attempt_id>")
@login_required
def download_report(attempt_id: int):
    if not _ensure_student():
        return redirect(url_for("auth.home"))
    return redirect(url_for("files.report", attempt_id=attempt_id))
