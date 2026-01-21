import os
bind = f"0.0.0.0:{os.environ.get('PORT','10000')}"
workers = int(os.environ.get('WEB_CONCURRENCY','2'))
threads = int(os.environ.get('GUNICORN_THREADS','1'))
timeout = int(os.environ.get('GUNICORN_TIMEOUT','120'))
