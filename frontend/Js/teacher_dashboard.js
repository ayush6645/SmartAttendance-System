document.addEventListener('DOMContentLoaded', () => {
    // --- STATE & CONFIG ---
    let liveLectureData = null;
    let weeklyTrendChart, branchCompChart;
    const POLLING_INTERVAL = 30000; // 30 seconds for live data refresh

    // --- DOM ELEMENT SELECTORS ---
    const dom = {
        loader: document.getElementById('loading-overlay'),
        userMenu: document.getElementById('userMenu'),
        userAvatar: document.getElementById('userAvatar'),
        userDropdown: document.getElementById('userDropdown'),
        headerTitle: document.getElementById('header-title'),
        navLinks: document.querySelectorAll('.nav-link'),
        views: document.querySelectorAll('.view'),
        // Dashboard View
        nextLecture: {
            title: document.getElementById('next-lecture-title'),
            details: document.getElementById('next-lecture-details'),
            countdownContainer: document.getElementById('live-lecture-countdown-container'),
            countdown: document.getElementById('live-lecture-countdown')
        },
        stats: {
            liveStudents: document.getElementById('stat-live-students'),
            atRisk: document.getElementById('stat-at-risk'),
            absent: document.getElementById('stat-absent')
        },
        liveLectureCard: document.getElementById('live-lecture-card'),
        liveLectureContainer: document.getElementById('live-lecture-container'),
        studentListFilters: document.getElementById('student-list-filters'),
        // Other Views
        timetableContainer: document.getElementById('timetable-container'),
        editTableContainer: document.getElementById('edit-table-container'),
        // Modals
        alertModal: document.getElementById('alert-modal'),
        alertModalTitle: document.getElementById('alert-modal-title'),
        alertModalMessage: document.getElementById('alert-modal-message')
    };

    // --- UTILITY FUNCTIONS ---
    const showLoader = (show) => dom.loader.classList.toggle('active', show);
    const showAlert = (message, title = "Notification") => {
        dom.alertModalTitle.textContent = title;
        dom.alertModalMessage.textContent = message;
        dom.alertModal.style.display = 'block';
    };

    const api = {
        get: async (url) => {
            const response = await fetch(url);
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.error || `HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            if (data.success === false) throw new Error(data.error || 'API request failed.');
            return data;
        }
    };

    // --- VIEW SWITCHING LOGIC ---
    dom.navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const viewName = link.dataset.view;
            if (!viewName) return;

            dom.navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            dom.views.forEach(v => v.classList.remove('active'));
            document.getElementById(`view-${viewName}`).classList.add('active');

            dom.headerTitle.textContent = link.querySelector('span').textContent;
        });
    });

    // --- RENDER FUNCTIONS ---
    const renderTimetable = (timetable, container) => {
        container.innerHTML = '';
        Object.keys(timetable).forEach(day => {
            const dayColumn = document.createElement('div');
            dayColumn.className = 'day-column';
            dayColumn.innerHTML = `<h3>${day}</h3>`;
            if (timetable[day].length > 0) {
                timetable[day].forEach(lec => {
                    dayColumn.innerHTML += `
                        <div class="lecture-card">
                            <strong>${lec.subject}</strong>
                            <div class="lecture-details">
                                <i class="fas fa-clock"></i> ${lec.startTime} - ${lec.endTime}<br>
                                <i class="fas fa-university"></i> ${lec.branchId} | Yr ${lec.year} | Div ${lec.division}
                            </div>
                        </div>`;
                });
            } else {
                 dayColumn.innerHTML += `<p class="placeholder" style="font-size:0.9rem; padding:1rem 0;">No lectures</p>`;
            }
            container.appendChild(dayColumn);
        });
    };

    const renderLiveStudentRoster = (filter = 'all') => {
        if (!liveLectureData || !liveLectureData.students) return;

        let students = liveLectureData.students;
        if (filter === 'atRisk') students = students.filter(s => s.atRisk);
        if (filter === 'absent') students = students.filter(s => s.todayStatus === 'Absent');

        if (students.length === 0) {
            dom.liveLectureContainer.innerHTML = `<p class="placeholder">No students match the filter.</p>`;
            return;
        }

        const table = `
            <table class="student-table">
                <thead><tr><th>Student ID</th><th>Name</th><th>Overall Attd.</th><th>Today's Status</th></tr></thead>
                <tbody>
                    ${students.map(s => `
                        <tr class="${s.atRisk ? 'at-risk-true' : ''}">
                            <td>${s.studentId}</td>
                            <td>${s.name}</td>
                            <td>${s.attendancePercentage}%</td>
                            <td class="status-${s.todayStatus.toLowerCase()}">${s.todayStatus}</td>
                        </tr>`).join('')}
                </tbody>
            </table>`;
        dom.liveLectureContainer.innerHTML = table;
    };
    
    const updateDashboardView = (data, fullTimetable) => {
        liveLectureData = data.liveLecture ? data : null;
        const now = new Date();
        
        if (liveLectureData) {
            const lecture = liveLectureData.liveLecture;
            dom.nextLecture.title.textContent = `${lecture.subject} (${lecture.courseCode})`;
            dom.nextLecture.details.textContent = `Room ${lecture.roomNo} | ${lecture.branchId} | Year ${lecture.year}`;
            dom.nextLecture.countdownContainer.style.display = 'block';
            startCountdown(lecture.endTime);

            dom.stats.liveStudents.textContent = liveLectureData.students.length;
            dom.stats.atRisk.textContent = liveLectureData.students.filter(s => s.atRisk).length;
            dom.stats.absent.textContent = liveLectureData.students.filter(s => s.todayStatus === 'Absent').length;
            
            dom.liveLectureCard.style.display = 'block';
            renderLiveStudentRoster();
        } else {
            // Find next lecture
            const todayStr = now.toLocaleDateString('en-US', { weekday: 'long' });
            const todayLectures = fullTimetable[todayStr] || [];
            const nextLecture = todayLectures.find(lec => {
                const [h, m] = lec.startTime.split(':');
                return (h > now.getHours() || (h == now.getHours() && m > now.getMinutes()));
            });

            if (nextLecture) {
                dom.nextLecture.title.textContent = `${nextLecture.subject} at ${nextLecture.startTime}`;
                dom.nextLecture.details.textContent = `Room ${nextLecture.roomNo} | ${nextLecture.branchId}`;
            } else {
                 dom.nextLecture.title.textContent = "No more classes today.";
                 dom.nextLecture.details.textContent = "Take a well-deserved break!";
            }
            
            dom.nextLecture.countdownContainer.style.display = 'none';
            dom.stats.liveStudents.textContent = '--';
            dom.stats.atRisk.textContent = '--';
            dom.stats.absent.textContent = '--';
            dom.liveLectureCard.style.display = 'none';
        }
    };
    
    // --- CHART RENDERING ---
    const renderChart = (canvasId, type, chartInstance, data, options) => {
        const ctx = document.getElementById(canvasId).getContext('2d');
        if (chartInstance) chartInstance.destroy();
        return new Chart(ctx, { type, data, options });
    };

    // --- EVENT LISTENERS ---
    dom.userMenu.addEventListener('click', () => dom.userDropdown.style.display = dom.userDropdown.style.display === 'block' ? 'none' : 'block');
    document.addEventListener('click', (e) => {
        if (dom.userMenu && !dom.userMenu.contains(e.target)) dom.userDropdown.style.display = 'none';
        if (e.target.matches('.close-btn, #close-alert-modal')) e.target.closest('.modal').style.display = 'none';
    });
    
    dom.studentListFilters.addEventListener('click', (e) => {
        if (e.target.matches('.filter-btn')) {
            dom.studentListFilters.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            e.target.classList.add('active');
            renderLiveStudentRoster(e.target.dataset.filter);
        }
    });

    document.getElementById('trend-division-filter').addEventListener('change', fetchAndRenderWeeklyTrend);

    // --- DATA FETCHING & INITIALIZATION ---
    async function initializeDashboard() {
        showLoader(true);
        try {
            const [filterData, timetableData, liveData, branchCompData] = await Promise.all([
                api.get('/api/teacher/filters'),
                api.get('/api/teacher/timetable'),
                api.get('/api/teacher/live-lecture'),
                api.get('/api/teacher/analytics/branch-comparison')
            ]);
            
            populateFilterDropdowns(filterData.filters);
            renderTimetable(timetableData.timetable, dom.timetableContainer);
            updateDashboardView(liveData, timetableData.timetable);

            weeklyTrendChart = renderChart('weeklyTrendChart', 'bar', weeklyTrendChart, { labels: [], datasets: [] }, { responsive: true, maintainAspectRatio: false });
            branchCompChart = renderChart('branchComparisonChart', 'pie', branchCompChart, {
                labels: Object.keys(branchCompData.branch_comparison),
                datasets: [{ data: Object.values(branchCompData.branch_comparison), backgroundColor: ['#4a69bd', '#60a3bc', '#f39c12', '#e74c3c', '#c0392b'] }]
            }, { responsive: true, maintainAspectRatio: false });

            // Set up polling for live data
            setInterval(async () => {
                const liveData = await api.get('/api/teacher/live-lecture');
                updateDashboardView(liveData, timetableData.timetable);
            }, POLLING_INTERVAL);

        } catch (error) {
            showAlert(error.message, "Dashboard Failed to Load");
        } finally {
            showLoader(false);
        }
    }
    
    function populateFilterDropdowns(filters) {
        const populate = (id, options) => {
            const select = document.getElementById(id);
            options.forEach(opt => select.innerHTML += `<option value="${opt.value}">${opt.text}</option>`);
        };
        populate('trend-branch-filter', filters.branches.map(b => ({ value: b.id, text: b.name })));
        populate('edit-branch-filter', filters.branches.map(b => ({ value: b.id, text: b.name })));
        populate('trend-year-filter', filters.years.map(y => ({ value: y, text: `Year ${y}` })));
        populate('edit-year-filter', filters.years.map(y => ({ value: y, text: `Year ${y}` })));
        populate('trend-division-filter', filters.divisions.map(d => ({ value: d, text: `Div ${d}` })));
        populate('edit-division-filter', filters.divisions.map(d => ({ value: d, text: `Div ${d}` })));
    }

    async function fetchAndRenderWeeklyTrend() {
        const branch = document.getElementById('trend-branch-filter').value;
        const year = document.getElementById('trend-year-filter').value;
        const division = document.getElementById('trend-division-filter').value;
        if (!branch || !year || !division) return;

        try {
            const params = new URLSearchParams({ branchId: branch, year, division });
            const trendData = await api.get(`/api/teacher/analytics/weekly-trend?${params}`);
            weeklyTrendChart = renderChart('weeklyTrendChart', 'bar', weeklyTrendChart, {
                labels: Object.keys(trendData.trend),
                datasets: [{ label: 'Attendance Count', data: Object.values(trendData.trend), backgroundColor: 'rgba(74, 105, 189, 0.7)' }]
            });
        } catch (error) {
            showAlert(error.message, "Could not load trend chart");
        }
    }
    
    function startCountdown(endTimeStr) {
        const [endH, endM] = endTimeStr.split(':');
        const now = new Date();
        const endTime = new Date(now.getFullYear(), now.getMonth(), now.getDate(), endH, endM);
        
        const update = () => {
            const diff = endTime - new Date();
            if (diff <= 0) {
                dom.nextLecture.countdown.textContent = "00:00";
                return;
            }
            const minutes = Math.floor((diff / 1000) / 60);
            const seconds = Math.floor((diff / 1000) % 60);
            dom.nextLecture.countdown.textContent = `${String(minutes).padStart(2,'0')}:${String(seconds).padStart(2,'0')}`;
        };
        update();
        setInterval(update, 1000);
    }

    initializeDashboard();
});

// --- ATTENDANCE MANAGER FUNCTIONS ---
function initializeAttendanceManager() {
    // Add event listeners for attendance manager
    const fetchBtn = document.getElementById('fetch-editable-attendance-btn');
    const saveBtn = document.getElementById('save-attendance-changes-btn');
    
    if (fetchBtn) {
        fetchBtn.addEventListener('click', fetchEditableAttendance);
    }
    
    if (saveBtn) {
        saveBtn.addEventListener('click', saveAttendanceChanges);
    }
    
    // Initialize date inputs with default values
    const today = new Date();
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(today.getDate() - 7);
    
    document.getElementById('edit-start-date').value = sevenDaysAgo.toISOString().split('T')[0];
    document.getElementById('edit-end-date').value = today.toISOString().split('T')[0];
}

async function fetchEditableAttendance() {
    showLoader(true);
    try {
        const branch = document.getElementById('edit-branch-filter').value;
        const year = document.getElementById('edit-year-filter').value;
        const division = document.getElementById('edit-division-filter').value;
        const startDate = document.getElementById('edit-start-date').value;
        const endDate = document.getElementById('edit-end-date').value;
        
        if (!branch || !year || !division || !startDate || !endDate) {
            showAlert("Please select all filters and date range", "Missing Information");
            return;
        }
        
        // Validate date range (max 7 days)
        const start = new Date(startDate);
        const end = new Date(endDate);
        const diffDays = Math.ceil((end - start) / (1000 * 60 * 60 * 24));
        
        if (diffDays > 7) {
            showAlert("Date range cannot exceed 7 days", "Invalid Date Range");
            return;
        }
        
        if (diffDays < 0) {
            showAlert("End date cannot be before start date", "Invalid Date Range");
            return;
        }
        
        // Build API URL with query parameters
        const params = new URLSearchParams({
            branchId: branch,
            year: year,
            division: division,
            startDate: startDate,
            endDate: endDate
        });
        
        const data = await api.get(`/api/teacher/attendance/editable?${params}`);
        renderEditableAttendanceTable(data.attendance);
        
        // Enable save button if data is loaded
        document.getElementById('save-attendance-changes-btn').disabled = false;
        
    } catch (error) {
        showAlert(error.message, "Failed to Load Attendance Data");
    } finally {
        showLoader(false);
    }
}

function renderEditableAttendanceTable(attendanceData) {
    const container = document.getElementById('edit-table-container');
    
    if (!attendanceData || attendanceData.length === 0) {
        container.innerHTML = '<p class="placeholder">No attendance records found for the selected criteria.</p>';
        return;
    }
    
    let tableHTML = `
        <table class="editable-table">
            <thead>
                <tr>
                    <th>Student ID</th>
                    <th>Name</th>
                    <th>Date</th>
                    <th>Lecture</th>
                    <th>Current Status</th>
                    <th>Change Status</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    attendanceData.forEach(record => {
        tableHTML += `
            <tr data-record-id="${record.id}">
                <td>${record.studentId}</td>
                <td>${record.studentName}</td>
                <td>${record.date}</td>
                <td>${record.lectureCode}</td>
                <td class="status-${record.status.toLowerCase()}">${record.status}</td>
                <td>
                    <select class="status-select" data-record-id="${record.id}">
                        <option value="Present" ${record.status === 'Present' ? 'selected' : ''}>Present</option>
                        <option value="Absent" ${record.status === 'Absent' ? 'selected' : ''}>Absent</option>
                        <option value="Late" ${record.status === 'Late' ? 'selected' : ''}>Late</option>
                        <option value="Excused" ${record.status === 'Excused' ? 'selected' : ''}>Excused</option>
                    </select>
                </td>
            </tr>
        `;
    });
    
    tableHTML += `
            </tbody>
        </table>
    `;
    
    container.innerHTML = tableHTML;
    
    // Add event listeners to status dropdowns
    const statusSelects = container.querySelectorAll('.status-select');
    statusSelects.forEach(select => {
        select.addEventListener('change', function() {
            const recordId = this.dataset.recordId;
            const newStatus = this.value;
            
            // Update the current status display
            const statusCell = this.closest('tr').querySelector('td:nth-child(5)');
            statusCell.textContent = newStatus;
            statusCell.className = `status-${newStatus.toLowerCase()}`;
        });
    });
}

async function saveAttendanceChanges() {
    showLoader(true);
    try {
        const changes = [];
        const statusSelects = document.querySelectorAll('.status-select');
        
        statusSelects.forEach(select => {
            const recordId = select.dataset.recordId;
            const newStatus = select.value;
            changes.push({ recordId, status: newStatus });
        });
        
        if (changes.length === 0) {
            showAlert("No changes to save", "Information");
            return;
        }
        
        const response = await fetch('/api/teacher/attendance/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ changes }),
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Failed to save changes');
        }
        
        const result = await response.json();
        showAlert(result.message || "Changes saved successfully!", "Success");
        
        // Disable save button after successful save
        document.getElementById('save-attendance-changes-btn').disabled = true;
        
    } catch (error) {
        showAlert(error.message, "Failed to Save Changes");
    } finally {
        showLoader(false);
    }
}