import os

# Render requires binding to 0.0.0.0 on the port given by PORT (default 10000)
bind = f"0.0.0.0:{os.environ.get('PORT','10000')}"

workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
threads = int(os.environ.get("GUNICORN_THREADS", "1"))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
