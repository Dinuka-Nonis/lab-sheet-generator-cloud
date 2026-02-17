import sys
import os

# ── Set path FIRST so every import below can find the modules ──
project_home = '/home/DinukaNonis/lab-sheet-generator-cloud'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# ── Environment variables ──────────────────────────────────────
os.environ['DATABASE_URL'] = 'sqlite:////home/DinukaNonis/lab-sheet-generator-cloud/labsheets.db'
os.environ['GMAIL_USER']          = 'dinukanonis49@gmail.com'       # ← change this
os.environ['GMAIL_APP_PASSWORD']  = 'apau nwur qsjd tkgg'        # ← change this
os.environ['SECRET_KEY']          = 'a8f5k9d3j2h7g4s6l1m8n0p5q2w9e7r4t6y3u8i1o0'  # ← change this (anything)
os.environ['BASE_URL']            = 'http://DinukaNonis.pythonanywhere.com'
os.environ['ONEDRIVE_CLIENT_ID']     = ''
os.environ['ONEDRIVE_CLIENT_SECRET'] = ''
os.environ['ONEDRIVE_REFRESH_TOKEN'] = ''

# ── Import app ─────────────────────────────────────────────────
from app import app as application

# ── Create DB tables on first run ─────────────────────────────
from database import init_database
try:
    init_database()
    print("Database ready!")
except Exception as e:
    print(f"DB init: {e}")
