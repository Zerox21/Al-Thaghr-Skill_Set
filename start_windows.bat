@echo off
setlocal

REM --- Create and activate venv ---
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate

REM --- Install deps ---
python -m pip install --upgrade pip
pip install -r requirements.txt

REM --- Run ---
python run.py
