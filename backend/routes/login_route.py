from flask import Blueprint, request, jsonify, session # Added session import
from flask_cors import CORS, cross_origin
from firebase_admin import firestore
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint for login routes
login_bp = Blueprint('login', __name__)

# Store db reference (will be set from app.py)
db = None

# --- ADDED THIS FUNCTION ---
def init_login_routes(flask_app, db_instance):
    """Initializes the login routes and registers the blueprint."""
    global db
    db = db_instance
    # Using /api prefix for login routes
    flask_app.register_blueprint(login_bp, url_prefix='/api') 
# --- END OF ADDED FUNCTION ---

# This function is no longer needed to be called from app.py
def init_db(db_instance):
    global db
    db = db_instance

@login_bp.route('/login', methods=['POST', 'OPTIONS'])
@cross_origin()
def login():
    """
    Handle user login.
    - Sets the session on ANY successful login (normal or first-time).
    - If it's a first-time login, prompts for a password update.
    """
    if request.method == 'OPTIONS':
        return jsonify({"success": True})
        
    try:
        data = request.get_json()
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({"success": False, "message": "Email and password are required"}), 400
        
        email = data.get('email')
        password = data.get('password')
        
        users_ref = db.collection('users')
        query = users_ref.where('email', '==', email).limit(1)
        results = query.get()
        
        if not results:
            return jsonify({"success": False, "message": "Invalid email or password"}), 401
        
        user_doc = results[0]
        user_data = user_doc.to_dict()

        # Helper function to set session and prepare user data for response
        def create_user_payload():
            session['user_id'] = user_doc.id
            session['role'] = user_data.get('role', 'Unknown')
            logger.info(f"Session set for user: {email}, role: {session['role']}")
            return {
                "uid": user_doc.id, "email": email,
                "name": user_data.get('name', 'User'), "role": user_data.get('role', 'Unknown')
            }

        # Scenario 1: User has an existing password (Normal Login)
        if 'password' in user_data and user_data['password']:
            if password == user_data['password']:
                return jsonify({
                    "success": True, "message": "Login successful", 
                    "user": create_user_payload()
                }), 200
            else:
                return jsonify({"success": False, "message": "Invalid email or password"}), 401

        # Scenario 2: User has no password (First-Time Login)
        else:
            default_password_correct = False
            if email.endswith('@student.edu.in') and password == 'student123':
                default_password_correct = True
            elif email.endswith('@teacher.edu.in') and password == 'teacher123':
                default_password_correct = True
            
            if default_password_correct:
                return jsonify({
                    "success": True, "password_update_required": True,
                    "message": "Welcome! Please create a new password.",
                    "user": create_user_payload() # <-- Set session here too
                }), 200
            else:
                return jsonify({"success": False, "message": "Incorrect default password."}), 401

    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        return jsonify({"success": False, "message": "An unexpected error occurred"}), 500
    

@login_bp.route('/update-password', methods=['POST', 'OPTIONS'])
@cross_origin()
def update_password():
    """
    Update user password in Firestore.
    """
    if request.method == 'OPTIONS':
        return jsonify({"success": True})
        
    try:
        data = request.get_json()
        uid = data.get('uid')
        new_password = data.get('new_password')

        if not uid or not new_password:
            return jsonify({"success": False, "message": "User ID and new password are required"}), 400
        
        user_ref = db.collection('users').document(uid)
        user_ref.update({'password': new_password})
        
        logger.info(f"Password created/updated successfully for user: {uid}")
        
        # After updating password, log the user in by setting the session
        user_doc = user_ref.get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            session['user_id'] = uid
            session['role'] = user_data.get('role')

        return jsonify({"success": True, "message": "Password updated successfully"}), 200
            
    except Exception as e:
        logger.error(f"Firestore update error: {str(e)}")
        return jsonify({"success": False, "message": "Database error during password update"}), 500