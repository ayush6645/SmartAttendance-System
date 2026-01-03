from flask import Blueprint, request, jsonify, session
from firebase_admin import firestore
import logging
from functools import wraps
from datetime import datetime

# --- Blueprint Setup ---
admin_system_bp = Blueprint('admin_system', __name__)
logger = logging.getLogger(__name__)
db = None

def init_admin_system_routes(flask_app, firestore_db):
    """Initializes the admin system routes."""
    global db
    db = firestore_db
    flask_app.register_blueprint(admin_system_bp, url_prefix='/api/system')

# --- Authentication Decorator ---
def admin_login_required(f):
    """Decorator to ensure a user is logged in as an Admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # In a production app, you'd also check against a valid session token
        if 'user_id' not in session or session.get('role') != 'Admin':
            return jsonify({"error": "Authentication required. Please log in as an admin."}), 401
        return f(*args, **kwargs)
    return decorated_function

# ==============================================================================
# --- 1. ADMIN SETTINGS ENDPOINTS ---
# ==============================================================================

@admin_system_bp.route('/admin/details', methods=['PUT'])
@admin_login_required
def update_admin_details():
    """Updates the logged-in admin's own details."""
    try:
        admin_id = session['user_id']
        data = request.get_json()

        if not data or ('email' not in data and 'phone' not in data):
            return jsonify({"error": "No data provided to update."}), 400

        update_data = {}
        if 'email' in data:
            update_data['email'] = data['email'].strip()
        if 'phone' in data:
            update_data['phone'] = data['phone'].strip()
        
        update_data['updatedAt'] = firestore.SERVER_TIMESTAMP

        db.collection('users').document(admin_id).update(update_data)
        logger.info(f"Admin {admin_id} updated their details.")
        return jsonify({"message": "Your details have been updated successfully."}), 200

    except Exception as e:
        logger.error(f"Error updating admin details for {session.get('user_id')}: {e}")
        return jsonify({"error": "An internal error occurred."}), 500

@admin_system_bp.route('/admin/password', methods=['POST'])
@admin_login_required
def change_admin_password():
    """Changes the logged-in admin's own password."""
    try:
        admin_id = session['user_id']
        data = request.get_json()
        new_password = data.get('newPassword')

        if not new_password or len(new_password) < 6:
            return jsonify({"error": "Password must be at least 6 characters long."}), 400

        # In a real application, you would hash the password before saving.
        # Example: from werkzeug.security import generate_password_hash
        # hashed_password = generate_password_hash(new_password)
        update_data = {
            'password': new_password, # Storing plaintext for this project as per existing structure
            'updatedAt': firestore.SERVER_TIMESTAMP
        }

        db.collection('users').document(admin_id).update(update_data)
        logger.info(f"Admin {admin_id} changed their password.")
        return jsonify({"message": "Password updated successfully."}), 200

    except Exception as e:
        logger.error(f"Error changing admin password for {session.get('user_id')}: {e}")
        return jsonify({"error": "An internal error occurred."}), 500

# ==============================================================================
# --- 2. TEACHER MANAGEMENT ENDPOINTS ---
# ==============================================================================

@admin_system_bp.route('/teachers/no-bluetooth', methods=['GET'])
@admin_login_required
def get_teachers_without_bluetooth():
    """Gets a list of teachers with no Bluetooth ID."""
    try:
        teachers_ref = db.collection('users').where('role', '==', 'Teacher')
        all_teachers = teachers_ref.stream()
        
        teachers_list = []
        for teacher in all_teachers:
            teacher_data = teacher.to_dict()
            if not teacher_data.get('bluetoothDeviceId'):
                teachers_list.append({
                    "id": teacher.id,
                    "name": teacher_data.get('name'),
                    "teacherId": teacher_data.get('teacherId')
                })

        return jsonify(teachers_list), 200
    except Exception as e:
        logger.error(f"Error fetching teachers without Bluetooth ID: {e}")
        return jsonify({"error": "Failed to fetch teacher data."}), 500

@admin_system_bp.route('/teachers/<teacher_id>', methods=['PUT'])
@admin_login_required
def update_teacher_details(teacher_id):
    """Updates a specific teacher's details."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No update data provided."}), 400
        
        # You can add more validation here as needed
        update_data = data
        update_data['updatedAt'] = firestore.SERVER_TIMESTAMP

        db.collection('users').document(teacher_id).update(update_data)
        logger.info(f"Admin updated details for teacher {teacher_id}.")
        return jsonify({"message": "Teacher details updated successfully."}), 200
    except Exception as e:
        logger.error(f"Error updating teacher {teacher_id}: {e}")
        return jsonify({"error": "Failed to update teacher details."}), 500

@admin_system_bp.route('/teachers/<teacher_id>', methods=['DELETE'])
@admin_login_required
def remove_teacher(teacher_id):
    """Removes a teacher from the system."""
    try:
        data = request.get_json()
        reason = data.get('reason', 'No reason provided.')

        teacher_doc = db.collection('users').document(teacher_id).get()
        if not teacher_doc.exists:
            return jsonify({"error": "Teacher not found."}), 404

        # Log the removal action before deleting
        log_entry = {
            "action": "REMOVE_TEACHER",
            "targetId": teacher_id,
            "targetDetails": teacher_doc.to_dict(),
            "reason": reason,
            "adminId": session.get('user_id'),
            "timestamp": firestore.SERVER_TIMESTAMP
        }
        db.collection('audit_logs').add(log_entry)

        # Delete the user
        db.collection('users').document(teacher_id).delete()
        logger.warning(f"Admin removed teacher {teacher_id} for reason: {reason}")
        return jsonify({"message": "Teacher removed successfully."}), 200
    except Exception as e:
        logger.error(f"Error removing teacher {teacher_id}: {e}")
        return jsonify({"error": "Failed to remove teacher."}), 500

# Endpoint for resetting password can be similar to the admin password reset
# For brevity, this can be added if required, following the same pattern.

# ==============================================================================
# --- 3. STUDENT MANAGEMENT ENDPOINTS ---
# ==============================================================================

@admin_system_bp.route('/students/find', methods=['GET'])
@admin_login_required
def find_students():
    """Finds students based on branch, year, and division filters."""
    try:
        branch_id = request.args.get('branchId')
        year = request.args.get('year', type=int)
        division = request.args.get('division')

        if not all([branch_id, year, division]):
            return jsonify({"error": "Branch, Year, and Division are required."}), 400

        students_query = db.collection('users') \
            .where('role', '==', 'Student') \
            .where('branchId', '==', branch_id) \
            .where('year', '==', year) \
            .where('division', '==', division)
        
        students_docs = students_query.stream()
        
        student_list = []
        for doc in students_docs:
            student_data = doc.to_dict()
            student_id = student_data.get('studentId')

            # Calculate attendance for each student
            # Note: This is inefficient for large lists. In a production system,
            # you might store aggregated attendance data on the user document
            # and update it with a cloud function.
            total_lectures = db.collection('attendance').where('studentId', '==', student_id).stream()
            present_lectures = db.collection('attendance').where('studentId', '==', student_id).where('status', '==', 'Present').stream()
            
            total_count = sum(1 for _ in total_lectures)
            present_count = sum(1 for _ in present_lectures)
            
            attendance_percent = (present_count / total_count * 100) if total_count > 0 else 100

            student_list.append({
                "id": doc.id,
                "name": student_data.get('name'),
                "studentId": student_id,
                "email": student_data.get('email'),
                "attendance": f"{attendance_percent:.2f}%"
            })
            
        return jsonify(student_list), 200
    except Exception as e:
        logger.error(f"Error finding students: {e}")
        return jsonify({"error": "Failed to retrieve student data."}), 500

@admin_system_bp.route('/students/<student_user_id>/block', methods=['POST'])
@admin_login_required
def block_student_attendance(student_user_id):
    """Blocks a student's attendance until a specified date."""
    try:
        data = request.get_json()
        block_until = data.get('blockUntilDate')
        reason = data.get('reason')

        if not block_until or not reason:
            return jsonify({"error": "Block date and reason are required."}), 400
        
        # Convert string date 'YYYY-MM-DD' to datetime object for Firestore
        block_until_dt = datetime.strptime(block_until, '%Y-%m-%d')

        update_data = {
            "isBlocked": True,
            "blockUntil": block_until_dt,
            "blockReason": reason,
            "updatedAt": firestore.SERVER_TIMESTAMP
        }
        db.collection('users').document(student_user_id).update(update_data)
        
        logger.warning(f"Admin blocked student {student_user_id} until {block_until} for reason: {reason}")
        return jsonify({"message": "Student attendance has been blocked."}), 200
    except Exception as e:
        logger.error(f"Error blocking student {student_user_id}: {e}")
        return jsonify({"error": "Failed to block student."}), 500

@admin_system_bp.route('/students/<student_user_id>', methods=['PUT'])
@admin_login_required
def update_student_details(student_user_id):
    """Updates a specific student's details, including class assignment."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No update data provided."}), 400
        
        # Prepare the data for updating. Only include fields that are present.
        update_data = {}
        allowed_fields = ['name', 'email', 'phone', 'branchId', 'year', 'division', 'studentId']
        for field in allowed_fields:
            if field in data:
                # Ensure year is an integer if provided
                if field == 'year':
                    update_data[field] = int(data[field])
                else:
                    update_data[field] = data[field]

        if not update_data:
            return jsonify({"error": "No valid fields to update."}), 400

        update_data['updatedAt'] = firestore.SERVER_TIMESTAMP

        db.collection('users').document(student_user_id).update(update_data)
        logger.info(f"Admin updated details for student {student_user_id}.")
        return jsonify({"message": "Student details updated successfully."}), 200
    except Exception as e:
        logger.error(f"Error updating student {student_user_id}: {e}")
        return jsonify({"error": "Failed to update student details."}), 500

@admin_system_bp.route('/students/<student_user_id>/reset-password', methods=['POST'])
@admin_login_required
def reset_student_password(student_user_id):
    """Resets a student's password without needing the old one."""
    try:
        data = request.get_json()
        new_password = data.get('newPassword')

        if not new_password or len(new_password) < 6:
            return jsonify({"error": "New password must be at least 6 characters long."}), 400
        
        # In production, this password should be securely hashed.
        update_data = {
            'password': new_password, # Storing plaintext as per existing structure
            'updatedAt': firestore.SERVER_TIMESTAMP
        }
        
        db.collection('users').document(student_user_id).update(update_data)
        logger.info(f"Admin reset password for student {student_user_id}.")
        return jsonify({"message": "Student password has been reset successfully."}), 200
    except Exception as e:
        logger.error(f"Error resetting password for student {student_user_id}: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

@admin_system_bp.route('/students/<student_user_id>', methods=['DELETE'])
@admin_login_required
def remove_student(student_user_id):
    """Removes a student from the system and logs the reason."""
    try:
        data = request.get_json()
        reason = data.get('reason', 'No reason provided.')

        student_doc = db.collection('users').document(student_user_id).get()
        if not student_doc.exists:
            return jsonify({"error": "Student not found."}), 404

        # Log the removal action to an audit trail before deleting
        log_entry = {
            "action": "REMOVE_STUDENT",
            "targetId": student_user_id,
            "targetDetails": student_doc.to_dict(),
            "reason": reason,
            "adminId": session.get('user_id'),
            "timestamp": firestore.SERVER_TIMESTAMP
        }
        db.collection('audit_logs').add(log_entry)

        # Proceed with deleting the user document
        db.collection('users').document(student_user_id).delete()
        
        # You may also want to delete related data, like their face encoding and attendance records.
        # This can be done here or with a background Cloud Function.
        
        logger.warning(f"Admin removed student {student_user_id} for reason: {reason}")
        return jsonify({"message": "Student removed successfully."}), 200
    except Exception as e:
        logger.error(f"Error removing student {student_user_id}: {e}")
        return jsonify({"error": "Failed to remove student."}), 500
# Add other student management endpoints (update, remove, reset password)
# following the same patterns as the teacher endpoints.