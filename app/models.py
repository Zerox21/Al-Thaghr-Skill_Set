from __future__ import annotations
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db

class User(UserMixin, db.Model):
    id = db.Column(db.String(64), primary_key=True)
    role = db.Column(db.String(16), nullable=False)  # student / teacher / chairman
    name = db.Column(db.String(128), nullable=False)
    pin_hash = db.Column(db.String(256), nullable=False)

    # Student-only
    teacher_id = db.Column(db.String(64), db.ForeignKey("user.id"), nullable=True)
    # Teacher-only
    email = db.Column(db.String(256), nullable=True)

    def set_pin(self, pin: str) -> None:
        self.pin_hash = generate_password_hash(pin)

    def check_pin(self, pin: str) -> bool:
        return check_password_hash(self.pin_hash, pin)

    def get_id(self) -> str:
        return self.id

class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    order_index = db.Column(db.Integer, default=0)
    duration_min = db.Column(db.Integer, nullable=True)
    pass_pct = db.Column(db.Integer, nullable=True)  # pass threshold percent
    is_active = db.Column(db.Boolean, default=True)

class StudentSkill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(64), db.ForeignKey("user.id"), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey("skill.id"), nullable=False)
    allowed = db.Column(db.Boolean, default=False)
    unlocked_at = db.Column(db.DateTime, nullable=True)
    locked_reason = db.Column(db.String(256), nullable=True)

    student = db.relationship("User", foreign_keys=[student_id])
    skill = db.relationship("Skill")

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    skill_id = db.Column(db.Integer, db.ForeignKey("skill.id"), nullable=False)
    qtype = db.Column(db.String(32), nullable=False)
    prompt = db.Column(db.Text, nullable=False)

    options_json = db.Column(db.Text, nullable=True)
    answer_json = db.Column(db.Text, nullable=True)
    meta_json = db.Column(db.Text, nullable=True)

    skill = db.relationship("Skill")

class Attempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(64), db.ForeignKey("user.id"), nullable=False)
    teacher_id = db.Column(db.String(64), db.ForeignKey("user.id"), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey("skill.id"), nullable=False)

    iso_year = db.Column(db.Integer, nullable=False)
    iso_week = db.Column(db.Integer, nullable=False)

    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    finished_at = db.Column(db.DateTime, nullable=True)
    duration_sec = db.Column(db.Integer, nullable=True)

    score = db.Column(db.Float, nullable=True)
    correct_count = db.Column(db.Integer, nullable=True)
    total_count = db.Column(db.Integer, nullable=True)
    passed = db.Column(db.Boolean, nullable=True)

    answers_json = db.Column(db.Text, nullable=True)
    pdf_path = db.Column(db.String(512), nullable=True)

    student = db.relationship("User", foreign_keys=[student_id])
    teacher = db.relationship("User", foreign_keys=[teacher_id])
    skill = db.relationship("Skill")

class RemediationUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.String(64), db.ForeignKey("user.id"), nullable=False)
    student_id = db.Column(db.String(64), db.ForeignKey("user.id"), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey("skill.id"), nullable=False)

    filename = db.Column(db.String(256), nullable=False)
    stored_path = db.Column(db.String(512), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    note = db.Column(db.String(512), nullable=True)

    teacher = db.relationship("User", foreign_keys=[teacher_id])
    student = db.relationship("User", foreign_keys=[student_id])
    skill = db.relationship("Skill")
