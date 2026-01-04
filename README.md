# 🎓 Smart Attendance System V5

![Project Status](https://img.shields.io/badge/status-active-success.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3-green.svg)
![Firebase](https://img.shields.io/badge/Firebase-Firestore-orange.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

> A robust, secure, and automated desktop-based attendance management solution powered by **Face Recognition**, **Geofencing**, and **Device Fingerprinting**.

---

## 📖 Overview

**Smart Attendance System** is a modern desktop application designed to streamline the attendance process for educational institutions. Breaking away from traditional manual methods, this system ensures authenticity and security by combining biometric verification (Face ID) with physical presence checks (Location, WiFi, Bluetooth).

Built with a **Flask** backend and wrapped in **PyWebview** for a native desktop experience, it offers a seamless interface for Students, Teachers, and Administrators.

---

## ✨ Key Features

### 🔐 Security & Anti-Spoofing
*   **Face Recognition**: High-precision authentication using `dlib` and `face_recognition` libraries.
*   **Liveness/Session Checks**: Server-side validation to prevent API replay attacks or attendance spoofing.
*   **Role-Based Access Control (RBAC)**: Strict separation of duties for Admins, Teachers, and Students.

### 👤 User Portals
*   **Admin Dashboard**: 
    *   Manage Users (Students/Teachers).
    *   Configure Courses, Rooms, and Timetables.
    *   View Global Statistics and Reports.
    *   Register Face Data for users.
*   **Student Portal**: 
    *   View personalized Timetable.
    *   **Mark Attendance**: One-click check-in (requires Face + Location verification).
    *   View Attendance History and Percentage.
*   **Teacher Portal**: 
    *   View assigned classes.
    *   Manual override for attendance.
    *   Generate attendance reports.

### 📡 Smart Presence Detection (Experimental)
*   Integrates local hardware scanning to verify physical presence:
    *   **WiFi SSID Matching**: Ensures student is connected to the campus network.
    *   **Bluetooth Beaconing**: (Optional) Detects proximity to classroom beacons/teacher devices.

---

## 🛠️ Technology Stack

*   **Core Logic**: Python 3.12
*   **Web Framework**: Flask (REST API structure)
*   **GUI Wrapper**: PyWebview (Chromium-based desktop window)
*   **Database**: Google Firebase (Firestore) for real-time data syncing.
*   **Computer Vision**: OpenCV, Face_Recognition
*   **Packaging**: PyInstaller (Standalone `.exe` build)

---


### 🔑 Login Credentials (Demo Accounts)

*   **👨‍💼 Admin Login (Super User)**:
    *   **Email**: `admin@college.edu`
    *   **Password**: `admin123`
    *   ** Capabilities**: Can **register new Students**, **Teachers**, and **add more Admins**.

*   **🎓 Student Login (Sample)**:
    *   **Email**: `gyan.gupta@student.edu.in`
    *   **Password**: `ayush123`

*   **👨‍🏫 Faculty (Teacher) Login**:
    *   **Email**: `anyname@teacher.edu.in` (Must be manually registered by Admin first)
    *   **Default Password**: `teacher123`

> **Note**: The Admin account has full privileges to manage the entire system, including creating new users and assigning roles.

---

## 🚀 Quick Start (For Users)
> **No Python or Code Installation Required!**

1.  **Download**: Go to the **[Releases](https://github.com/ayush6645/SmartAttendance-System/releases)** section.
2.  **Get the App**: Download the latest `SmartAttendance.exe`.
3.  **Run**: Double-click the file to start the application immediately. 
    *   *Note: First launch might take a few seconds to initialize.*

---

## 👨‍💻 Developer Setup (Source Code)
Follow these steps ONLY if you want to modify the code or build it yourself.

### Prerequisites
1.  Python 3.10 or higher.
2.  C++ Build Tools (required for compiling `dlib` on Windows).

### 1. Clone the Repository
```bash
git clone https://github.com/ayush6645/SmartAttendance-System.git
cd SmartAttendance-System
```

### 2. Set up Virtual Environment
```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Firebase
1.  Go to your Firebase Console.
2.  Generate a new Private Key for your Service Account.
3.  Download the JSON file and rename it to `serviceAccountKey.json`.
4.  Place it in the root directory.

### 5. Run Locally
```bash
python run_desktop.py
```

### 6. Build Executable (Optional)
To package your modified code into a new `.exe`:
```bash
# Clean old builds
rmdir /s /q build dist
# Run build script
python build_exe.py
```

---

## 🧪 Testing

The project includes a suite of unit tests to ensure security and stability.

```bash
# Run all tests
python -m unittest discover tests

# Run specific security tests
python -m unittest tests/test_admin_security.py
```

---

## 📂 Project Structure

```text
attendance_system/
├── backend/
│   ├── routes/          # API endpoints (Auth, Admin, Student, Teacher)
│   └── ...
├── frontend/            # HTML/CSS/JS Assets
├── tests/               # Unit and Integration Tests
├── run_desktop.py       # Main Entry Point (PyWebview)
├── build_exe.py         # PyInstaller Build Script
├── serviceAccountKey.json # Firebase Credentials (Ignored in Git)
├── requirements.txt
└── README.md
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:
1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

---

## 👤 Author

**Ayush**
*   GitHub: [@ayush6645](https://github.com/ayush6645)

---

<p align="center">Made with ❤️ for efficient campus management.</p>
