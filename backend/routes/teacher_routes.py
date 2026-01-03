from flask import Blueprint, jsonify, request, session
from firebase_admin import firestore
from datetime import datetime, timedelta
import logging
from functools import wraps

# --------------------------------------------------------------------------
# Blueprint Setup
# --------------------------------------------------------------------------
teacher_bp = Blueprint("teacher_bp", __name__)
logger = logging.getLogger(__name__)
db = None  # Firestore reference

def init_teacher_routes(app, firestore_db):
    """Initializes the teacher routes and registers the blueprint."""
    global db
    db = firestore_db
    app.register_blueprint(teacher_bp, url_prefix="/api/teacher")

# --------------------------------------------------------------------------
# Authentication Decorator
# --------------------------------------------------------------------------
def teacher_login_required(f):
    """Decorator to ensure a user is logged in as a teacher."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'Teacher':
            return jsonify({"success": False, "error": "Authentication required. Please log in as a teacher."}), 401
        return f(*args, **kwargs)
    return decorated_function

# --------------------------------------------------------------------------
# NEW: Utility Endpoint for UI Filters
# --------------------------------------------------------------------------
@teacher_bp.route('/filters', methods=['GET'])
@teacher_login_required
def get_filter_options():
    """
    Provides unique values for branches, years, and divisions to populate UI dropdowns.
    This removes hardcoding from the frontend and makes it dynamic.
    """
    try:
        all_lectures_ref = db.collection("timetable").stream()
        
        branches = {}
        years = set()
        divisions = set()
        
        for doc in all_lectures_ref:
            lecture = doc.to_dict()
            branch_id = lecture.get("branchId")
            
            if branch_id and branch_id not in branches:
                 branches[branch_id] = branch_id 
            
            if lecture.get("year"):
                years.add(lecture.get("year"))
            if lecture.get("division"):
                divisions.add(lecture.get("division"))
        
        branch_name_map = {}
        try:
            branches_ref = db.collection("branches").stream()
            branch_name_map = {doc.id: doc.to_dict().get("name", doc.id) for doc in branches_ref}
        except Exception as e:
            logger.warning(f"Could not fetch from 'branches' collection, falling back to IDs: {e}")

        final_branches = [{"id": b_id, "name": branch_name_map.get(b_id, b_id)} for b_id in branches.keys()]

        return jsonify({
            "success": True,
            "filters": {
                "branches": sorted(final_branches, key=lambda x: x['name']),
                "years": sorted(list(years)),
                "divisions": sorted(list(divisions))
            }
        }), 200

    except Exception as e:
        logger.error(f"Error fetching filter options: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

# --------------------------------------------------------------------------
# 1. Teacher's Timetable
# --------------------------------------------------------------------------
@teacher_bp.route("/timetable", methods=["GET"])
@teacher_login_required
def get_teacher_timetable():
    """
    Fetches the logged-in teacher's personal weekly timetable, structured by day.
    """
    try:
        teacher_id = session['user_id']
        timetable_ref = db.collection("timetable").where("teacherId", "==", teacher_id).stream()
        timetable = {day: [] for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]}
        for doc in timetable_ref:
            lecture_data = {**doc.to_dict(), 'id': doc.id}
            day = lecture_data.get("day")
            if day in timetable:
                timetable[day].append(lecture_data)
        for day in timetable:
            timetable[day].sort(key=lambda x: datetime.strptime(x.get('startTime', '00:00'), '%H:%M'))
        return jsonify({"success": True, "timetable": timetable}), 200
    except Exception as e:
        logger.error(f"Error fetching timetable for teacher {session.get('user_id')}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# --------------------------------------------------------------------------
# 2. Live Lecture & Student List
# --------------------------------------------------------------------------
@teacher_bp.route("/live-lecture", methods=["GET"])
@teacher_login_required
def get_live_lecture_and_students():
    """
    Finds the current live lecture for the teacher and fetches the corresponding
    student list with attendance status for today.
    """
    try:
        teacher_id = session['user_id']
        now = datetime.now()
        today_str = now.strftime("%A")
        today_date_str = now.strftime("%Y-%m-%d")

        timetable_ref = db.collection("timetable").where("teacherId", "==", teacher_id).where("day", "==", today_str).stream()
        live_lecture = None
        for doc in timetable_ref:
            lecture = doc.to_dict()
            start_time = datetime.strptime(lecture["startTime"], "%H:%M").time()
            end_time = datetime.strptime(lecture["endTime"], "%H:%M").time()
            if start_time <= now.time() <= end_time:
                live_lecture = {**lecture, "id": doc.id}
                break

        if not live_lecture:
            return jsonify({"success": True, "message": "No live lecture right now."}), 200

        students_ref = db.collection("users").where("role", "==", "Student") \
            .where("branchId", "==", live_lecture["branchId"]) \
            .where("year", "==", live_lecture["year"]) \
            .where("division", "==", live_lecture["division"]).stream()
            
        student_list = [{**s.to_dict(), "id": s.id} for s in students_ref]
        student_ids = [s.get('studentId') for s in student_list if s.get('studentId')]

        if not student_ids:
             return jsonify({
                "success": True,
                "liveLecture": live_lecture,
                "students": []
            }), 200

        attendance_ref = db.collection("attendance") \
            .where("lectureId", "==", live_lecture["id"]) \
            .where("studentId", "in", student_ids) \
            .where("date", "==", today_date_str).stream()
        
        present_students = {record.to_dict()['studentId'] for record in attendance_ref}

        final_student_list = []
        for student in student_list:
            student_id = student.get('studentId')
            
            total_lectures_q = db.collection("attendance").where("studentId", "==", student_id).stream()
            present_lectures_q = db.collection("attendance").where("studentId", "==", student_id).where("status", "==", "Present").stream()
            
            total_count = sum(1 for _ in total_lectures_q)
            present_count = sum(1 for _ in present_lectures_q)
            
            percentage = (present_count / total_count * 100) if total_count > 0 else 100
            student['attendancePercentage'] = round(percentage, 2)
            student['atRisk'] = percentage < 75
            student['todayStatus'] = "Present" if student_id in present_students else "Absent"
            final_student_list.append(student)

        return jsonify({
            "success": True,
            "liveLecture": live_lecture,
            "students": final_student_list
        }), 200

    except Exception as e:
        logger.error(f"Error getting live lecture data: {e}", exc_info=True)
        return jsonify({"success": False, "error": "An internal server error occurred."}), 500

# --------------------------------------------------------------------------
# 3. Visual Dashboards
# --------------------------------------------------------------------------
@teacher_bp.route('/analytics/weekly-trend', methods=['GET'])
@teacher_login_required
def get_weekly_attendance_trend():
    """
    Calculates the daily attendance count for the current week based on filters.
    """
    try:
        branch_id = request.args.get('branchId')
        year = request.args.get('year')
        division = request.args.get('division')

        if not all([branch_id, year, division]):
            return jsonify({"success": False, "error": "branchId, year, and division are required."}), 400

        lectures_ref = db.collection("timetable") \
            .where("branchId", "==", branch_id) \
            .where("year", "==", int(year)) \
            .where("division", "==", division).stream()
        lecture_ids = [doc.id for doc in lectures_ref]

        if not lecture_ids:
             return jsonify({"success": True, "trend": {}, "message": "No lectures found."}), 200

        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())
        
        trend = {day: 0 for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]}
        
        attendance_ref = db.collection("attendance").where("lectureId", "in", lecture_ids).stream()
        
        for record in attendance_ref:
            att_data = record.to_dict()
            att_date_str = att_data.get("date")
            if att_date_str:
                att_date = datetime.strptime(att_date_str, "%Y-%m-%d")
                if start_of_week <= att_date < start_of_week + timedelta(days=6):
                    day_name = att_date.strftime("%A")
                    if day_name in trend:
                        trend[day_name] += 1
        
        return jsonify({"success": True, "trend": trend}), 200

    except Exception as e:
        logger.error(f"Error fetching weekly trend: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@teacher_bp.route('/analytics/branch-comparison', methods=['GET'])
@teacher_login_required
def get_branch_attendance_comparison():
    """
    Compares attendance percentages across all branches.
    """
    try:
        branches_ref = db.collection("branches").stream()
        branch_ids = {doc.id: doc.to_dict().get("name") for doc in branches_ref}
        branch_stats = {}

        for branch_id, branch_name in branch_ids.items():
            lectures_ref = db.collection("timetable").where("branchId", "==", branch_id).stream()
            lecture_ids = [doc.id for doc in lectures_ref]

            if not lecture_ids:
                branch_stats[branch_name] = 0
                continue

            total_q = db.collection("attendance").where("lectureId", "in", lecture_ids).stream()
            present_q = db.collection("attendance").where("lectureId", "in", lecture_ids).where("status", "==", "Present").stream()
            
            total_count = sum(1 for _ in total_q)
            present_count = sum(1 for _ in present_q)

            percentage = (present_count / total_count * 100) if total_count > 0 else 0
            branch_stats[branch_name] = round(percentage, 2)
            
        return jsonify({"success": True, "branch_comparison": branch_stats}), 200

    except Exception as e:
        logger.error(f"Error fetching branch comparison: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# Add these routes to teacher_routes.py

@teacher_bp.route('/attendance/editable', methods=['GET'])
@teacher_login_required
def get_editable_attendance():
    """
    Fetch attendance records that can be edited by the teacher
    """
    try:
        branch_id = request.args.get('branchId')
        year = request.args.get('year')
        division = request.args.get('division')
        start_date = request.args.get('startDate')
        end_date = request.args.get('endDate')
        
        if not all([branch_id, year, division, start_date, end_date]):
            return jsonify({"success": False, "error": "All parameters are required"}), 400
        
        # Get lectures for this branch/year/division
        lectures_ref = db.collection("timetable") \
            .where("branchId", "==", branch_id) \
            .where("year", "==", int(year)) \
            .where("division", "==", division).stream()
        
        lecture_ids = [doc.id for doc in lectures_ref]
        
        if not lecture_ids:
            return jsonify({"success": True, "attendance": []}), 200
        
        # Get attendance records
        attendance_ref = db.collection("attendance") \
            .where("lectureId", "in", lecture_ids) \
            .where("date", ">=", start_date) \
            .where("date", "<=", end_date).stream()
        
        attendance_list = []
        for record in attendance_ref:
            record_data = record.to_dict()
            record_data['id'] = record.id
            attendance_list.append(record_data)
        
        return jsonify({"success": True, "attendance": attendance_list}), 200
        
    except Exception as e:
        logger.error(f"Error fetching editable attendance: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@teacher_bp.route('/attendance/update', methods=['POST'])
@teacher_login_required
def update_attendance():
    """
    Update attendance records in bulk
    """
    try:
        data = request.get_json()
        if not data or 'changes' not in data:
            return jsonify({"success": False, "error": "No changes provided"}), 400
        
        changes = data['changes']
        batch = db.batch()
        
        for change in changes:
            record_ref = db.collection("attendance").document(change['recordId'])
            batch.update(record_ref, {
                'status': change['status'],
                'updatedAt': firestore.SERVER_TIMESTAMP,
                'modifiedBy': session['user_id']
            })
        
        batch.commit()
        
        return jsonify({"success": True, "message": f"Updated {len(changes)} records"}), 200
        
    except Exception as e:
        logger.error(f"Error updating attendance: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500