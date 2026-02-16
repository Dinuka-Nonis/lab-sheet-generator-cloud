"""
WSGI configuration for PythonAnywhere
This file tells PythonAnywhere how to run your Flask app
"""

import sys
import os

# Add your project directory to the sys.path
project_home = '/home/YOUR_USERNAME/labsheetgenerator'  # CHANGE THIS!
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables
os.environ['DATABASE_URL'] = 'mysql+mysqlconnector://YOUR_USERNAME:YOUR_PASSWORD@YOUR_USERNAME.mysql.pythonanywhere-services.com/YOUR_USERNAME$labsheets'
os.environ['GMAIL_USER'] = 'your.email@gmail.com'  # CHANGE THIS!
os.environ['GMAIL_APP_PASSWORD'] = 'your-app-password'  # CHANGE THIS!
os.environ['SECRET_KEY'] = 'your-secret-key-here-make-it-random'  # CHANGE THIS!
os.environ['BASE_URL'] = 'https://YOUR_USERNAME.pythonanywhere.com'  # CHANGE THIS!

# Optional: OneDrive settings (uncomment if using)
# os.environ['ONEDRIVE_CLIENT_ID'] = 'your-client-id'
# os.environ['ONEDRIVE_CLIENT_SECRET'] = 'your-client-secret'
# os.environ['ONEDRIVE_REFRESH_TOKEN'] = 'your-refresh-token'

# Import your Flask app
from app import app as application  # noqa

# Initialize database on first run
from database import init_database
try:
    init_database()
    print("Database initialized successfully")
except Exception as e:
    print(f"Database initialization error: {e}")
