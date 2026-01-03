from flask import Blueprint, request, jsonify, session
from firebase_admin import firestore
import logging
from datetime import datetime
import face_recognition
import numpy as np
import base64
import io
from PIL import Image
from functools import wraps

# Create blueprint
admin_bp = Blueprint('admin', __name__)

# Initialize logger
logger = logging.getLogger(__name__)

# Global app and db reference
app = None
db = None

def init_admin_routes(flask_app, firestore_db):
    """Initialize admin routes with app and database"""
    global app, db
    app = flask_app
    db = firestore_db
    app.register_blueprint(admin_bp, url_prefix='/api/admin')

# --------------------------------------------------------------------------
# Authentication Decorator
# --------------------------------------------------------------------------
def admin_login_required(f):
    """Decorator to ensure a user is logged in as an Admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'Admin':
            return jsonify({"error": "Authentication required. Please log in as an Admin."}), 401
        return f(*args, **kwargs)
    return decorated_function

# --- User Management Routes ---
@admin_bp.route('/users', methods=['GET'])
@admin_login_required
def get_users():
    """Get all users with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        search = request.args.get('search', '')
        
        users_ref = db.collection('users')
        
        # Apply search filter if provided
        if search:
            # Fixed query syntax for Firestore
            query = users_ref.where('name', '>=', search).where('name', '<=', search + '\uf8ff')
        else:
            query = users_ref
            
        # Get total count for pagination - FIXED
        # Note: In a real production app with many users, fetching all for count is inefficient.
        # Consider using aggregation queries or maintaining a counter.
        all_users = list(query.stream())
        total_users = len(all_users)
        
        # Apply pagination manually since we consumed the stream
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_users = all_users[start_idx:end_idx]
        
        users_list = []
        for user in paginated_users:
            user_data = user.to_dict()
            user_data['id'] = user.id
            # Convert Firestore timestamps to strings
            for key, value in user_data.items():
                if hasattr(value, 'isoformat'):
                    user_data[key] = value.isoformat()
            users_list.append(user_data)
            
        return jsonify({
            'users': users_list,
            'total': total_users,
            'page': page,
            'limit': limit
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        return jsonify({"error": "Failed to fetch users", "details": str(e)}), 500
    


@admin_bp.route('/users/<user_id>', methods=['GET'])
@admin_login_required
def get_user(user_id):
    """Get a specific user by ID"""
    try:
        user_ref = db.collection('users').document(user_id)
        user = user_ref.get()
        
        if not user.exists:
            return jsonify({"error": "User not found"}), 404
            
        user_data = user.to_dict()
        user_data['id'] = user.id
        
        return jsonify(user_data), 200
        
    except Exception as e:
        logger.error(f"Error fetching user: {str(e)}")
        return jsonify({"error": "Failed to fetch user"}), 500

@admin_bp.route('/users', methods=['POST'])
@admin_login_required
def create_user():
    """Create a new user"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate required fields
        required_fields = ['name', 'email', 'role']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Validate email format
        if '@' not in data['email']:
            return jsonify({"error": "Invalid email format"}), 400
        
        # Role-specific validation
        if data['role'] == 'Student':
            student_fields = ['branchId', 'year', 'division', 'studentId']
            for field in student_fields:
                if field not in data or not data[field]:
                    return jsonify({"error": f"Missing required field for student: {field}"}), 400
        
        elif data['role'] == 'Teacher':
            teacher_fields = ['teacherId', 'bluetoothDeviceId']
            for field in teacher_fields:
                if field not in data or not data[field]:
                    return jsonify({"error": f"Missing required field for teacher: {field}"}), 400
        
        elif data['role'] == 'Admin':
            if 'adminId' not in data or not data['adminId']:
                return jsonify({"error": "Missing required field for admin: adminId"}), 400
        
        # Check if user already exists (email)
        users_ref = db.collection('users')
        existing_email = users_ref.where('email', '==', data['email']).limit(1).get()
        if len(existing_email) > 0:
            return jsonify({"error": "Email already exists"}), 400
        
        # Check for duplicate IDs
        if data['role'] == 'Student':
            existing_student = users_ref.where('studentId', '==', data['studentId']).limit(1).get()
            if len(existing_student) > 0:
                return jsonify({"error": "Student ID already exists"}), 400
        elif data['role'] == 'Teacher':
            existing_teacher = users_ref.where('teacherId', '==', data['teacherId']).limit(1).get()
            if len(existing_teacher) > 0:
                return jsonify({"error": "Teacher ID already exists"}), 400
        
        # Create user document
        user_data = {
            'name': data['name'].strip(),
            'email': data['email'].lower().strip(),
            'role': data['role'],
            'createdAt': firestore.SERVER_TIMESTAMP,
            'updatedAt': firestore.SERVER_TIMESTAMP
        }
        
        # Add role-specific fields
        if data['role'] == 'Student':
            user_data.update({
                'branchId': data['branchId'],
                'year': int(data['year']),
                'division': data['division'],
                'studentId': data['studentId'].strip()
            })
        elif data['role'] == 'Teacher':
            user_data.update({
                'teacherId': data['teacherId'].strip(),
                'bluetoothDeviceId': data['bluetoothDeviceId'].strip(),
                'prefix': data.get('prefix', '').strip()
            })
        elif data['role'] == 'Admin':
            user_data.update({
                'adminId': data['adminId'].strip()
            })
        
        # Add optional fields
        if 'phone' in data and data['phone']:
            user_data['phone'] = data['phone'].strip()
        
        # Save to Firestore
        new_user_ref = users_ref.document()
        new_user_ref.set(user_data)
        
        return jsonify({
            "message": "User created successfully",
            "userId": new_user_ref.id,
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        return jsonify({"error": "Failed to create user"}), 500

@admin_bp.route('/users/<user_id>', methods=['PUT'])
@admin_login_required
def update_user(user_id):
    """Update a user"""
    try:
        data = request.get_json()
        
        user_ref = db.collection('users').document(user_id)
        user = user_ref.get()
        
        if not user.exists:
            return jsonify({"error": "User not found"}), 404
        
        update_data = {'updatedAt': firestore.SERVER_TIMESTAMP}
        
        # Update basic fields if provided
        if 'name' in data:
            update_data['name'] = data['name'].strip()
        if 'email' in data:
            update_data['email'] = data['email'].lower().strip()
        if 'phone' in data:
            update_data['phone'] = data['phone'].strip()
        
        # Update role-specific fields
        user_data = user.to_dict()
        if user_data.get('role') == 'Student':
            student_fields = ['branchId', 'year', 'division', 'studentId']
            for field in student_fields:
                if field in data:
                    update_data[field] = data[field]
        
        user_ref.update(update_data)
        
        return jsonify({"message": "User updated successfully"}), 200
        
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        return jsonify({"error": "Failed to update user"}), 500

@admin_bp.route('/users/<user_id>', methods=['DELETE'])
@admin_login_required
def delete_user(user_id):
    """Delete a user"""
    try:
        user_ref = db.collection('users').document(user_id)
        user = user_ref.get()
        
        if not user.exists:
            return jsonify({"error": "User not found"}), 404
        
        user_ref.delete()
        
        return jsonify({"message": "User deleted successfully"}), 200
        
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        return jsonify({"error": "Failed to delete user"}), 500

# --- Timetable Management Routes ---

@admin_bp.route('/timetable', methods=['POST'])
@admin_login_required
def create_timetable_entry():
    """Create a new timetable entry"""
    try:
        data = request.get_json()
        
        is_break = data.get('courseCode') == 'BREAK'

        # Validate required fields based on whether it's a break
        if is_break:
            required_fields = ['branchId', 'year', 'division', 'day', 'lectureNumber', 'courseCode']
        else:
            # ADDED startTime and endTime to the required fields for a lecture
            required_fields = ['branchId', 'year', 'division', 'day', 'lectureNumber', 
                              'courseCode', 'teacherId', 'roomNumber', 'startTime', 'endTime']
        
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Validate lecture number range (This can be removed if not needed)
        # if not (1 <= int(data['lectureNumber']) <= 8):
        #     return jsonify({"error": "Lecture number must be between 1 and 8"}), 400
        
        # Check for timetable clashes only if it's not a break
        if not is_break:
            clash_check = check_timetable_clash(
                data['branchId'], data['year'], data['division'],
                data['day'], data['lectureNumber'], data['roomNumber'],
                data['teacherId'], data['courseCode']
            )
            
            if clash_check['hasClash']:
                return jsonify({
                    "error": "Timetable clash detected",
                    "details": clash_check['details']
                }), 400
        
        # Create timetable entry
        timetable_data = {
            'branchId': data['branchId'],
            'year': int(data['year']),
            'division': data['division'],
            'day': data['day'],
            'lectureNumber': int(data['lectureNumber']),
            'courseCode': data['courseCode'],
            'teacherId': data.get('teacherId', 'N/A'),
            'roomNumber': data.get('roomNumber', 'N/A'),
            'startTime': data.get('startTime'), # <-- ADDED START TIME
            'endTime': data.get('endTime'),     # <-- ADDED END TIME
            'createdAt': firestore.SERVER_TIMESTAMP,
            'updatedAt': firestore.SERVER_TIMESTAMP
        }
        
        # Save to Firestore
        timetable_ref = db.collection('timetable').document()
        timetable_ref.set(timetable_data)
        
        return jsonify({
            "message": "Timetable entry created successfully",
            "timetableId": timetable_ref.id
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating timetable entry: {str(e)}")
        return jsonify({"error": "Failed to create timetable entry"}), 500
    

@admin_bp.route('/timetable/<branch_id>/<year>/<division>', methods=['GET'])
@admin_login_required
def get_timetable(branch_id, year, division):
    """Get timetable for specific branch, year, and division"""
    try:
        # Construct the full branch ID format that matches how it's stored
        full_branch_id = f"{branch_id}_Y{year}_{division}"
        
        # Query the timetable collection with the correctly formatted ID
        timetable_ref = db.collection('timetable')
        query = timetable_ref.where('branchId', '==', full_branch_id)
        timetable_entries = query.stream()
        
        timetable = {
            'Monday': {}, 'Tuesday': {}, 'Wednesday': {}, 
            'Thursday': {}, 'Friday': {}, 'Saturday': {}
        }
        
        for entry in timetable_entries:
            entry_data = entry.to_dict()
            day = entry_data['day']
            lecture_num = entry_data['lectureNumber']
            entry_data['id'] = entry.id
            
            if day in timetable:
                timetable[day][lecture_num] = entry_data
        
        return jsonify(timetable), 200
        
    except Exception as e:
        logger.error(f"Error fetching timetable: {str(e)}")
        return jsonify({"error": "Failed to fetch timetable"}), 500


@admin_bp.route('/timetable/<timetable_id>', methods=['DELETE'])
@admin_login_required
def delete_timetable_entry(timetable_id):
    """Delete a timetable entry"""
    try:
        db.collection('timetable').document(timetable_id).delete()
        return jsonify({"message": "Timetable entry deleted successfully"}), 200
        
    except Exception as e:
        logger.error(f"Error deleting timetable entry: {str(e)}")
        return jsonify({"error": "Failed to delete timetable entry"}), 500

@admin_bp.route('/timetable/bulk', methods=['POST'])
@admin_login_required
def create_bulk_timetable():
    """Create multiple timetable entries at once"""
    try:
        data = request.get_json()
        
        if not data or 'entries' not in data:
            return jsonify({"error": "No entries provided"}), 400
        
        results = {
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        for entry in data['entries']:
            try:
                # Validate required fields
                required_fields = ['branchId', 'year', 'division', 'day', 'lectureNumber', 
                                  'courseCode', 'teacherId', 'roomNumber']
                for field in required_fields:
                    if field not in entry or not entry[field]:
                        raise ValueError(f"Missing required field: {field}")
                
                # Check for clashes
                clash_check = check_timetable_clash(
                    entry['branchId'], entry['year'], entry['division'],
                    entry['day'], entry['lectureNumber'], entry['roomNumber'],
                    entry['teacherId'], entry['courseCode']
                )
                
                if clash_check['hasClash']:
                    raise ValueError(f"Timetable clash: {', '.join(clash_check['details'])}")
                
                # Create timetable entry
                timetable_data = {
                    'branchId': entry['branchId'],
                    'year': int(entry['year']),
                    'division': entry['division'],
                    'day': entry['day'],
                    'lectureNumber': int(entry['lectureNumber']),
                    'courseCode': entry['courseCode'],
                    'teacherId': entry['teacherId'],
                    'roomNumber': entry['roomNumber'],
                    'createdAt': firestore.SERVER_TIMESTAMP,
                    'updatedAt': firestore.SERVER_TIMESTAMP
                }
                
                db.collection('timetable').document().set(timetable_data)
                results['successful'] += 1
                
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'entry': entry,
                    'error': str(e)
                })
        
        return jsonify(results), 201
        
    except Exception as e:
        logger.error(f"Error creating bulk timetable: {str(e)}")
        return jsonify({"error": "Failed to create bulk timetable"}), 500

# --- Utility Functions ---
def check_timetable_clash(branch_id, year, division, day, lecture_number, room_number, teacher_id, course_code):
    """Check for timetable clashes"""
    try:
        timetable_ref = db.collection('timetable')
        
        # Check room clash
        room_clash = (
            timetable_ref
            .where('roomNumber', '==', room_number)
            .where('day', '==', day)
            .where('lectureNumber', '==', int(lecture_number))
            .get()
        )
        
        # Check teacher clash
        teacher_clash = (
            timetable_ref
            .where('teacherId', '==', teacher_id)
            .where('day', '==', day)
            .where('lectureNumber', '==', int(lecture_number))
            .get()
        )
        
        # Check course clash for same branch/year/division
        course_clash = (
            timetable_ref
            .where('branchId', '==', branch_id)
            .where('year', '==', int(year))
            .where('division', '==', division)
            .where('day', '==', day)
            .where('lectureNumber', '==', int(lecture_number))
            .get()
        )
        
        clash_details = []
        has_clash = False
        
        if len(room_clash) > 0:
            has_clash = True
            clash_details.append("Room already occupied at this time")
        
        if len(teacher_clash) > 0:
            has_clash = True
            clash_details.append("Teacher already assigned at this time")
        
        if len(course_clash) > 0:
            has_clash = True
            clash_details.append("Course already scheduled for this class at this time")
        
        return {
            "hasClash": has_clash,
            "details": clash_details
        }
        
    except Exception as e:
        logger.error(f"Error checking timetable clash: {str(e)}")
        return {"hasClash": True, "details": ["Error checking clashes"]}

# --- Data Fetching Routes for Dropdowns ---
@admin_bp.route('/branches', methods=['GET'])
@admin_login_required
def get_branches():
    """Get all branches"""
    try:
        branches_ref = db.collection('branches')
        branches = branches_ref.stream()
        
        branches_list = []
        for branch in branches:
            branch_data = branch.to_dict()
            branch_data['id'] = branch.id
            branches_list.append(branch_data)
            
        return jsonify(branches_list), 200
        
    except Exception as e:
        logger.error(f"Error fetching branches: {str(e)}")
        return jsonify({"error": "Failed to fetch branches"}), 500

@admin_bp.route('/teachers', methods=['GET'])
@admin_login_required
def get_teachers():
    """Get all users with the role of Teacher"""
    try:
        # Query the 'users' collection for documents where role is 'Teacher'
        users_ref = db.collection('users')
        query = users_ref.where('role', '==', 'Teacher')
        teachers = query.stream()
        
        teachers_list = []
        for teacher in teachers:
            teacher_data = teacher.to_dict()
            teacher_data['id'] = teacher.id
            teachers_list.append(teacher_data)
            
        return jsonify(teachers_list), 200
        
    except Exception as e:
        logger.error(f"Error fetching teachers: {str(e)}")
        return jsonify({"error": "Failed to fetch teachers"}), 500
    

@admin_bp.route('/courses', methods=['GET'])
@admin_login_required
def get_courses():
    """Get all courses"""
    try:
        courses_ref = db.collection('courses')
        courses = courses_ref.stream()
        
        courses_list = []
        for course in courses:
            course_data = course.to_dict()
            course_data['id'] = course.id
            courses_list.append(course_data)
            
        return jsonify(courses_list), 200
        
    except Exception as e:
        logger.error(f"Error fetching courses: {str(e)}")
        return jsonify({"error": "Failed to fetch courses"}), 500

@admin_bp.route('/rooms', methods=['GET'])
@admin_login_required
def get_rooms():
    """Get all rooms"""
    try:
        rooms_ref = db.collection('rooms')
        rooms = rooms_ref.stream()
        
        rooms_list = []
        for room in rooms:
            room_data = room.to_dict()
            room_data['id'] = room.id
            rooms_list.append(room_data)
            
        return jsonify(rooms_list), 200
        
    except Exception as e:
        logger.error(f"Error fetching rooms: {str(e)}")
        return jsonify({"error": "Failed to fetch rooms"}), 500

# --- Statistics Routes ---
@admin_bp.route('/stats', methods=['GET'])
@admin_login_required
def get_stats():
    """Get dashboard statistics"""
    try:
        # Get user counts - FIXED query execution
        users_ref = db.collection('users')
        total_users = sum(1 for _ in users_ref.stream())
        students_count = sum(1 for _ in users_ref.where('role', '==', 'Student').stream())
        teachers_count = sum(1 for _ in users_ref.where('role', '==', 'Teacher').stream())
        
        # Get other counts - FIXED query execution
        courses_count = sum(1 for _ in db.collection('courses').stream())
        timetable_count = sum(1 for _ in db.collection('timetable').stream())
        
        return jsonify({
            'totalUsers': total_users,
            'studentsCount': students_count,
            'teachersCount': teachers_count,
            'coursesCount': courses_count,
            'timetableEntries': timetable_count
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        return jsonify({"error": "Failed to fetch statistics", "details": str(e)}), 500


@admin_bp.route('/users/<user_id>/register-face', methods=['POST'])
@admin_login_required
def register_face(user_id):
    """Receives an image, generates a face encoding, and saves it to Firestore."""
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({"error": "No image data provided"}), 400

        # Verify the user exists in the 'users' collection
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        if not user_doc.exists:
            return jsonify({"error": "User not found"}), 404

        # Decode the Base64 image sent from the frontend
        image_data_url = data['image']
        header, encoded = image_data_url.split(",", 1)
        image_bytes = base64.b64decode(encoded)

        # Load the image into a format that face_recognition can read
        image = Image.open(io.BytesIO(image_bytes))
        image_np = np.array(image)

        # Find all faces in the image. We expect only one.
        face_locations = face_recognition.face_locations(image_np)

        if len(face_locations) == 0:
            return jsonify({"error": "No face was detected in the image. Please try again."}), 400
        if len(face_locations) > 1:
            return jsonify({"error": "Multiple faces were detected. Please ensure only one person is in the frame."}), 400

        # Generate the 128-point facial embedding vector
        face_encodings = face_recognition.face_encodings(image_np, face_locations)
        face_encoding = face_encodings[0].tolist() # Convert NumPy array to a Python list for Firestore

        # Save the encoding in a new 'face_encodings' collection
        # We use the user_id as the document ID for a direct 1-to-1 link
        encoding_ref = db.collection('face_encodings').document(user_id)
        encoding_ref.set({
            'userId': user_id,
            'encoding': face_encoding,
            'createdAt': firestore.SERVER_TIMESTAMP,
            'studentId': user_doc.to_dict().get('studentId') # Link to studentId for easier queries
        })

        return jsonify({"message": "Face registered successfully"}), 201

    except Exception as e:
        logger.error(f"Error registering face for user {user_id}: {str(e)}")
        return jsonify({"error": "An internal error occurred while processing the image"}), 500