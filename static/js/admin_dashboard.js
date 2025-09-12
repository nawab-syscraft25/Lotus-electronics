// Admin Dashboard JavaScript

let currentSection = 'dashboard';
let currentUsersFilters = {};
let currentModalSession = null;

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    setInterval(updateStats, 30000); // Update stats every 30 seconds
});

// Initialize dashboard
function initializeDashboard() {
    setupNavigation();
    loadStats();
    loadRecentActivity();
    showSection('dashboard');
}

// Setup navigation
function setupNavigation() {
    document.querySelectorAll('[data-section]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const section = this.getAttribute('data-section');
            showSection(section);
            
            // Update active nav link
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

// Show specific section
function showSection(sectionName) {
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.style.display = 'none';
    });
    
    // Show selected section
    const targetSection = document.getElementById(sectionName + '-section');
    if (targetSection) {
        targetSection.style.display = 'block';
        currentSection = sectionName;
        
        // Load section-specific data
        switch(sectionName) {
            case 'dashboard':
                loadStats();
                loadRecentActivity();
                break;
            case 'users':
                loadUsers();
                break;
            case 'conversations':
                loadConversations();
                break;
            case 'logs':
                loadLogs();
                break;
            case 'analytics':
                loadAnalytics();
                break;
        }
    }
}

// Load dashboard stats
async function loadStats() {
    try {
        const response = await fetch('/admin/api/stats');
        const data = await response.json();
        
        if (data.success) {
            const stats = data.stats;
            document.getElementById('total-conversations').textContent = stats.total_conversations || 0;
            document.getElementById('total-sessions').textContent = stats.unique_sessions || 0;
            document.getElementById('today-conversations').textContent = stats.today_conversations || 0;
            document.getElementById('error-logs-today').textContent = stats.error_logs_today || 0;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Update stats (for periodic refresh)
function updateStats() {
    if (currentSection === 'dashboard') {
        loadStats();
    }
}

// Load recent activity
async function loadRecentActivity() {
    try {
        const response = await fetch('/admin/api/conversations?limit=5');
        const data = await response.json();
        
        if (data.success) {
            displayRecentConversations(data.conversations);
        }
    } catch (error) {
        console.error('Error loading recent activity:', error);
    }
}

// Display recent conversations
function displayRecentConversations(conversations) {
    const container = document.getElementById('recent-conversations');
    if (!container) return;
    
    if (conversations.length === 0) {
        container.innerHTML = '<p class="text-muted">No recent conversations</p>';
        return;
    }
    
    const html = conversations.map(conv => `
        <div class="conversation-card p-3 mb-2 ${conv.message_type === 'human' ? 'message-human' : 'message-ai'}">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <strong>${conv.message_type === 'human' ? 'User' : 'AI'}:</strong>
                    <span class="text-muted small">Session: ${conv.session_id.substring(0, 8)}</span>
                </div>
                <small class="text-muted">${formatTimestamp(conv.timestamp)}</small>
            </div>
            <p class="mb-0 mt-1">${truncateText(conv.message_content, 100)}</p>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

// Load users and their conversations
async function loadUsers() {
    try {
        console.log('🔧 loadUsers() called');
        const filters = currentUsersFilters;
        console.log('🔧 Current filters:', filters);
        
        const params = new URLSearchParams();
        
        if (filters.start_date) params.append('start_date', filters.start_date);
        if (filters.end_date) params.append('end_date', filters.end_date);
        
        const url = `/admin/api/users?${params}`;
        console.log('🔧 Request URL:', url);
        
        const response = await fetch(url);
        console.log('🔧 Response status:', response.status);
        
        const data = await response.json();
        console.log('🔧 Response data:', data);
        
        if (data.success) {
            console.log('🔧 Users data:', data.users);
            displayUsers(data.users);
        } else {
            console.error('🔧 API returned error:', data.message);
            showError(data.message || 'Failed to load users');
        }
    } catch (error) {
        console.error('Error loading users:', error);
        showError('Failed to load users');
    }
}

// Display users list
function displayUsers(users) {
    console.log('🔧 displayUsers() called with:', users);
    console.log('🔧 Users count:', users ? users.length : 'null/undefined');
    
    const container = document.getElementById('users-list');
    const countElement = document.getElementById('users-count');
    
    if (!container) {
        console.error('🔧 users-list element not found');
        return;
    }
    
    if (!countElement) {
        console.error('🔧 users-count element not found');
    } else {
        console.log('🔧 Setting users count to:', users.length);
        countElement.textContent = users.length;
    }
    
    if (users.length === 0) {
        console.log('🔧 No users to display, showing empty message');
        container.innerHTML = '<div class="text-center text-muted py-4">No users found for the selected date range</div>';
        return;
    }

    console.log('🔧 Generating HTML for', users.length, 'users');
    const html = users.map(user => {
        console.log('🔧 Processing user:', user);
        return `
        <div class="card mb-3">
            <div class="card-body">
                <div class="row align-items-center">
                    <div class="col-md-8">
                        <h6 class="mb-1">
                            <i class="fas fa-user me-2"></i>
                            Session: ${user.session_id}
                        </h6>
                        ${user.user_phone ? `<p class="text-muted mb-1"><i class="fas fa-phone me-2"></i>Phone: ${user.user_phone}</p>` : ''}
                        <small class="text-muted">
                            <i class="fas fa-calendar me-1"></i>
                            First Activity: ${formatTimestamp(user.first_activity)} | 
                            Last Activity: ${formatTimestamp(user.last_activity)}
                        </small>
                    </div>
                    <div class="col-md-2 text-center">
                        <div class="badge bg-primary rounded-pill">
                            ${user.message_count} messages
                        </div>
                    </div>
                    <div class="col-md-2 text-end">
                        <button class="btn btn-outline-primary btn-sm" onclick="viewUserConversation('${user.session_id}')">
                            <i class="fas fa-comments me-1"></i>View Chat
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    }).join('');
    
    console.log('🔧 Setting HTML for users-list:', html.length, 'characters');
    container.innerHTML = html;
}

// View individual user conversation
async function viewUserConversation(sessionId) {
    try {
        currentModalSession = sessionId;
        document.getElementById('modal-session-id').textContent = sessionId;
        
        // Clear previous filters
        document.getElementById('modal-start-date').value = '';
        document.getElementById('modal-end-date').value = '';
        
        await loadUserConversationContent(sessionId);
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('userConversationModal'));
        modal.show();
    } catch (error) {
        console.error('Error viewing user conversation:', error);
        showError('Failed to load user conversation');
    }
}

// Load user conversation content
async function loadUserConversationContent(sessionId, startDate = null, endDate = null) {
    try {
        const params = new URLSearchParams();
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        
        const response = await fetch(`/admin/api/users/${sessionId}/conversation?${params}`);
        const data = await response.json();
        
        if (data.success) {
            displayUserConversation(data.conversation);
        }
    } catch (error) {
        console.error('Error loading user conversation content:', error);
        showError('Failed to load conversation content');
    }
}

// Display user conversation in modal
function displayUserConversation(conversation) {
    const container = document.getElementById('user-conversation-content');
    if (!container) return;
    
    if (conversation.length === 0) {
        container.innerHTML = '<div class="text-center text-muted py-4">No messages found for the selected date range</div>';
        return;
    }
    
    const html = conversation.map(msg => `
        <div class="conversation-card p-3 mb-2 ${msg.message_type === 'human' ? 'message-human' : 'message-ai'}">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <strong><i class="fas fa-${msg.message_type === 'human' ? 'user' : 'robot'} me-2"></i>${msg.message_type === 'human' ? 'User' : 'AI Assistant'}</strong>
                </div>
                <small class="text-muted">${formatTimestamp(msg.timestamp)}</small>
            </div>
            <div class="mt-2">
                <p class="mb-0">${msg.message_content}</p>
                ${msg.response_metadata ? `
                    <div class="mt-2">
                        <button class="btn btn-sm btn-outline-secondary" onclick="showMetadata(${msg.id})" data-bs-toggle="collapse" data-bs-target="#metadata-${msg.id}">
                            <i class="fas fa-info-circle me-1"></i>Show Details
                        </button>
                        <div class="collapse mt-2" id="metadata-${msg.id}">
                            <div class="card card-body bg-light">
                                <pre class="mb-0" style="white-space: pre-wrap; font-size: 0.8em;">${JSON.stringify(msg.response_metadata, null, 2)}</pre>
                            </div>
                        </div>
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

// Filter users by date
function filterUsers() {
    console.log('🔧 filterUsers() called');
    
    const startDate = document.getElementById('user-start-date').value;
    const endDate = document.getElementById('user-end-date').value;
    
    console.log('🔧 Start date:', startDate);
    console.log('🔧 End date:', endDate);
    
    currentUsersFilters = {
        start_date: startDate || null,
        end_date: endDate || null
    };
    
    console.log('🔧 Updated filters:', currentUsersFilters);
    
    loadUsers();
}

// Clear user filters
function clearUserFilters() {
    document.getElementById('user-start-date').value = '';
    document.getElementById('user-end-date').value = '';
    currentUsersFilters = {};
    loadUsers();
}

// Filter modal conversation
function filterModalConversation() {
    const startDate = document.getElementById('modal-start-date').value;
    const endDate = document.getElementById('modal-end-date').value;
    
    if (currentModalSession) {
        loadUserConversationContent(currentModalSession, startDate, endDate);
    }
}

// Export user conversation
function exportUserConversation() {
    if (currentModalSession) {
        const startDate = document.getElementById('modal-start-date').value;
        const endDate = document.getElementById('modal-end-date').value;
        
        const params = new URLSearchParams();
        params.append('session_id', currentModalSession);
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        
        window.open(`/admin/api/export/conversations?${params}`, '_blank');
    }
}

// Load all conversations (existing function - keeping for compatibility)
async function loadConversations(page = 1) {
    // Implementation for the All Conversations section
    // This would be similar to the existing conversation loading logic
    try {
        const response = await fetch(`/admin/api/conversations?page=${page}&limit=20`);
        const data = await response.json();
        
        if (data.success) {
            // Display conversations in the all conversations section
            // Implementation details...
        }
    } catch (error) {
        console.error('Error loading conversations:', error);
    }
}

// Load logs (existing function - keeping for compatibility)
async function loadLogs(page = 1) {
    // Implementation for logs section
    try {
        const response = await fetch(`/admin/api/logs?page=${page}&limit=20`);
        const data = await response.json();
        
        if (data.success) {
            // Display logs
            // Implementation details...
        }
    } catch (error) {
        console.error('Error loading logs:', error);
    }
}

// Load analytics (placeholder)
function loadAnalytics() {
    // Implementation for analytics section
    console.log('Loading analytics...');
}

// Utility functions
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString();
}

function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function showError(message) {
    // Simple error display - could be enhanced with a proper toast/alert system
    alert('Error: ' + message);
}

function showSuccess(message) {
    // Simple success display - could be enhanced with a proper toast/alert system
    alert('Success: ' + message);
}
