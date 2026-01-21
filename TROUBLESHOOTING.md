# Render troubleshooting

## Start command
Use:
gunicorn -c gunicorn.conf.py wsgi:app

This binds to 0.0.0.0:$PORT automatically (Render requirement).

## If deploy still fails
Open Render Logs and copy the traceback lines.
Most common fixes:
- Set Root Directory to the folder that contains wsgi.py and requirements.txt
- Ensure DATABASE_URL is set (if using Postgres)
- Do NOT set STORAGE_DIR=/var/data unless you attached a persistent disk
