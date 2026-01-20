from __future__ import annotations
import os, re, smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, List, Tuple

from flask import current_app
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def iso_year_week(dt: datetime) -> Tuple[int, int]:
    iso = dt.isocalendar()
    return int(iso.year), int(iso.week)

def safe_filename(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return name or "file"

def _wrap(s: str, width: int) -> List[str]:
    words = s.split()
    out, line, n = [], [], 0
    for w in words:
        if n + len(w) + (1 if line else 0) > width:
            out.append(" ".join(line))
            line, n = [w], len(w)
        else:
            line.append(w)
            n += len(w) + (1 if line else 0)
    if line:
        out.append(" ".join(line))
    return out

def generate_attempt_pdf(
    out_path: str,
    *,
    school_name: str,
    student_id: str,
    student_name: str,
    teacher_name: str,
    skill_name: str,
    started_at: datetime,
    finished_at: datetime,
    duration_sec: int,
    answers: List[Dict[str, Any]],
    summary: Dict[str, Any],
):
    Path(os.path.dirname(out_path)).mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(out_path, pagesize=A4)
    width, height = A4

    y = height - 60
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, f"{school_name} — Student Test Report")
    y -= 24

    c.setFont("Helvetica", 11)
    c.drawString(40, y, f"Student: {student_name} ({student_id})"); y -= 16
    c.drawString(40, y, f"Teacher: {teacher_name}"); y -= 16
    c.drawString(40, y, f"Skill: {skill_name}"); y -= 16
    c.drawString(40, y, f"Started: {started_at.strftime('%Y-%m-%d %H:%M:%S')}  Finished: {finished_at.strftime('%Y-%m-%d %H:%M:%S')}"); y -= 16
    c.drawString(40, y, f"Time consumed: {duration_sec} sec ({round(duration_sec/60,2)} min)"); y -= 20

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Summary"); y -= 16
    c.setFont("Helvetica", 11)
    c.drawString(40, y, f"Score: {summary.get('score_pct','-')}%  Correct: {summary.get('correct','-')}/{summary.get('total','-')}"); y -= 14
    c.drawString(40, y, f"Most lacking skills (overall): {', '.join(summary.get('lacking_skills', [])) or '-'}"); y -= 22

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Answers"); y -= 16
    c.setFont("Helvetica", 10)

    for i, a in enumerate(answers, start=1):
        line = f"{i}. {a.get('prompt','')}"
        for chunk in _wrap(line, 95):
            c.drawString(40, y, chunk); y -= 12
            if y < 70:
                c.showPage(); y = height - 60; c.setFont("Helvetica", 10)

        c.drawString(55, y, f"Student answer: {a.get('student_answer','-')}"); y -= 12
        c.drawString(55, y, f"Correct answer: {a.get('correct_answer','-')}  Result: {'✅' if a.get('is_correct') else '❌'}"); y -= 16

        if y < 70:
            c.showPage(); y = height - 60; c.setFont("Helvetica", 10)

    c.save()

def try_email_pdf(to_email: str, subject: str, body: str, pdf_path: str) -> bool:
    cfg = current_app.config
    if not (cfg.get("SMTP_HOST") and cfg.get("SMTP_USER") and cfg.get("SMTP_PASS") and cfg.get("SMTP_FROM")):
        return False

    msg = EmailMessage()
    msg["From"] = cfg["SMTP_FROM"]
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with open(pdf_path, "rb") as f:
        data = f.read()
    msg.add_attachment(data, maintype="application", subtype="pdf", filename=os.path.basename(pdf_path))

    server = smtplib.SMTP(cfg["SMTP_HOST"], cfg.get("SMTP_PORT", 587))
    if cfg.get("SMTP_TLS", True):
        server.starttls()
    server.login(cfg["SMTP_USER"], cfg["SMTP_PASS"])
    server.send_message(msg)
    server.quit()
    return True
