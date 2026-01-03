import os
from flask import Flask, send_from_directory, session
import firebase_admin
from firebase_admin import credentials, firestore
import logging
from dotenv import load_dotenv # <-- Import dotenv

# --- Load Environment Variables ---
load_dotenv() # <-- Loads variables from your .env file

# Import the initializers for your route blueprints
from backend.routes.login_route import init_login_routes
from backend.routes.admin_routes import init_admin_routes
from backend.routes.student_routes import init_student_routes
from backend.routes.admin_system_route import init_admin_system_routes
from backend.routes.teacher_routes import init_teacher_routes
# --- Basic App Configuration ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# This path is correct based on your 'tree' output
FRONTEND_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend')

app = Flask(__name__, static_folder=FRONTEND_FOLDER, static_url_path='')

# --- Load the Secret Key from the .env file ---
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') # <-- Loads secret key from .env file
if not app.config['SECRET_KEY']:
    raise ValueError("No SECRET_KEY set for Flask application. Please set it in your .env file.")

# --- Firebase Initialization ---
try:
    cred_path = os.path.join(os.path.dirname(__file__), 'serviceAccountKey.json')
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    logger.info("Firebase connection successful.")
except Exception as e:
    logger.error(f"Error initializing Firebase: {e}")
    db = None

# --- Register Blueprints (API Routes) ---
if db:
    init_login_routes(app, db)
    init_admin_routes(app, db)
    init_student_routes(app, db)
    init_admin_system_routes(app, db)
    init_teacher_routes(app, db)
    logger.info("All API routes registered successfully.")
else:
    logger.error("Database not initialized. API routes will not be available.")

# --- Page Serving Routes ---

@app.route('/')
def serve_root():
    """Serves the main landing page."""
    return send_from_directory(FRONTEND_FOLDER, 'index.html') # <-- Serves index.html as the landing page

@app.route('/<path:filename>')
def serve_page(filename):
    """Serves other HTML pages like admin_dashboard.html, etc."""
    if ".." in filename or filename.startswith("/"):
        return "Not Found", 404
    return send_from_directory(FRONTEND_FOLDER, filename)

# --- Main Execution ---
if __name__ == '__main__':
    # You might need to install python-dotenv: pip install python-dotenv
    app.run(host='127.0.0.1', port=5000, debug=True)