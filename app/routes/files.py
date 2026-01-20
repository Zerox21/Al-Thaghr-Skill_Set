from __future__ import annotations
import os
from flask import Blueprint, current_app, send_file, abort
from flask_login import login_required, current_user
from ..models import Attempt, RemediationUpload

bp = Blueprint('files', __name__)

@bp.get('/report/<int:attempt_id>')
@login_required
def report(attempt_id: int):
    a = Attempt.query.get(attempt_id)
    if not a or not a.pdf_path:
        abort(404)

    if current_user.role == 'student' and a.student_id != current_user.id:
        abort(403)
    if current_user.role == 'teacher' and a.teacher_id != current_user.id:
        abort(403)

    abs_path = os.path.join(current_app.config['REPORTS_DIR'], a.pdf_path)
    if not os.path.exists(abs_path):
        abort(404)
    return send_file(abs_path, as_attachment=True, download_name=a.pdf_path)

@bp.get('/remediation/<int:upload_id>')
@login_required
def remediation(upload_id: int):
    u = RemediationUpload.query.get(upload_id)
    if not u:
        abort(404)

    if current_user.role == 'student' and u.student_id != current_user.id:
        abort(403)
    if current_user.role == 'teacher' and u.teacher_id != current_user.id:
        abort(403)

    abs_path = os.path.join(current_app.config['UPLOADS_DIR'], u.stored_path)
    if not os.path.exists(abs_path):
        abort(404)
    return send_file(abs_path, as_attachment=True, download_name=u.filename)

@bp.get('/media/<path:relpath>')
@login_required
def media(relpath: str):
    abs_path = os.path.join(current_app.config['MEDIA_DIR'], relpath)
    if not os.path.exists(abs_path):
        abort(404)
    return send_file(abs_path)
