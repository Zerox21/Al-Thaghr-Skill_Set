import json
from flask import Blueprint

bp = Blueprint("filters", __name__)

@bp.app_template_filter("loads")
def loads_filter(s):
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None
