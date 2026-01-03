import firebase_admin
from firebase_admin import credentials, firestore
import random

# --- Initialize Firestore ---
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
except Exception as e:
    print(f"Error initializing Firebase: {e}\nPlease ensure 'serviceAccountKey.json' is present.")
    exit()

db = firestore.client()

# ==============================================================================
# --- DATA DEFINITIONS ---
# ==============================================================================

first_names = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Krishna", "Ishaan", "Shaurya",
    "Ananya", "Diya", "Pari", "Aadhya", "Navya", "Ira", "Anika", "Myra", "Aarohi", "Saanvi"
]
last_names = [
    "Patel", "Sharma", "Iyer", "Nair", "Menon", "Reddy", "Rao", "Kumar", "Gupta", "Singh",
    "Chopra", "Joshi", "Mehta", "Deshmukh", "Banerjee", "Mukherjee", "Das", "Roy", "Chatterjee", "Verma"
]

prefixes = ["Dr.", "Prof.", "Mr.", "Ms."]
divisions = ["A", "B", "C"]

branches = [
    {"branchId": "CSE", "branchName": "Computer Science"},
    {"branchId": "IT", "branchName": "Information Technology"},
    {"branchId": "MECH", "branchName": "Mechanical Engineering"},
    {"branchId": "CIVIL", "branchName": "Civil Engineering"},
    {"branchId": "EEE", "branchName": "Electrical Engineering"},
    {"branchId": "ECE", "branchName": "Electronics & Communication"},
]

courses = [
    "Mathematics", "Physics", "Chemistry", "Data Structures", "DBMS", "Operating Systems",
    "Computer Networks", "AI & ML", "Web Development", "Cloud Computing", "Cyber Security",
    "Thermodynamics", "Strength of Materials", "Circuit Theory", "Digital Electronics"
]

rooms = [f"Room-{i}" for i in range(101, 151)] + [f"Lab-{i}" for i in range(1, 51)]

# ==============================================================================
# --- DATA GENERATION ---
# ==============================================================================

teachers_data = []
courses_data = []
rooms_data = []
branches_data = []

# Teachers
for i in range(20):
    fname, lname = random.choice(first_names), random.choice(last_names)
    tid = f"T{i+1:03d}"
    teachers_data.append({
        "teacherId": tid,
        "prefix": random.choice(prefixes),
        "name": f"{fname} {lname}",
        "role": "Teacher",
        "email": f"{tid.lower()}@college.edu",
        "password": tid,
        "bluetoothDeviceId": f"{random.randint(10,99)}:{random.randint(10,99)}:{random.randint(10,99)}:{random.randint(10,99)}:{random.randint(10,99)}:{random.randint(10,99)}"
    })

# Admin (default super admin)
admin_data = {
    "adminId": "ADMIN001",
    "name": "System Admin",
    "role": "Admin",
    "email": "admin@college.edu",
    "password": "admin123"
}

# Courses
for i, cname in enumerate(courses, 1):
    courses_data.append({
        "courseCode": f"C{i:03d}",
        "courseName": cname
    })

# Rooms
for r in rooms[:50]:
    rooms_data.append({"roomNumber": r})

# Branches
for branch in branches:
    for year in range(1, 5):
        for div in divisions[:2]:
            branches_data.append({
                "branchId": f"{branch['branchId']}_Y{year}_{div}",
                "branchName": branch["branchName"],
                "division": div,
                "year": year
            })

# ==============================================================================
# --- UPLOAD TO FIRESTORE ---
# ==============================================================================

print("🚀 Starting Firestore seeding...")

# Admin
db.collection("users").document(admin_data["adminId"]).set(admin_data)
print("✅ Admin user added")

# Teachers
for t in teachers_data:
    db.collection("users").document(t["teacherId"]).set(t)
print(f"✅ {len(teachers_data)} teachers added")

# --- STUDENT DATA REMOVED AS REQUESTED ---
print("ℹ️ Student seeding skipped.")

# Courses
for c in courses_data:
    db.collection("courses").document(c["courseCode"]).set(c)
print(f"✅ {len(courses_data)} courses added")

# Rooms
for r in rooms_data:
    db.collection("rooms").document(r["roomNumber"]).set(r)
print(f"✅ {len(rooms_data)} rooms added")

# Branches
for b in branches_data:
    db.collection("branches").document(b["branchId"]).set(b)
print(f"✅ {len(branches_data)} branches added")

print("\n🎉 Seeding complete: Admin + Teachers + Courses + Rooms + Branches ✅")