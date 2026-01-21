from datetime import datetime
from werkzeug.security import generate_password_hash
from . import db
from .models import User, Skill, StudentSkill

def ensure_seed_data():
    # chairman
    if not User.query.filter_by(role="chairman").first():
        db.session.add(User(
            id="chairman",
            role="chairman",
            name="School Chairman",
            pin_hash=generate_password_hash("1234"),
        ))

    # teacher
    if not User.query.filter_by(id="t001").first():
        db.session.add(User(
            id="t001",
            role="teacher",
            name="Teacher A",
            email="teacherA@example.com",
            pin_hash=generate_password_hash("1234"),
        ))

    # student
    if not User.query.filter_by(id="s001").first():
        db.session.add(User(
            id="s001",
            role="student",
            name="Student One",
            teacher_id="t001",
            pin_hash=generate_password_hash("1234"),
        ))

    if Skill.query.count() == 0:
        db.session.add_all([
            Skill(name="Skill 1: Basics", order_index=1, duration_min=15, pass_pct=80),
            Skill(name="Skill 2: Intermediate", order_index=2, duration_min=20, pass_pct=80),
            Skill(name="Skill 3: Advanced", order_index=3, duration_min=25, pass_pct=80),
        ])

    db.session.commit()

    # Ensure StudentSkill rows
    students = User.query.filter_by(role="student").all()
    skills = Skill.query.order_by(Skill.order_index.asc()).all()
    for stu in students:
        for sk in skills:
            perm = StudentSkill.query.filter_by(student_id=stu.id, skill_id=sk.id).first()
            if not perm:
                allowed = (sk.order_index == 1)
                db.session.add(StudentSkill(
                    student_id=stu.id,
                    skill_id=sk.id,
                    allowed=allowed,
                    unlocked_at=datetime.utcnow() if allowed else None,
                ))
    db.session.commit()
