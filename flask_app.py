"""
WSGI configuration for PythonAnywhere
Uses SQLite — no database plan needed!

HOW TO USE THIS FILE:
1. In PythonAnywhere → Web tab → click WSGI configuration file link
2. DELETE everything in it
3. PASTE this entire file
4. Edit the 4 values marked with ← CHANGE THIS
5. Click Save
6. Click Reload on the Web tab
"""

import sys
import os

# ── 1. Point to your project folder ──────────────────────────────────────────
# Replace YOUR_USERNAME with your PythonAnywhere username
project_home = '/home/DinukaNonis/lab-sheet-cloud'   # ← CHANGE THIS
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# ── 2. Environment variables ──────────────────────────────────────────────────

# SQLite — stored as a file inside your project folder. No setup needed!
os.environ['DATABASE_URL'] = f'sqlite:///{project_home}/labsheets.db'

# Your Gmail address (the one that sends emails TO students)
os.environ['GMAIL_USER'] = 'your-email@gmail.com'          # ← CHANGE THIS

# Gmail App Password (16 chars, get from Google Account → Security → App passwords)
os.environ['GMAIL_APP_PASSWORD'] = 'xxxx xxxx xxxx xxxx'   # ← CHANGE THIS

# Random secret key — paste any long random string here
os.environ['SECRET_KEY'] = 'change-this-to-any-long-random-string-abc123'  # ← CHANGE THIS

# Your PythonAnywhere URL (replace YOUR_USERNAME)
os.environ['BASE_URL'] = 'http://DinukaNonis.pythonanywhere.com'   # ← CHANGE THIS

# OneDrive — leave blank (optional feature)
os.environ['ONEDRIVE_CLIENT_ID'] = ''
os.environ['ONEDRIVE_CLIENT_SECRET'] = ''
os.environ['ONEDRIVE_REFRESH_TOKEN'] = ''

# ── 3. Load the Flask app ─────────────────────────────────────────────────────
from app import app as application

# ── 4. Create database tables on first run ────────────────────────────────────
from database import init_database
try:
    init_database()
    print("Database ready!")
except Exception as e:
    print(f"DB init note: {e}")
