document.addEventListener('DOMContentLoaded', () => {
    // Set the first tab as active on page load
    showTab('admin-settings');

    // --- MOCK FUNCTIONALITY FOR DEMO ---
    const findStudentsBtn = document.getElementById('find-students-btn');
    if (findStudentsBtn) {
        findStudentsBtn.addEventListener('click', () => {
            // In a real app, you'd fetch data here
            document.getElementById('student-list-container').style.display = 'block';
        });
    }

    const manageStudentBtn = document.querySelector('#student-list-container .btn');
    if (manageStudentBtn) {
        manageStudentBtn.addEventListener('click', () => {
            document.getElementById('student-manage-panel').style.display = 'block';
        });
    }

    const searchTeacherInput = document.getElementById('teacher-search');
    if(searchTeacherInput) {
        searchTeacherInput.addEventListener('keyup', (e) => {
            if (e.target.value.length > 2) { // Show details after typing a few characters
                 document.getElementById('teacher-details-container').style.display = 'block';
            } else {
                 document.getElementById('teacher-details-container').style.display = 'none';
            }
        });
    }
});

/**
 * Shows a specific tab and hides others.
 * @param {string} tabId The ID of the tab content to show.
 */
function showTab(tabId) {
    // Hide all tab content
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => {
        content.classList.remove('active');
    });

    // Deactivate all tab links
    const tabLinks = document.querySelectorAll('.tab-link');
    tabLinks.forEach(link => {
        link.classList.remove('active');
    });

    // Show the selected tab content
    const selectedTab = document.getElementById(tabId);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }

    // Activate the selected tab link
    const selectedLink = document.querySelector(`.tab-link[onclick="showTab('${tabId}')"]`);
    if (selectedLink) {
        selectedLink.classList.add('active');
    }
}