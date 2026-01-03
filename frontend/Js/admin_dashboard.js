// =================================================================================
// SMART ATTENDANCE: ADMIN DASHBOARD SCRIPT
// =================================================================================
let timetableHeaders = []; // To store dynamic lecture times
// API Base URL
const API_BASE = '/api/admin';

// Global variables
let allUsers = [];
let allBranches = [];
let currentLectureDay = null;
let currentLectureNumber = null;
let currentPage = 1;
const usersPerPage = 10;

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
});

function initializeDashboard() {
    loadStats();
    loadUsers();
    loadDropdownData();
    setupEventListeners();
    
    // Initialize role fields to ensure proper display
    toggleRoleFields();
    
    // Load timetable headers from localStorage if available
    const savedHeaders = localStorage.getItem('timetableHeaders');
    if (savedHeaders) {
        timetableHeaders = JSON.parse(savedHeaders);
    }
}

function setupEventListeners() {
    // Search functionality with debounce to avoid excessive API calls
    const searchInput = document.getElementById('userSearch');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(filterUsers, 300));
    }
    
    // Form submission for adding a new user
    const userForm = document.getElementById('userForm');
    if (userForm) {
        userForm.addEventListener('submit', handleAddUserSubmit);
    }
    
    // Form submission for assigning a lecture
    const lectureForm = document.getElementById('lectureForm');
    if (lectureForm) {
        lectureForm.addEventListener('submit', saveLecture);
    }
    
    // Role change listener for the add user form
    const roleSelect = document.getElementById('role');
    if (roleSelect) {
        roleSelect.addEventListener('change', toggleRoleFields);
    }
    
    // Close modal when clicking outside
    document.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal-overlay')) {
            closeModal(event.target.id);
        }
    });
}

// --- ROLE FIELDS TOGGLE FUNCTION ---
function toggleRoleFields() {
    const role = document.getElementById('role').value;
    const submitButton = document.querySelector('#addUserModal button[type="submit"]');

    // Hide all role-specific field sections first
    document.querySelectorAll('.role-fields').forEach(field => {
        field.style.display = 'none';
    });
    
    // Show the correct section and update the button text
    if (role === 'Student') {
        document.getElementById('studentFields').style.display = 'block';
        if (submitButton) {
            submitButton.textContent = 'Proceed to Face Capture'; 
        }
    } else if (role === 'Teacher') {
        document.getElementById('teacherFields').style.display = 'block';
        if (submitButton) {
            submitButton.textContent = 'Add Teacher';
        }
    } else if (role === 'Admin') {
        document.getElementById('adminFields').style.display = 'block';
        if (submitButton) {
            submitButton.textContent = 'Add Admin';
        }
    } else {
        // If no role is selected, revert the button text
        if (submitButton) {
            submitButton.textContent = 'Add User';
        }
    }
}

// --- DATA LOADING & UI UPDATES ---

// --- Dashboard Statistics ---
async function loadStats() {
    console.log("Calling /api/admin/stats ...");
    const statsGrid = document.getElementById('statsGrid');
    try {
        const response = await fetch(`${API_BASE}/stats`);
        console.log('Stats response:', response.status, response.statusText);
        
        if (response.ok) {
            const stats = await response.json();
            console.log('Stats data:', stats);
            updateStatsUI(stats);
            if (statsGrid) {
                statsGrid.querySelectorAll('.stat-card').forEach(card => card.classList.remove('loading'));
            }
        } else {
            const errorText = await response.text();
            console.error('Stats API error:', errorText);
            showNotification('Failed to load dashboard statistics', 'error');
        }
    } catch (error) {
        console.error('Error loading stats:', error);
        showNotification('Failed to load dashboard statistics', 'error');
    }
}

function updateStatsUI(stats) {
    const statsGrid = document.getElementById('statsGrid');
    if (!statsGrid) return;
    
    const userCard = statsGrid.querySelector('.stat-card:nth-child(1)');
    if (userCard) {
        userCard.querySelector('h3').textContent = stats.totalUsers || 0;
        userCard.querySelector('p:last-child').innerHTML = `<strong>${stats.studentsCount || 0}</strong> Students &nbsp; <strong>${stats.teachersCount || 0}</strong> Teachers`;
    }

    const coursesCard = statsGrid.querySelector('.stat-card:nth-child(2) h3');
    if (coursesCard) coursesCard.textContent = stats.coursesCount || 0;
    
    const liveClassesCard = statsGrid.querySelector('.stat-card:nth-child(3) h3');
    if (liveClassesCard) liveClassesCard.textContent = '0';
    
    const uptimeCard = statsGrid.querySelector('.stat-card:nth-child(4) h3');
    if (uptimeCard) uptimeCard.textContent = '99.9%';
}

// --- User Management ---
async function loadUsers() {
    console.log("Calling /api/admin/users ..."); 
    const usersLoading = document.getElementById('usersLoading');
    const userTable = document.getElementById('userTable');
    const noUsersMessage = document.getElementById('noUsersMessage');

    if (usersLoading) usersLoading.style.display = 'flex';
    if (userTable) userTable.style.display = 'none';
    if (noUsersMessage) noUsersMessage.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE}/users`);
        console.log('Users response:', response.status, response.statusText);
        
        if (response.ok) {
            const data = await response.json();
            console.log('Users data:', data);
            allUsers = data.users || []; 
            displayUsersPage(1); 
        } else {
            const errorText = await response.text();
            console.error('Users API error:', errorText);
            if (usersLoading) usersLoading.innerHTML = '<i class="fas fa-exclamation-circle"></i> Failed to load users.';
        }
    } catch (error) {
        console.error('Error loading users:', error);
        if (usersLoading) usersLoading.innerHTML = '<i class="fas fa-exclamation-circle"></i> Failed to load users.';
        showNotification('Failed to load users', 'error');
    }
}

function displayUsersPage(page, filteredUsers = null) {
    const usersToDisplay = filteredUsers !== null ? filteredUsers : allUsers;
    
    const usersLoading = document.getElementById('usersLoading');
    const userTable = document.getElementById('userTable');
    const noUsersMessage = document.getElementById('noUsersMessage');
    const tbody = userTable ? userTable.querySelector('tbody') : null;

    if (!tbody) return;
    
    if (usersLoading) usersLoading.style.display = 'none';
    
    if (usersToDisplay.length === 0) {
        if (userTable) userTable.style.display = 'none';
        if (noUsersMessage) noUsersMessage.style.display = 'block';
        updatePagination(0, 0);
        return;
    }

    if (noUsersMessage) noUsersMessage.style.display = 'none';
    if (userTable) userTable.style.display = 'table';
    
    tbody.innerHTML = '';
    const start = (page - 1) * usersPerPage;
    const end = start + usersPerPage;
    const paginatedUsers = usersToDisplay.slice(start, end);

    paginatedUsers.forEach(user => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <div class="user-info">
                    <div class="avatar" style="background-color: ${getAvatarColor(user.role)}; color: white;">
                        ${getInitials(user.name)}
                    </div>
                    <span>${user.name}</span>
                </div>
            </td>
            <td>${user.email || 'N/A'}</td>
            <td><span class="role-pill ${user.role.toLowerCase()}">${user.role}</span></td>
            <td>${getUserDetails(user)}</td>
            <td class="action-buttons">
                <a href="#" title="Edit" onclick="editUser('${user.id}')"><i class="fas fa-pencil-alt"></i></a>
                <a href="#" title="Delete" onclick="deleteUser('${user.id}')"><i class="fas fa-trash-alt"></i></a>
            </td>
        `;
        tbody.appendChild(row);
    });

    currentPage = page;
    updatePagination(usersToDisplay.length, page);
}

// --- Timetable ---
async function loadTimetable() {
    const timetableLoading = document.getElementById('timetableLoading');
    const timetableTable = document.getElementById('timetableTable');
    
    if (timetableLoading) timetableLoading.style.display = 'flex';
    if (timetableTable) timetableTable.style.display = 'none';

    const branch = document.getElementById('branchFilter');
    const year = document.getElementById('yearFilter');
    const division = document.getElementById('divisionFilter');

    if (!branch || !year || !division || !branch.value || !year.value || !division.value) {
        showNotification('Please select Branch, Year, and Division', 'warning');
        if (timetableLoading) timetableLoading.style.display = 'none';
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/timetable/${branch.value}/${year.value}/${division.value}`);
        if (timetableLoading) timetableLoading.style.display = 'none';
        
        if (response.ok) {
            const timetableData = await response.json();
            updateTimetableUI(timetableData);
            if (timetableTable) timetableTable.style.display = 'table';
        } else {
            showNotification('Failed to load timetable.', 'error');
        }
    } catch (error) {
        console.error('Error loading timetable:', error);
        showNotification('An error occurred while loading the timetable.', 'error');
    }
}

function updateTimetableUI(timetableData) {
    const timetableTable = document.getElementById('timetableTable');
    if (!timetableTable) return;
    
    const tbody = timetableTable.querySelector('tbody');
    const theadRow = timetableTable.querySelector('thead tr');
    
    if (!tbody || !theadRow) return;
    
    tbody.innerHTML = '';
    theadRow.innerHTML = '<th>Day / Time</th>'; // Reset header

    // If timetableHeaders is empty, initialize with default lectures
    if (timetableHeaders.length === 0) {
        timetableHeaders = [
            { lectureNumber: 1, startTime: "09:00", endTime: "10:00" },
            { lectureNumber: 2, startTime: "10:00", endTime: "11:00" },
            { lectureNumber: 3, startTime: "11:00", endTime: "12:00" },
            { lectureNumber: 4, startTime: "12:00", endTime: "13:00" },
            { lectureNumber: 5, startTime: "14:00", endTime: "15:00" },
        ];
    }

    // Create table headers from our dynamic array
    timetableHeaders.forEach(header => {
        const th = document.createElement('th');
        th.innerHTML = `
            <div class="time-header-content">
                <span class="lecture-title">Lecture ${header.lectureNumber}</span>
                <div class="time-inputs">
                    <input type="time" value="${header.startTime}" onchange="updateHeaderTime(${header.lectureNumber}, 'start', this.value)">
                    <span>-</span>
                    <input type="time" value="${header.endTime}" onchange="updateHeaderTime(${header.lectureNumber}, 'end', this.value)">
                </div>
            </div>
        `;
        theadRow.appendChild(th);
    });

    // Add the "+" button to add more lecture slots
    const addSlotTh = document.createElement('th');
    addSlotTh.id = 'addLectureSlot';
    addSlotTh.innerHTML = '<i class="fas fa-plus-circle"></i>';
    addSlotTh.onclick = addLectureColumn;
    theadRow.appendChild(addSlotTh);

    // Create table body rows
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    days.forEach(day => {
        const row = document.createElement('tr');
        row.innerHTML = `<td class="day-cell">${day}</td>`;
        timetableHeaders.forEach(header => {
            const cell = document.createElement('td');
            const lectureNumber = header.lectureNumber;
            const lecture = timetableData[day]?.[lectureNumber];

            // Check if the lecture is a break and apply special styling
            if (lecture && lecture.courseCode === 'BREAK') {
                cell.classList.add('break-slot');
                cell.innerHTML = '<div class="lecture-info">BREAK</div>';
                cell.dataset.timetableId = lecture.id;
                cell.dataset.lectureData = JSON.stringify(lecture);
            } 
            // Check for a regular lecture
            else if (lecture) {
                cell.innerHTML = `
                    <div class="lecture-info">
                        <strong>${lecture.courseCode}</strong>
                        <div>${lecture.teacherId}</div>
                        <em>${lecture.roomNumber}</em>
                    </div>
                `;
                // Store the unique ID for deletion/editing
                cell.dataset.timetableId = lecture.id;
                cell.dataset.lectureData = JSON.stringify(lecture);
            }
            
            // This onclick works for empty slots, breaks, and lectures
            cell.onclick = () => openLectureModal(day, lectureNumber, cell.dataset.timetableId, cell.dataset.lectureData);
            row.appendChild(cell);
        });
        tbody.appendChild(row);
    });
}

function updateHeaderTime(lectureNumber, type, value) {
    const header = timetableHeaders.find(h => h.lectureNumber === lectureNumber);
    if (header) {
        if (type === 'start') {
            // Validate that start time is before end time
            if (header.endTime && value >= header.endTime) {
                showNotification('Start time must be before end time', 'error');
                return false;
            }
            header.startTime = value;
        } else if (type === 'end') {
            // Validate that end time is after start time
            if (header.startTime && value <= header.startTime) {
                showNotification('End time must be after start time', 'error');
                return false;
            }
            header.endTime = value;
        }
        
        // Save timetable headers to localStorage for persistence
        localStorage.setItem('timetableHeaders', JSON.stringify(timetableHeaders));
        console.log('Timetable headers updated:', timetableHeaders);
        return true;
    }
    return false;
}

function addLectureColumn() {
    // Find the maximum lecture number to ensure proper sequencing
    const maxLectureNumber = timetableHeaders.length > 0 
        ? Math.max(...timetableHeaders.map(h => h.lectureNumber)) 
        : 0;
    
    const newLectureNumber = maxLectureNumber + 1;
    
    // Calculate default times based on the last lecture
    let defaultStartTime = "15:00";
    let defaultEndTime = "16:00";
    
    if (timetableHeaders.length > 0) {
        const lastLecture = timetableHeaders[timetableHeaders.length - 1];
        const lastEndTime = new Date(`2000-01-01T${lastLecture.endTime}`);
        lastEndTime.setMinutes(lastEndTime.getMinutes() + 60); // Add 1 hour
        
        defaultStartTime = lastLecture.endTime;
        defaultEndTime = `${String(lastEndTime.getHours()).padStart(2, '0')}:${String(lastEndTime.getMinutes()).padStart(2, '0')}`;
    }
    
    timetableHeaders.push({
        lectureNumber: newLectureNumber,
        startTime: defaultStartTime,
        endTime: defaultEndTime
    });
    
    // Save to localStorage
    localStorage.setItem('timetableHeaders', JSON.stringify(timetableHeaders));
    
    // Refresh the timetable view
    loadTimetable();
    
    showNotification(`Lecture slot ${newLectureNumber} added successfully`, 'success');
}

async function clearLecture() {
    const timetableId = document.body.dataset.currentTimetableId;

    if (!timetableId || timetableId === 'undefined') {
        showNotification('This slot is already empty', 'info');
        closeModal('lectureModal');
        return;
    }

    // Use a confirmation modal instead of native confirm for better UX
    const confirmed = await showConfirmationModal(
        'Clear Lecture Slot',
        'Are you sure you want to clear this lecture slot? This action cannot be undone.',
        'Clear',
        'Cancel'
    );
    
    if (!confirmed) return;

    showLoading(true);
    try {
        const response = await fetch(`${API_BASE}/timetable/${timetableId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showNotification('Lecture slot cleared successfully', 'success');
            closeModal('lectureModal');
            loadTimetable(); // Refresh the timetable view
            
            // Also clear any local data
            delete document.body.dataset.currentTimetableId;
        } else {
            const errorData = await response.json().catch(() => ({}));
            showNotification(`Failed to clear lecture slot: ${errorData.error || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        console.error('Error clearing lecture:', error);
        showNotification('Network error occurred while clearing lecture slot', 'error');
    } finally {
        showLoading(false);
    }
}

// Helper function for confirmation modal
async function showConfirmationModal(title, message, confirmText, cancelText) {
    return new Promise((resolve) => {
        // Create modal elements
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.style.display = 'flex';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>${title}</h2>
                    <button class="close-btn" onclick="this.closest('.modal-overlay').remove(); resolve(false)">×</button>
                </div>
                <div class="modal-body">
                    <p>${message}</p>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-outline" onclick="this.closest('.modal-overlay').remove(); resolve(false)">${cancelText}</button>
                    <button class="btn btn-danger" onclick="this.closest('.modal-overlay').remove(); resolve(true)">${confirmText}</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    });
}

// --- Dropdown Population ---
async function loadDropdownData() {
    try {
        const [branches, teachers, courses, rooms] = await Promise.all([
            fetch(`${API_BASE}/branches`).then(res => res.ok ? res.json() : []),
            fetch(`${API_BASE}/teachers`).then(res => res.ok ? res.json() : []),
            fetch(`${API_BASE}/courses`).then(res => res.ok ? res.json() : []),
            fetch(`${API_BASE}/rooms`).then(res => res.ok ? res.json() : [])
        ]);
        
        allBranches = branches;

        populateDropdown('classroom', rooms, 'roomNumber', 'roomNumber');
        populateDropdown('faculty', teachers, 'teacherId', 'name', 'prefix');
        populateDropdown('subject', courses, 'courseCode', 'courseName');
        populateTimetableFilters();
        populateAddUserFilters();

    } catch (error) {
        console.error('Error loading dropdown data:', error);
        showNotification('Failed to load dropdown data', 'error');
    }
}

function populateTimetableFilters() {
    const uniqueBranches = [...new Set(allBranches.map(b => b.branchName))];
    const uniqueYears = [...new Set(allBranches.map(b => b.year))].sort();
    const uniqueDivisions = [...new Set(allBranches.map(b => b.division))].sort();

    const branchFilter = document.getElementById('branchFilter');
    const yearFilter = document.getElementById('yearFilter');
    const divisionFilter = document.getElementById('divisionFilter');

    if (!branchFilter || !yearFilter || !divisionFilter) return;

    const branchNameToIdMap = allBranches.reduce((acc, branch) => {
        const baseId = branch.branchId.split('_')[0];
        if (!acc[branch.branchName]) {
            acc[branch.branchName] = baseId;
        }
        return acc;
    }, {});

    uniqueBranches.forEach(name => {
        const option = document.createElement('option');
        option.value = branchNameToIdMap[name];
        option.textContent = name;
        branchFilter.appendChild(option);
    });

    uniqueYears.forEach(year => {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = `Year ${year}`;
        yearFilter.appendChild(option);
    });

    uniqueDivisions.forEach(div => {
        const option = document.createElement('option');
        option.value = div;
        option.textContent = `Division ${div}`;
        divisionFilter.appendChild(option);
    });
}

function populateAddUserFilters() {
    const studentBranch = document.getElementById('studentBranch');
    const studentYear = document.getElementById('studentYear');
    const studentDivision = document.getElementById('studentDivision');

    if (!studentBranch || !studentYear || !studentDivision) return;

    const uniqueBranches = [...new Map(allBranches.map(item => [item['branchName'], item])).values()];
    const uniqueYears = [...new Set(allBranches.map(b => b.year))].sort();
    const uniqueDivisions = [...new Set(allBranches.map(b => b.division))].sort();

    uniqueBranches.forEach(branch => {
        const option = document.createElement('option');
        option.value = branch.branchId; 
        option.textContent = branch.branchName;
        studentBranch.appendChild(option);
    });

    uniqueYears.forEach(year => {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = `Year ${year}`;
        studentYear.appendChild(option);
    });

    uniqueDivisions.forEach(div => {
        const option = document.createElement('option');
        option.value = div;
        option.textContent = `Division ${div}`;
        studentDivision.appendChild(option);
    });
}

// =================================================================================
// --- EVENT HANDLERS & FORM SUBMISSIONS ---
// =================================================================================

async function handleAddUserSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const role = form.querySelector('#role').value;

    if (!role) {
        showNotification('Please select a role.', 'warning');
        return;
    }
    
    const userData = {
        name: form.querySelector('#fullName').value,
        email: form.querySelector('#email').value,
        phone: form.querySelector('#phone').value,
        role: role
    };

    if (role === 'Student') {
        userData.studentId = form.querySelector('#studentId').value;
        userData.branchId = form.querySelector('#studentBranch').value;
        userData.year = parseInt(form.querySelector('#studentYear').value);
        userData.division = form.querySelector('#studentDivision').value;
    } else if (role === 'Teacher') {
        userData.teacherId = form.querySelector('#teacherId').value;
        userData.bluetoothDeviceId = form.querySelector('#bluetoothId').value;
    } else if (role === 'Admin') {
        userData.adminId = form.querySelector('#adminId').value;
    }

    if (!userData.name || !userData.email || !userData.phone) {
        showNotification('Please fill in all required fields.', 'warning');
        return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(userData.email)) {
        showNotification('Please enter a valid email address.', 'warning');
        return;
    }

    try {
        showLoading(true);
        const response = await fetch(`${API_BASE}/users`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        });
        
        const result = await response.json();

        if (response.ok) {
            showNotification(`${role} details saved successfully!`, 'success');
            form.reset(); 

            if (role === 'Student') {
                const newUserId = result.userId; 
                console.log(`Student created with ID: ${newUserId}. Proceeding to face capture.`);
                
                closeModal('addUserModal');
                openModal('faceInstructionModal');
                
                // Store the ID to use when uploading the face data
                document.body.dataset.currentStudentId = newUserId;
            } else {
                closeModal('addUserModal');
                loadUsers(); 
            }
        } else {
            if (response.status === 400 && result.error.includes("already exists")) {
                showNotification(result.error, 'error');
            } else {
                showNotification(`Error: ${result.error || 'Failed to create user'}`, 'error');
            }
        }
    } catch (error) {
        console.error('Error creating user:', error);
        showNotification('Failed to create user. Please try again.', 'error');
    } finally {
        showLoading(false);
    }
}

async function saveLecture(event) {
    event.preventDefault();
    const form = event.target;
    
    const branch = document.getElementById('branchFilter');
    const year = document.getElementById('yearFilter');
    const division = document.getElementById('divisionFilter');
    
    if (!branch || !year || !division || !branch.value || !year.value || !division.value) {
        showNotification('Please select branch, year, and division from the main filters first.', 'warning');
        return;
    }
    
    const fullBranchId = allBranches.find(b => b.branchId.startsWith(branch.value) && b.year == year.value && b.division == division.value)?.branchId;
    if (!fullBranchId) {
        showNotification('Could not find a matching branch configuration.', 'error');
        return;
    }

    // Find the corresponding time for the current lecture number
    const lectureHeader = timetableHeaders.find(h => h.lectureNumber === parseInt(currentLectureNumber));

    if (!lectureHeader) {
        showNotification('Could not find time data for this lecture slot.', 'error');
        return;
    }
    
    const timetableData = {
        branchId: fullBranchId,
        year: parseInt(year.value),
        division: division.value,
        day: currentLectureDay,
        lectureNumber: parseInt(currentLectureNumber),
        startTime: lectureHeader.startTime, // <-- ADDED START TIME
        endTime: lectureHeader.endTime,     // <-- ADDED END TIME
        courseCode: form.querySelector('#subject').value,
        teacherId: form.querySelector('#faculty').value,
        roomNumber: form.querySelector('#classroom').value
    };

    try {
        showLoading(true);
        const response = await fetch(`${API_BASE}/timetable`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(timetableData)
        });
        const result = await response.json();

        if (response.ok) {
            showNotification('Lecture assigned successfully!', 'success');
            closeModal('lectureModal');
            form.reset();
            loadTimetable();
        } else {
            showNotification(`Error: ${result.error}\n${result.details ? result.details.join('\n') : ''}`, 'error');
        }
    } catch (error) {
        console.error('Error saving lecture:', error);
        showNotification('Failed to save lecture. Please try again.', 'error');
    } finally {
        showLoading(false);
    }
}

// =================================================================================
// --- MODAL & UI INTERACTION ---
// =================================================================================

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
        
        if (modalId === 'addUserModal') {
            const userForm = document.getElementById('userForm');
            if (userForm) userForm.reset();
            toggleRoleFields(); 
        }
    }
}

function openAddUserModal() {
    openModal('addUserModal');
}

function openLectureModal(day, lectureNumber, timetableId, lectureDataJSON) {
    currentLectureDay = day;
    currentLectureNumber = lectureNumber;
    document.body.dataset.currentTimetableId = timetableId;

    const form = document.getElementById('lectureForm');
    const formBody = form.querySelector('.modal-body');
    const clearBtn = document.getElementById('clearLectureBtn');
    const addBreakBtn = document.getElementById('addBreakBtn');
    const saveLectureBtn = form.querySelector('button[type="submit"]');

    form.reset();

    if (lectureDataJSON) {
        const lectureData = JSON.parse(lectureDataJSON);
        clearBtn.style.display = 'inline-flex'; // Show clear button if any data exists

        if (lectureData.courseCode === 'BREAK') {
            // It's a break, so hide the form and save/break buttons
            formBody.style.display = 'none';
            addBreakBtn.style.display = 'none';
            saveLectureBtn.style.display = 'none';
        } else {
            // It's a regular lecture, pre-fill form and show all buttons
            formBody.style.display = 'block';
            addBreakBtn.style.display = 'inline-flex';
            saveLectureBtn.style.display = 'inline-flex';
            form.querySelector('#classroom').value = lectureData.roomNumber;
            form.querySelector('#faculty').value = lectureData.teacherId;
            form.querySelector('#subject').value = lectureData.courseCode;
        }
    } else {
        // It's a completely empty slot
        formBody.style.display = 'block';
        clearBtn.style.display = 'none'; // Hide clear button
        addBreakBtn.style.display = 'inline-flex';
        saveLectureBtn.style.display = 'inline-flex';
    }

    openModal('lectureModal');
}

function proceedToFaceCapture() {
    closeModal('faceInstructionModal'); 
    openModal('faceCaptureModal');      
    startCamera();                      
}

// --- Face Capture Functions ---
async function startCamera() {
    const video = document.getElementById('video');
    if (!video) return;

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
            video: { width: 400, height: 300 } 
        });
        
        video.srcObject = stream;
        video.onloadedmetadata = () => {
            video.play();
        };

    } catch (error) {
        console.error("Error accessing camera:", error);
        showNotification("Could not access camera. Please check permissions.", 'error');
        closeFaceCaptureModal();
    }
}

async function addBreak() {
    const branch = document.getElementById('branchFilter');
    const year = document.getElementById('yearFilter');
    const division = document.getElementById('divisionFilter');
    
    if (!branch || !year || !division || !branch.value || !year.value || !division.value) {
        showNotification('Please select branch, year, and division first.', 'error');
        return;
    }
    
    const fullBranchId = allBranches.find(b => b.branchId.startsWith(branch.value) && b.year == year.value && b.division == division.value)?.branchId;
    if (!fullBranchId) {
        showNotification('Could not find a matching branch configuration.', 'error');
        return;
    }

    const timetableData = {
        branchId: fullBranchId,
        year: parseInt(year.value),
        division: division.value,
        day: currentLectureDay,
        lectureNumber: parseInt(currentLectureNumber),
        courseCode: 'BREAK'
    };

    showLoading(true);
    try {
        const response = await fetch(`${API_BASE}/timetable`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(timetableData)
        });

        if (response.ok) {
            showNotification('Break added successfully!', 'success');
            closeModal('lectureModal');
            loadTimetable();
        } else {
            const result = await response.json();
            showNotification(`Error: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('Error adding break:', error);
        showNotification('Failed to add break.', 'error');
    } finally {
        showLoading(false);
    }
}

function stopCamera() {
    const video = document.getElementById('video');
    if (video && video.srcObject) {
        const stream = video.srcObject;
        const tracks = stream.getTracks();
        tracks.forEach(track => track.stop());
        video.srcObject = null;
    }
}

function closeFaceCaptureModal() {
    stopCamera(); 
    closeModal('faceCaptureModal');
}

async function captureFace() {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    
    if (!video || !canvas) {
        showNotification('Camera elements not found', 'error');
        return;
    }
    
    const context = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    const imageDataUrl = canvas.toDataURL('image/jpeg');
    const userId = document.body.dataset.currentStudentId;
    
    if (!userId) {
        showNotification("Error: Could not find student ID", 'error');
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await fetch(`${API_BASE}/users/${userId}/register-face`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ image: imageDataUrl }),
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showNotification('Face registered successfully!', 'success');
            const capturedImage = document.getElementById('capturedImage');
            if (capturedImage) capturedImage.src = imageDataUrl;
            const captureResult = document.getElementById('captureResult');
            if (captureResult) captureResult.style.display = 'block';
            
            setTimeout(() => {
                closeFaceCaptureModal();
                loadUsers();
            }, 2500);
        } else {
            showNotification(`Error: ${result.error || 'Failed to register face.'}`, 'error');
        }
    } catch (error) {
        console.error('Error registering face:', error);
        showNotification('Network error occurred. Please try again.', 'error');
    } finally {
        showLoading(false);
    }
}

function filterUsers() {
    const searchTerm = document.getElementById('userSearch').value.toLowerCase();
    if (!searchTerm) {
        displayUsersPage(1, allUsers);
        return;
    }
    const filtered = allUsers.filter(user => 
        user.name.toLowerCase().includes(searchTerm) ||
        user.email?.toLowerCase().includes(searchTerm) ||
        getUserDetails(user).toLowerCase().includes(searchTerm)
    );
    displayUsersPage(1, filtered);
}

// =================================================================================
// --- UTILITY & HELPER FUNCTIONS ---
// =================================================================================

function populateDropdown(dropdownId, items, valueKey, textKey, prefixKey = null) {
    const dropdown = document.getElementById(dropdownId);
    if (!dropdown) return;
    
    // Clear existing options except the first one
    while (dropdown.options.length > 1) {
        dropdown.remove(1);
    }
    
    items.forEach(item => {
        const option = document.createElement('option');
        option.value = item[valueKey];
        option.textContent = (prefixKey && item[prefixKey]) 
            ? `${item[prefixKey]} ${item[textKey]}` 
            : item[textKey];
        dropdown.appendChild(option);
    });
}

function updatePagination(totalItems, currentPage) {
    const paginationContainer = document.getElementById('userPagination');
    if (!paginationContainer) return;

    paginationContainer.innerHTML = '';
    const totalPages = Math.ceil(totalItems / usersPerPage);

    if (totalPages <= 1) return;

    if (currentPage > 1) {
        const prevButton = document.createElement('button');
        prevButton.innerHTML = '&laquo;';
        prevButton.onclick = () => {
            displayUsersPage(currentPage - 1);
        };
        paginationContainer.appendChild(prevButton);
    }

    for (let i = 1; i <= totalPages; i++) {
        const pageButton = document.createElement('button');
        pageButton.textContent = i;
        pageButton.className = (i === currentPage) ? 'active' : '';
        pageButton.onclick = () => {
            displayUsersPage(i);
        };
        paginationContainer.appendChild(pageButton);
    }

    if (currentPage < totalPages) {
        const nextButton = document.createElement('button');
        nextButton.innerHTML = '&raquo;';
        nextButton.onclick = () => {
            displayUsersPage(currentPage + 1);
        };
        paginationContainer.appendChild(nextButton);
    }
}

function getAvatarColor(role) {
    const colors = { 'Admin': '#E53E3E', 'Teacher': '#4299E1', 'Student': '#38B2AC' };
    return colors[role] || '#718096';
}

function getInitials(name) {
    if (!name || typeof name !== 'string') return '??';
    return name.split(' ').map(word => word[0]).join('').toUpperCase().substring(0, 2);
}

function getUserDetails(user) {
    switch (user.role) {
        case 'Student':
            return `${user.studentId || 'N/A'} | Yr ${user.year || '?'} ${user.division || '?'}`;
        case 'Teacher':
            return user.teacherId || 'Teacher';
        case 'Admin':
            return user.adminId || 'Administrator';
        default:
            return '';
    }
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Notification system
function showNotification(message, type = 'info') {
    // Remove any existing notifications first
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(notification => notification.remove());
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas ${getNotificationIcon(type)}"></i>
            <span>${message}</span>
        </div>
        <button class="notification-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

function getNotificationIcon(type) {
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };
    return icons[type] || 'fa-info-circle';
}

// Loading indicator
function showLoading(show) {
    let overlay = document.getElementById('loadingOverlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'loadingOverlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        `;
        overlay.innerHTML = `
            <div style="background: white; padding: 20px; border-radius: 8px; display: flex; align-items: center;">
                <i class="fas fa-spinner fa-spin" style="margin-right: 10px;"></i>
                <span>Processing...</span>
            </div>
        `;
        document.body.appendChild(overlay);
    }
    
    overlay.style.display = show ? 'flex' : 'none';
}

// Placeholder functions for unimplemented features
function editUser(userId) { 
    console.log('Editing user:', userId); 
    showNotification('Edit functionality not yet implemented.', 'info'); 
}

async function deleteUser(userId) {
    if (confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
        try {
            showLoading(true);
            const response = await fetch(`${API_BASE}/users/${userId}`, { method: 'DELETE' });
            if (response.ok) {
                showNotification('User deleted successfully.', 'success');
                loadUsers(); 
            } else {
                const result = await response.json();
                showNotification(`Error: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Error deleting user:', error);
            showNotification('Failed to delete user.', 'error');
        } finally {
            showLoading(false);
        }
    }
}

function saveTimetable() { 
    showNotification('Save Timetable functionality not yet implemented.', 'info'); 
}

function resetTimetable() { 
    showNotification('Reset Timetable functionality not yet implemented.', 'info'); 
}

function scrollToTimetable() {
    const timetableSection = document.querySelector('.timetable-section');
    if (timetableSection) {
        timetableSection.scrollIntoView({ behavior: 'smooth' });
    }
}

// Add CSS for notifications
const notificationStyles = `
    .notification {
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 8px;
        color: white;
        display: flex;
        align-items: center;
        justify-content: space-between;
        min-width: 300px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    }
    
    .notification-success { background: #27ae60; }
    .notification-error { background: #e74c3c; }
    .notification-warning { background: #f39c12; }
    .notification-info { background: #3498db; }
    
    .notification-content {
        display: flex;
        align-items: center;
        flex: 1;
    }
    
    .notification-content i {
        margin-right: 10px;
    }
    
    .notification-close {
        background: none;
        border: none;
        color: white;
        cursor: pointer;
        margin-left: 15px;
        opacity: 0.7;
        transition: opacity 0.2s;
    }
    
    .notification-close:hover {
        opacity: 1;
    }
    
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
`;

// Inject notification styles
const styleSheet = document.createElement('style');
styleSheet.textContent = notificationStyles;
document.head.appendChild(styleSheet);

// Make all functions available globally
window.toggleRoleFields = toggleRoleFields;
window.openAddUserModal = openAddUserModal;
window.loadTimetable = loadTimetable;
window.openLectureModal = openLectureModal;
window.captureFace = captureFace;
window.closeFaceCaptureModal = closeFaceCaptureModal;
window.closeModal = closeModal;
window.filterUsers = filterUsers;
window.editUser = editUser;
window.deleteUser = deleteUser;
window.saveTimetable = saveTimetable;
window.resetTimetable = resetTimetable;
window.scrollToTimetable = scrollToTimetable;
window.addBreak = addBreak;
window.clearLecture = clearLecture;
window.addLectureColumn = addLectureColumn;
window.updateHeaderTime = updateHeaderTime;
window.proceedToFaceCapture = proceedToFaceCapture;