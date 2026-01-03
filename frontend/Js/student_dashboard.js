/**
 * =================================================================================
 * SMART ATTENDANCE: STUDENT DASHBOARD SCRIPT
 * =================================================================================
 * This is the complete script for the student dashboard. It handles:
 * - Fetching all user and timetable data from the backend.
 * - Dynamically rendering the UI, including stats and the daily schedule.
 * - Managing the multi-step attendance marking process.
 * - Providing clear user feedback and error handling.
 * - Desktop app integration for hardware scanning.
 */

const API_BASE = '/api/student';
let currentLecture = null; // Stores the currently active lecture object

// --- INITIALIZATION ---

/**
 * Main entry point. Fires when the page has loaded.
 */
document.addEventListener('DOMContentLoaded', () => {
    initializeDashboard();
    setupEventListeners();
    checkDesktopEnvironment();
});

/**
 * Fetches all necessary data to populate the dashboard.
 */
function initializeDashboard() {
    fetchDashboardData();
    fetchTimetableAndRender();
}

/**
 * Sets up all interactive event listeners for the page.
 */
function setupEventListeners() {
    const startCheckBtn = document.getElementById('startCheckBtn');
    if (startCheckBtn) {
        startCheckBtn.addEventListener('click', startAttendanceCheck);
    }
    const markAnotherBtn = document.getElementById('markAnotherBtn');
    if (markAnotherBtn) {
        // Re-run the check for active lectures when this button is clicked
        markAnotherBtn.addEventListener('click', fetchTimetableAndRender);
    }
}

/**
 * Checks if we're running in a desktop environment and updates UI accordingly
 */
function checkDesktopEnvironment() {
    if (window.pywebview && window.pywebview.api) {
        console.log("Running in desktop environment with hardware access");
        // You could show a desktop-specific indicator if needed
    } else {
        console.log("Running in web browser - limited hardware access");
        // Show a warning or disable certain features
        showToast("Running in browser mode. Some features may be limited.", "info");
    }
}

// --- DATA FETCHING & RENDERING ---

/**
 * Fetches the student's personal data and overall attendance statistics.
 */
async function fetchDashboardData() {
    try {
        const response = await fetch(`${API_BASE}/dashboard`, { credentials: 'include' });
        if (!response.ok) throw new Error('Could not fetch dashboard data.');
        const data = await response.json();

        // Populate header, welcome message, and user avatar
        document.querySelector('.dashboard-header h1').textContent = `Welcome back, ${data.name}!`;
        if (document.querySelector('.dropdown-header h4')) {
            document.querySelector('.dropdown-header h4').textContent = data.name;
        }
        document.getElementById('userAvatar').textContent = data.name.charAt(0).toUpperCase();

        // Populate the "Overall Attendance" stats card
        const attendanceCard = document.querySelector('.stats-grid .stat-card:first-child');
        attendanceCard.querySelector('h3').textContent = `${data.attendance.percentage}%`;
        attendanceCard.querySelector('.progress-bar').style.width = `${data.attendance.percentage}%`;
        attendanceCard.querySelector('.subtext').textContent = `${data.attendance.attended} of ${data.attendance.total} classes attended`;

    } catch (error) {
        console.error("Error fetching dashboard data:", error);
        showToast("Could not load your profile data.", "error");
    }
}

/**
 * Fetches the weekly timetable and triggers all UI updates that depend on it.
 */
async function fetchTimetableAndRender() {
    try {
        const response = await fetch(`${API_BASE}/timetable`, { credentials: 'include' });
        if (!response.ok) throw new Error('Could not fetch the timetable.');
        const timetable = await response.json();

        // Use the fetched data to update the relevant parts of the UI
        checkForCurrentLecture(timetable);
        renderTodaysSchedule(timetable);

    } catch (error) {
        console.error("Error fetching timetable:", error);
        updateMarkerUI('initial', {
            title: 'Error Loading Data',
            subtitle: 'Could not load your timetable. Please try again later.',
            buttonDisabled: true
        });
    }
}

/**
 * Dynamically generates and displays the "Today's Schedule" list.
 * @param {object} timetable - The complete weekly timetable object.
 */
function renderTodaysSchedule(timetable) {
    const now = new Date();
    const dayOfWeek = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][now.getDay()];
    const scheduleContainer = document.querySelector('.schedule-list');
    const scheduleHeader = document.querySelector('section .section-header p');

    // Update the date display
    if (scheduleHeader) {
        scheduleHeader.textContent = now.toLocaleDateString('en-US', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
        });
    }

    if (!timetable || !timetable[dayOfWeek] || Object.keys(timetable[dayOfWeek]).length === 0) {
        scheduleContainer.innerHTML = '<p>No classes scheduled for today.</p>';
        return;
    }

    // Get today's lectures, filter out breaks, and sort by start time
    const todaysLectures = Object.values(timetable[dayOfWeek])
        .filter(lec => lec.courseCode !== 'BREAK')
        .sort((a, b) => a.startTime.localeCompare(b.startTime));

    let scheduleHtml = '';
    todaysLectures.forEach(lecture => {
        const [startH, startM] = lecture.startTime.split(':').map(Number);
        const lectureStart = new Date(now.getFullYear(), now.getMonth(), now.getDate(), startH, startM);
        const [endH, endM] = lecture.endTime.split(':').map(Number);
        const lectureEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate(), endH, endM);

        let statusClass = 'upcoming';
        let statusText = 'UPCOMING';

        if (now >= lectureStart && now <= lectureEnd) {
            statusClass = 'active';
            statusText = 'ACTIVE';
        } else if (now > lectureEnd) {
            statusClass = 'finished';
            statusText = 'FINISHED';
        }

        scheduleHtml += `
            <div class="schedule-item">
                <div class="icon"><i class="fas fa-clock"></i></div>
                <div class="schedule-details">
                    <h4>${lecture.courseCode} <span class="pill ${statusClass}">${statusText}</span></h4>
                    <p>${lecture.startTime} - ${lecture.endTime} • ${lecture.teacherId} • ${lecture.roomNumber}</p>
                </div>
            </div>
        `;
    });

    scheduleContainer.innerHTML = scheduleHtml;
}

// --- ATTENDANCE MARKING LOGIC ---

/**
 * Checks the timetable for an active lecture and updates the main attendance marker.
 * @param {object} timetable - The complete weekly timetable object.
 */
function checkForCurrentLecture(timetable) {
    const now = new Date();
    const dayOfWeek = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][now.getDay()];

    if (timetable && timetable[dayOfWeek]) {
        for (const lecture of Object.values(timetable[dayOfWeek])) {
            if (!lecture.startTime || !lecture.endTime || lecture.courseCode === 'BREAK') continue;

            const [startH, startM] = lecture.startTime.split(':').map(Number);
            const lectureStart = new Date(now.getFullYear(), now.getMonth(), now.getDate(), startH, startM);
            const [endH, endM] = lecture.endTime.split(':').map(Number);
            const lectureEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate(), endH, endM);

            if (now >= lectureStart && now <= lectureEnd) {
                currentLecture = lecture;
                document.getElementById('marker-header').innerHTML = `${lecture.courseCode} <span class="pill active">ACTIVE</span>`;
                document.getElementById('marker-subheader').textContent = `Room ${lecture.roomNumber} • ${lecture.startTime} - ${lecture.endTime}`;
                updateMarkerUI('initial', { buttonDisabled: false });
                return; // Exit after finding the first active lecture
            }
        }
    }

    // This block runs if the loop completes without finding an active lecture
    currentLecture = null;
    document.getElementById('marker-header').innerHTML = `No Active Lecture`;
    document.getElementById('marker-subheader').textContent = 'Check your schedule for the next class.';
    updateMarkerUI('initial', {
        title: 'No lecture right now',
        subtitle: 'Come back when your next class starts.',
        buttonDisabled: true
    });
}

/**
 * Desktop-specific scanning function using pywebview API
 */
async function performDesktopScan() {
    if (window.pywebview && window.pywebview.api) {
        try {
            console.log("Starting desktop hardware scan...");
            updateVerificationStep('wifi', 'Scanning WiFi networks...', 'processing');
            updateVerificationStep('bluetooth', 'Scanning for teacher devices...', 'processing');

            const scanResults = await window.pywebview.api.perform_scans();
            
            if (scanResults.success) {
                console.log("Desktop scan successful:", scanResults);
                
                // Update UI with scan results
                if (scanResults.wifi_networks && scanResults.wifi_networks.length > 0) {
                    updateVerificationStep('wifi', `Found ${scanResults.wifi_networks.length} WiFi networks`, 'success');
                } else {
                    updateVerificationStep('wifi', 'No WiFi networks found', 'error');
                }

                if (scanResults.matched_bluetooth) {
                    updateVerificationStep('bluetooth', 'Teacher device detected!', 'success');
                } else {
                    updateVerificationStep('bluetooth', 'No teacher device found', 'error');
                }

                return {
                    location: scanResults.location,
                    wifiBSSID: scanResults.wifi_networks && scanResults.wifi_networks.length > 0 ? scanResults.wifi_networks[0].bssid : null,
                    bluetoothID: scanResults.matched_bluetooth
                };
            } else {
                throw new Error(scanResults.error || "Desktop scan failed");
            }
        } catch (error) {
            console.error("Desktop scan error:", error);
            updateVerificationStep('wifi', 'Scan failed', 'error');
            updateVerificationStep('bluetooth', 'Scan failed', 'error');
            throw error;
        }
    } else {
        throw new Error("Desktop API not available - running in browser mode");
    }
}

/**
 * Main function that orchestrates the entire attendance marking process.
 */
async function startAttendanceCheck() {
    if (!currentLecture) {
        showToast("Error: No active lecture found.", "error");
        return;
    }

    console.log("Starting attendance check for lecture:", currentLecture.courseCode);
    updateMarkerUI('location-scan');

    try {
        let scanData;
        
        // Use desktop scanning if available, otherwise fall back to web API
        if (window.pywebview && window.pywebview.api) {
            scanData = await performDesktopScan();
        } else {
            // Fallback to web geolocation only
            updateVerificationStep('wifi', 'Desktop mode required for WiFi', 'pending');
            updateVerificationStep('bluetooth', 'Desktop mode required for Bluetooth', 'pending');
            
            const position = await getCurrentPosition();
            scanData = {
                location: {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude
                },
                wifiBSSID: null,
                bluetoothID: null
            };
            
            updateVerificationStep('wifi', 'WiFi scan requires desktop app', 'error');
            updateVerificationStep('bluetooth', 'Bluetooth scan requires desktop app', 'error');
        }

        // Show toast notifications for scan results
        if (scanData.wifiBSSID) {
            showToast("WiFi network verified!", "success");
        } else {
            showToast("WiFi verification failed", "error");
        }

        if (scanData.bluetoothID) {
            showToast("Teacher device detected!", "success");
        } else {
            showToast("Teacher device not found", "error");
        }

        // Move to processing state
        updateMarkerUI('processing');

        // Send data to server for final validation and attendance marking
        const response = await fetch(`${API_BASE}/mark-attendance`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                lectureId: currentLecture.id,
                latitude: scanData.location.latitude,
                longitude: scanData.location.longitude,
                bssid: scanData.wifiBSSID,
                bluetoothDeviceId: scanData.bluetoothID
            })
        });

        const result = await response.json();
        console.log("Server response received:", result);

        if (response.ok) {
            updateMarkerUI('success', { 
                subtitle: result.message || "Attendance marked successfully!" 
            });
            showToast("Attendance Marked Successfully!", "success");
            
            // Refresh dashboard data to update attendance stats
            fetchDashboardData();
        } else {
            console.error("Server returned an error:", result.error);
            updateMarkerUI('initial', {
                title: 'Attendance Failed',
                subtitle: result.error || "Unknown server error",
                buttonDisabled: false
            });
            showToast(result.error || "Attendance failed", "error");
        }
    } catch (error) {
        console.error("An error occurred during the attendance check process:", error);
        updateMarkerUI('initial', {
            title: 'Check Failed',
            subtitle: error.message,
            buttonDisabled: false
        });
        showToast(error.message, "error");
    }
}

/**
 * Wraps the Geolocation API in a Promise for use with async/await.
 * @returns {Promise<GeolocationPosition>}
 */
function getCurrentPosition() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            return reject(new Error('Geolocation is not supported by your browser.'));
        }
        const options = { 
            timeout: 10000,
            enableHighAccuracy: true,
            maximumAge: 0
        };
        navigator.geolocation.getCurrentPosition(
            resolve, 
            (error) => reject(new Error(`Location error: ${error.message}`)), 
            options
        );
    });
}

// --- UI HELPER FUNCTIONS ---

/**
 * Manages which UI "state" is visible in the attendance marker card.
 * @param {string} state - The name of the state to show ('initial', 'location-scan', etc.).
 * @param {object} [options] - Optional data to update text or button states.
 */
function updateMarkerUI(state, options = {}) {
    const states = ['initial', 'location-scan', 'identity-check', 'processing', 'success'];
    states.forEach(s => {
        const el = document.getElementById(`state-${s}`);
        if (el) el.style.display = 'none';
    });
   
    const targetState = document.getElementById(`state-${state}`);
    if (!targetState) return;

    targetState.style.display = (state === 'initial') ? 'flex' : 'block';

    // Reset verification steps when not in location-scan state
    if (state !== 'location-scan') {
        updateVerificationStep('wifi', 'Checking Campus Wi-Fi...', 'pending');
        updateVerificationStep('bluetooth', 'Scanning for Classroom Beacon...', 'pending');
    }
    
    const titleEl = targetState.querySelector('.marker-title');
    const subtitleEl = targetState.querySelector('.marker-subtitle');
    const button = targetState.querySelector('button');

    if (options.title && titleEl) titleEl.textContent = options.title;
    if (options.subtitle && subtitleEl) subtitleEl.textContent = options.subtitle;
    if (typeof options.buttonDisabled !== 'undefined' && button) {
        button.disabled = options.buttonDisabled;
    }
}

/**
 * Updates a single step in the verification list UI.
 * @param {string} stepName - 'wifi' or 'bluetooth'.
 * @param {string} text - The new text to display.
 * @param {string} status - 'pending', 'success', or 'error'.
 */
function updateVerificationStep(stepName, text, status) {
    const stepEl = document.getElementById(`${stepName}-check`);
    const textEl = document.getElementById(`${stepName}-text`);
    if (stepEl && textEl) {
        textEl.textContent = text;
        stepEl.classList.remove('success', 'error', 'processing');
        if (status === 'success' || status === 'error' || status === 'processing') {
            stepEl.classList.add(status);
        }
    }
}

/**
 * Displays a temporary notification toast.
 * @param {string} message - The message for the toast.
 * @param {string} type - 'success', 'error', or 'info' for styling.
 */
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast-notification');
    if (toast) {
        toast.textContent = message;
        toast.className = `toast show ${type}`;
        setTimeout(() => {
            toast.className = toast.className.replace('show', '');
        }, 3000);
    }
}

/**
 * Utility function to format Bluetooth addresses for display
 */
function formatBluetoothAddress(address) {
    if (!address) return 'Unknown';
    return address.replace(/:/g, ':').toUpperCase();
}

/**
 * Utility function to format WiFi BSSID for display
 */
function formatBSSID(bssid) {
    if (!bssid) return 'Unknown';
    return bssid.toUpperCase();
}

// Add this function to help debug Bluetooth issues
function debugBluetoothScanning() {
    console.log("=== BLUETOOTH DEBUG INFO ===");
    console.log("Desktop API available:", !!window.pywebview?.api);
    
    if (window.pywebview?.api) {
        window.pywebview.api.perform_scans().then(results => {
            console.log("Raw scan results:", results);
            console.log("Detected Bluetooth devices:", results.bluetooth_devices);
            console.log("Teacher device match:", results.matched_bluetooth);
            
            if (results.bluetooth_devices && results.bluetooth_devices.length > 0) {
                showToast(`Found ${results.bluetooth_devices.length} Bluetooth devices`, "info");
            } else {
                showToast("No Bluetooth devices found", "error");
            }
        }).catch(error => {
            console.error("Debug scan failed:", error);
            showToast("Debug scan failed: " + error.message, "error");
        });
    }
}


// Add these new functions for face recognition

async function startFaceVerification() {
    try {
        updateMarkerUI('processing', {
            title: 'Face Verification',
            subtitle: 'Please look at the camera...'
        });

        // Open camera and capture image
        const imageData = await captureFaceImage();
        
        if (!imageData) {
            throw new Error('Could not capture image');
        }

        // Send image to server for verification
        const response = await fetch(`${API_BASE}/verify-face`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ image: imageData })
        });

        const result = await response.json();
        
        if (response.ok && result.match) {
            showToast("Face verified successfully!", "success");
            return true;
        } else {
            showToast(result.message || "Face verification failed", "error");
            return false;
        }
    } catch (error) {
        console.error("Face verification error:", error);
        showToast("Face verification failed: " + error.message, "error");
        return false;
    }
}

async function captureFaceImage() {
    return new Promise((resolve, reject) => {
        const video = document.createElement('video');
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');

        navigator.mediaDevices.getUserMedia({ video: true })
            .then(stream => {
                video.srcObject = stream;
                video.play();

                video.onloadedmetadata = () => {
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;

                    // Wait a moment for camera to focus
                    setTimeout(() => {
                        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                        const imageData = canvas.toDataURL('image/jpeg');
                        
                        // Stop the video stream
                        stream.getTracks().forEach(track => track.stop());
                        
                        resolve(imageData);
                    }, 1000);
                };
            })
            .catch(error => {
                reject(error);
            });
    });
}

// Modify the startAttendanceCheck function to include face recognition
async function startAttendanceCheck() {
    if (!currentLecture) {
        showToast("Error: No active lecture found.", "error");
        return;
    }

    console.log("Starting attendance check for lecture:", currentLecture.courseCode);
    updateMarkerUI('location-scan');

    try {
        let scanData;
        
        // Use desktop scanning if available, otherwise fall back to web API
        if (window.pywebview && window.pywebview.api) {
            scanData = await performDesktopScan();
        } else {
            // Fallback to web geolocation only
            const position = await getCurrentPosition();
            scanData = {
                location: {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude
                },
                wifiBSSID: null,
                bluetoothID: null
            };
        }

        // Update UI with scan results
        if (scanData.wifiBSSID) {
            updateVerificationStep('wifi', 'WiFi Verified!', 'success');
            showToast("WiFi network verified!", "success");
        }

        if (scanData.bluetoothID) {
            updateVerificationStep('bluetooth', 'Bluetooth Verified!', 'success');
            showToast("Teacher device detected!", "success");
        }

        // --- FACE VERIFICATION STEP ---
        updateMarkerUI('processing', {
            title: 'Face Verification',
            subtitle: 'Please look at the camera for identity verification'
        });

        const faceVerified = await startFaceVerification();
        
        if (!faceVerified) {
            throw new Error("Face verification failed");
        }

        // Send data to server for final validation and attendance marking
        const response = await fetch(`${API_BASE}/mark-attendance`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                lectureId: currentLecture.id,
                latitude: scanData.location.latitude,
                longitude: scanData.location.longitude,
                bssid: scanData.wifiBSSID,
                bluetoothDeviceId: scanData.bluetoothID,
                faceVerified: true
            })
        });

        const result = await response.json();
        console.log("Server response received:", result);

        if (response.ok) {
            updateMarkerUI('success', { 
                subtitle: result.message || "Attendance marked successfully!" 
            });
            showToast("Attendance Marked Successfully!", "success");
            
            // Refresh dashboard data to update attendance stats
            fetchDashboardData();
        } else {
            console.error("Server returned an error:", result.error);
            updateMarkerUI('initial', {
                title: 'Attendance Failed',
                subtitle: result.error || "Unknown server error",
                buttonDisabled: false
            });
            showToast(result.error || "Attendance failed", "error");
        }
    } catch (error) {
        console.error("An error occurred during the attendance check process:", error);
        updateMarkerUI('initial', {
            title: 'Check Failed',
            subtitle: error.message,
            buttonDisabled: false
        });
        showToast(error.message, "error");
    }
}