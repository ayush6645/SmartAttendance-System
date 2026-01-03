from flask import Blueprint, request, jsonify, session
from firebase_admin import firestore
import logging
from datetime import datetime, timedelta
from functools import wraps
from geopy.distance import geodesic
import face_recognition
import numpy as np
import cv2
import base64
from io import BytesIO
from PIL import Image

# --------------------------------------------------------------------------
# Blueprint Setup
# --------------------------------------------------------------------------
student_bp = Blueprint('student', __name__)
logger = logging.getLogger(__name__)
db = None

def init_student_routes(flask_app, firestore_db):
    """Initializes the student routes and registers the blueprint."""
    global db
    db = firestore_db
    flask_app.register_blueprint(student_bp, url_prefix='/api/student')

# --------------------------------------------------------------------------
# Authentication Decorator
# --------------------------------------------------------------------------
def student_login_required(f):
    """Decorator to ensure a user is logged in as a student."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'Student':
            return jsonify({"error": "Authentication required. Please log in as a student."}), 401
        return f(*args, **kwargs)
    return decorated_function

# --------------------------------------------------------------------------
# Utility Functions
# --------------------------------------------------------------------------
def normalize_bluetooth_address(address):
    """Normalize Bluetooth address by removing colons/dashes and making uppercase."""
    if not address:
        return ""
    return address.replace(':', '').replace('-', '').upper()

def normalize_bssid(bssid):
    """Normalize WiFi BSSID by removing colons and making uppercase."""
    if not bssid:
        return ""
    return bssid.replace(':', '').upper()

# --------------------------------------------------------------------------
# API Routes
# --------------------------------------------------------------------------

@student_bp.route('/dashboard', methods=['GET'])
@student_login_required
def get_dashboard_data():
    """
    Fetches the logged-in student's details and a summary of their attendance.
    """
    try:
        user_id = session['user_id']
        student_doc = db.collection('users').document(user_id).get()
        if not student_doc.exists:
            return jsonify({"error": "Student record not found"}), 404
        
        student_data = student_doc.to_dict()
        student_id = student_data.get('studentId')
        
        # Calculate attendance percentage
        attendance_ref = db.collection('attendance').where('studentId', '==', student_id)
        all_lectures_stream = attendance_ref.stream()
        present_lectures_stream = attendance_ref.where('status', '==', 'Present').stream()
        
        total_count = sum(1 for _ in all_lectures_stream)
        present_count = sum(1 for _ in present_lectures_stream)
        
        percentage = (present_count / total_count * 100) if total_count > 0 else 100
        
        return jsonify({
            "name": student_data.get('name'),
            "studentId": student_id,
            "attendance": {
                "percentage": round(percentage, 2),
                "attended": present_count,
                "total": total_count
            }
        }), 200
    except Exception as e:
        logger.error(f"Error fetching student dashboard data for user {session.get('user_id')}: {e}")
        return jsonify({"error": "Failed to fetch dashboard data due to a server error."}), 500


@student_bp.route('/timetable', methods=['GET'])
@student_login_required
def get_student_timetable():
    """
    Fetches the weekly timetable corresponding to the student's branch.
    """
    try:
        user_id = session['user_id']
        student_doc = db.collection('users').document(user_id).get()
        
        if not student_doc.exists:
            return jsonify({"error": "Student record not found"}), 404
        
        student_data = student_doc.to_dict()
        branch_id = student_data.get('branchId')
        
        if not branch_id:
            return jsonify({"error": "Student branch not found"}), 404
        
        query = db.collection('timetable').where('branchId', '==', branch_id)
        timetable_entries = query.stream()
        
        timetable = {
            'Monday': {}, 'Tuesday': {}, 'Wednesday': {}, 
            'Thursday': {}, 'Friday': {}, 'Saturday': {}
        }
        
        for entry in timetable_entries:
            entry_data = entry.to_dict()
            day = entry_data.get('day')
            lecture_num = entry_data.get('lectureNumber')
            entry_data['id'] = entry.id
            
            if day in timetable:
                timetable[day][lecture_num] = entry_data
            
        return jsonify(timetable), 200
    except Exception as e:
        logger.error(f"Error fetching timetable for user {session.get('user_id')}: {e}")
        return jsonify({"error": "Failed to fetch timetable due to a server error."}), 500


@student_bp.route('/teacher-devices', methods=['GET'])
def get_teacher_devices():
    """
    Returns all teacher Bluetooth device IDs for scanning
    This endpoint should be accessible without full authentication
    for the desktop app to work properly
    """
    try:
        teachers_ref = db.collection('users').where('role', '==', 'Teacher')
        teachers = teachers_ref.stream()
        
        device_ids = []
        for teacher in teachers:
            teacher_data = teacher.to_dict()
            if teacher_data.get('bluetoothDeviceId'):
                device_ids.append(teacher_data['bluetoothDeviceId'])
        
        logger.info(f"Found {len(device_ids)} teacher Bluetooth devices: {device_ids}")
        return jsonify({"devices": device_ids}), 200
        
    except Exception as e:
        logger.error(f"Error fetching teacher devices: {e}")
        return jsonify({"error": "Failed to fetch teacher devices"}), 500


@student_bp.route('/verify-face', methods=['POST'])
@student_login_required
def verify_face():
    """
    Verify student's face against stored encodings
    """
    try:
        user_id = session['user_id']
        
        # Get the image data from the request
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({"error": "No image data provided"}), 400
        
        # Decode the base64 image
        image_data = data['image'].split(',')[1]  # Remove data:image/jpeg;base64, prefix
        image_bytes = base64.b64decode(image_data)
        
        # Convert to numpy array
        image = Image.open(BytesIO(image_bytes))
        image_np = np.array(image)
        
        # Convert RGB to BGR (OpenCV format)
        image_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        
        # Find face locations and encodings in the current frame
        face_locations = face_recognition.face_locations(image_bgr)
        face_encodings = face_recognition.face_encodings(image_bgr, face_locations)
        
        if not face_encodings:
            return jsonify({"error": "No face detected in the image"}), 400
        
        if len(face_encodings) > 1:
            return jsonify({"error": "Multiple faces detected. Please ensure only one person is in the frame."}), 400
        
        # Get the first face encoding (assuming one face per image)
        current_face_encoding = face_encodings[0]
        
        # Get the student's stored face encoding from Firebase
        student_doc = db.collection('users').document(user_id).get()
        if not student_doc.exists:
            return jsonify({"error": "Student record not found"}), 404
        
        student_data = student_doc.to_dict()
        student_id = student_data.get('studentId')
        
        # Query face_encodings collection for this student
        face_encoding_ref = db.collection('face_encodings').where('studentId', '==', student_id).limit(1).stream()
        face_encodings_list = list(face_encoding_ref)
        
        if not face_encodings_list:
            return jsonify({"error": "No face encoding found for student"}), 404
        
        # Get the stored encoding
        stored_encoding_data = face_encodings_list[0].to_dict()
        stored_encoding = stored_encoding_data.get('encoding', [])
        
        if not stored_encoding:
            return jsonify({"error": "Invalid face encoding data"}), 400
        
        # Convert stored encoding to numpy array
        stored_encoding_np = np.array(stored_encoding)
        
        # Compare faces
        face_distance = face_recognition.face_distance([stored_encoding_np], current_face_encoding)[0]
        face_match = face_distance < 0.6  # Threshold for match (adjust as needed)
        
        logger.info(f"Face verification - Student: {student_id}, Distance: {face_distance:.4f}, Match: {face_match}")
        
        if face_match:
             # Store verification time in session for secure attendance marking
            session['face_verified_at'] = datetime.now().isoformat()
            
            return jsonify({
                "match": True,
                "distance": float(face_distance),
                "threshold": 0.6,
                "message": "Face verified successfully"
            }), 200
        else:
            return jsonify({
                "match": False,
                "distance": float(face_distance),
                "threshold": 0.6,
                "message": "Face verification failed"
            }), 200
        
    except Exception as e:
        logger.error(f"Error in face verification: {e}")
        return jsonify({"error": "Face verification failed due to server error"}), 500


@student_bp.route('/mark-attendance', methods=['POST'])
@student_login_required
def mark_attendance():
    """
    Marks attendance with comprehensive validation including location, WiFi, Bluetooth, and face recognition
    """
    try:
        data = request.get_json()
        user_id = session['user_id']
        
        # Get student data
        student_doc = db.collection('users').document(user_id).get()
        if not student_doc.exists:
            return jsonify({"error": "Student record not found"}), 404
        
        student_data = student_doc.to_dict()
        student_id = student_data.get('studentId')

        # Validate required fields
        required_fields = ['lectureId', 'latitude', 'longitude']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        lecture_id = data.get('lectureId')
        student_latitude = data.get('latitude')
        student_longitude = data.get('longitude')
        detected_bluetooth_id = data.get('bluetoothDeviceId')
        detected_bssid = data.get('bssid')
        
        # --- Face Verification Check (Server-Side) ---
        face_verified_at = session.get('face_verified_at')
        if not face_verified_at:
            return jsonify({"error": "Face verification required before marking attendance. Please verify your face first."}), 400
        
        # Check if verification is recent (e.g., within 5 minutes)
        verified_time = datetime.fromisoformat(face_verified_at)
        if datetime.now() - verified_time > timedelta(minutes=5):
             # Clear expired session
            session.pop('face_verified_at', None)
            return jsonify({"error": "Face verification expired. Please verify again."}), 400
            
        # Clear verification after use to prevent replay (optional, but good practice)
        session.pop('face_verified_at', None)

        student_coords = (student_latitude, student_longitude)
        logger.info(f"Attendance attempt - Student: {student_id}, Lecture: {lecture_id}, Coords: {student_coords}")

        # --- Time Validation ---
        lecture_doc = db.collection('timetable').document(lecture_id).get()
        if not lecture_doc.exists:
            return jsonify({"error": "Lecture not found."}), 404
        
        lecture_data = lecture_doc.to_dict()

        try:
            now = datetime.now()
            start_time_obj = datetime.strptime(lecture_data['startTime'], '%H:%M').time()
            end_time_obj = datetime.strptime(lecture_data['endTime'], '%H:%M').time()
            lecture_start_dt = now.replace(hour=start_time_obj.hour, minute=start_time_obj.minute, second=0, microsecond=0)
            lecture_end_dt = now.replace(hour=end_time_obj.hour, minute=end_time_obj.minute, second=0, microsecond=0)

            if not (lecture_start_dt <= now <= lecture_end_dt):
                return jsonify({"error": "This lecture is not currently active."}), 400
                
        except (ValueError, KeyError) as e:
            logger.error(f"Invalid lecture time format: {e}")
            return jsonify({"error": "Invalid lecture time format"}), 400

        # --- Location Validation ---
        location_passed = False
        location_name = "unknown location"
        locations_ref = db.collection('locations').stream()
        
        for loc_doc in locations_ref:
            loc_data = loc_doc.to_dict()
            if 'location' in loc_data and isinstance(loc_data['location'], firestore.GeoPoint):
                authorized_coords = (loc_data['location'].latitude, loc_data['location'].longitude)
                try:
                    distance = geodesic(student_coords, authorized_coords).meters
                    radius = loc_data.get('radius', 100)
                    
                    logger.info(f"Location check - Distance: {distance:.2f}m, Radius: {radius}m, Place: {loc_data.get('place', 'unknown')}")
                    
                    if distance <= radius:
                        location_passed = True
                        location_name = loc_data.get('place', 'authorized location')
                        break
                except Exception as e:
                    logger.error(f"Distance calculation error: {e}")
                    continue

        if not location_passed:
            logger.warning(f"Location validation failed for student {student_id} at {student_coords}")
            return jsonify({"error": f"You are not within the allowed range of {location_name}."}), 400

        logger.info(f"Location validation passed: {location_name}")

        # --- WiFi Validation ---
        wifi_passed = False
        wifi_name = "unknown network"
        if detected_bssid:
            normalized_bssid = normalize_bssid(detected_bssid)
            wifi_ref = db.collection('wifi_networks').stream()
            
            for wifi_doc in wifi_ref:
                wifi_data = wifi_doc.to_dict()
                if wifi_data.get('bssid'):
                    stored_bssid = normalize_bssid(wifi_data['bssid'])
                    if normalized_bssid == stored_bssid:
                        wifi_passed = True
                        wifi_name = wifi_data.get('ssid', 'recognized network')
                        break

        if not wifi_passed:
            logger.warning(f"WiFi validation failed for BSSID: {detected_bssid}")
            return jsonify({"error": "You are not connected to a recognized campus network."}), 400

        logger.info(f"WiFi validation passed: {wifi_name}")

        # --- Bluetooth Validation ---
        bluetooth_passed = False
        teacher_name = "unknown teacher"
        if detected_bluetooth_id:
            normalized_bt_id = normalize_bluetooth_address(detected_bluetooth_id)
            teachers_ref = db.collection('users').where('role', '==', 'Teacher').stream()
            
            for teacher_doc in teachers_ref:
                teacher_data = teacher_doc.to_dict()
                if teacher_data.get('bluetoothDeviceId'):
                    stored_bt_id = normalize_bluetooth_address(teacher_data['bluetoothDeviceId'])
                    if normalized_bt_id == stored_bt_id:
                        bluetooth_passed = True
                        teacher_name = teacher_data.get('name', 'teacher')
                        break

        if not bluetooth_passed:
            logger.warning(f"Bluetooth validation failed. Detected: {detected_bluetooth_id}")
            return jsonify({"error": "Teacher's device was not detected in range."}), 400

        logger.info(f"Bluetooth validation passed: {teacher_name}'s device")

        # --- Check for duplicate attendance ---
        existing_attendance_query = db.collection('attendance')\
            .where('studentId', '==', student_id)\
            .where('lectureId', '==', lecture_id)\
            .limit(1).stream()
            
        if sum(1 for _ in existing_attendance_query) > 0:
            return jsonify({"error": "You have already marked attendance for this lecture."}), 400

        # --- Save Attendance Record ---
        attendance_record = {
            "studentId": student_id,
            "lectureId": lecture_id,
            "courseCode": lecture_data.get('courseCode', 'Unknown'),
            "timestamp": firestore.SERVER_TIMESTAMP,
            "status": "Present",
            "validationMethod": "GPS+WiFi+Bluetooth+Face",
            "location": firestore.GeoPoint(student_latitude, student_longitude),
            "bssid": detected_bssid,
            "bluetoothDeviceId": detected_bluetooth_id,
            "validatedLocation": location_name,
            "validatedWifi": wifi_name,
            "validatedTeacher": teacher_name,
            "faceVerified": True
        }
        
        db.collection('attendance').add(attendance_record)
        logger.info(f"Attendance marked successfully for student {student_id} in lecture {lecture_data.get('courseCode', 'Unknown')}")

        return jsonify({
            "message": "Attendance marked successfully!",
            "details": {
                "location_validated": location_passed,
                "wifi_validated": wifi_passed,
                "bluetooth_validated": bluetooth_passed,
                "face_verified": True,
                "location": location_name,
                "wifi_network": wifi_name,
                "teacher": teacher_name
            }
        }), 201

    except Exception as e:
        logger.error(f"Critical error marking attendance: {str(e)}", exc_info=True)
        return jsonify({"error": "An internal server error occurred."}), 500


@student_bp.route('/attendance-history', methods=['GET'])
@student_login_required
def get_attendance_history():
    """
    Returns the student's attendance history
    """
    try:
        user_id = session['user_id']
        student_doc = db.collection('users').document(user_id).get()
        
        if not student_doc.exists:
            return jsonify({"error": "Student record not found"}), 404
        
        student_data = student_doc.to_dict()
        student_id = student_data.get('studentId')
        
        # Get attendance records
        attendance_ref = db.collection('attendance').where('studentId', '==', student_id)
        attendance_records = attendance_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
        
        history = []
        for record in attendance_records:
            record_data = record.to_dict()
            record_data['id'] = record.id
            
            # Convert Firestore timestamp to readable format
            if 'timestamp' in record_data and hasattr(record_data['timestamp'], 'strftime'):
                record_data['timestamp'] = record_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            
            history.append(record_data)
        
        return jsonify({"attendance_history": history}), 200
        
    except Exception as e:
        logger.error(f"Error fetching attendance history: {e}")
        return jsonify({"error": "Failed to fetch attendance history"}), 500


@student_bp.route('/register-face', methods=['POST'])
@student_login_required
def register_face():
    """
    Register a new face encoding for the student
    """
    try:
        user_id = session['user_id']
        
        # Get the image data from the request
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({"error": "No image data provided"}), 400
        
        # Decode the base64 image
        image_data = data['image'].split(',')[1]  # Remove data:image/jpeg;base64, prefix
        image_bytes = base64.b64decode(image_data)
        
        # Convert to numpy array
        image = Image.open(BytesIO(image_bytes))
        image_np = np.array(image)
        
        # Convert RGB to BGR (OpenCV format)
        image_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        
        # Find face locations and encodings in the current frame
        face_locations = face_recognition.face_locations(image_bgr)
        face_encodings = face_recognition.face_encodings(image_bgr, face_locations)
        
        if not face_encodings:
            return jsonify({"error": "No face detected in the image"}), 400
        
        if len(face_encodings) > 1:
            return jsonify({"error": "Multiple faces detected. Please ensure only one person is in the frame."}), 400
        
        # Get the first face encoding
        face_encoding = face_encodings[0].tolist()  # Convert to list for Firestore
        
        # Get student data
        student_doc = db.collection('users').document(user_id).get()
        if not student_doc.exists:
            return jsonify({"error": "Student record not found"}), 404
        
        student_data = student_doc.to_dict()
        student_id = student_data.get('studentId')
        
        # Check if face encoding already exists
        existing_face_ref = db.collection('face_encodings').where('studentId', '==', student_id).limit(1).stream()
        existing_faces = list(existing_face_ref)
        
        face_data = {
            "studentId": student_id,
            "userId": user_id,
            "encoding": face_encoding,
            "createdAt": firestore.SERVER_TIMESTAMP
        }
        
        if existing_faces:
            # Update existing face encoding
            existing_face_id = existing_faces[0].id
            db.collection('face_encodings').document(existing_face_id).set(face_data, merge=True)
            logger.info(f"Updated face encoding for student {student_id}")
        else:
            # Create new face encoding
            db.collection('face_encodings').add(face_data)
            logger.info(f"Created new face encoding for student {student_id}")
        
        return jsonify({
            "message": "Face registered successfully!",
            "details": {
                "studentId": student_id,
                "encoding_length": len(face_encoding)
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error in face registration: {e}")
        return jsonify({"error": "Face registration failed due to server error"}), 500