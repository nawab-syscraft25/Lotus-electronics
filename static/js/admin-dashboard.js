// Admin Dashboard JavaScript

class AdminDashboard {
    constructor() {
        this.currentPage = 1;
        this.pageSize = 20;
        this.currentSection = 'dashboard';
        
        this.init();
    }
    
    init() {
        this.setupNavigation();
        this.loadDashboardData();
        this.setupEventListeners();
    }
    
    setupNavigation() {
        document.querySelectorAll('.nav-link[data-section]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = e.target.getAttribute('data-section');
                this.showSection(section);
            });
        });
    }
    
    showSection(section) {
        // Hide all sections
        document.querySelectorAll('.content-section').forEach(sec => {
            sec.style.display = 'none';
        });
        
        // Show selected section
        document.getElementById(`${section}-section`).style.display = 'block';
        
        // Update active nav link
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        document.querySelector(`[data-section="${section}"]`).classList.add('active');
        
        this.currentSection = section;
        
        // Load section-specific data
        switch(section) {
            case 'dashboard':
                this.loadDashboardData();
                break;
            case 'users':
                this.loadUsers();
                break;
            case 'conversations':
                this.loadConversations();
                break;
            case 'logs':
                this.loadLogs();
                break;
            case 'analytics':
                this.loadAnalytics();
                break;
        }
    }
    
    setupEventListeners() {
        // Auto-refresh every 30 seconds
        setInterval(() => {
            if (this.currentSection === 'dashboard') {
                this.loadDashboardData();
            }
        }, 30000);
        
        // Log level filter
        document.getElementById('log-level-filter').addEventListener('change', () => {
            this.currentPage = 1;
            this.loadLogs();
        });
        
        // Session search
        document.getElementById('session-search').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.currentPage = 1;
                this.loadConversations();
            }
        });
    }
    
    async loadDashboardData() {
        try {
            const response = await fetch('/admin/api/stats');
            const data = await response.json();
            
            if (data.success) {
                const stats = data.stats;
                
                // Update stat cards with new metrics
                document.getElementById('total-unique-sessions').textContent = stats.total_unique_sessions;
                document.getElementById('last-7-days-sessions').textContent = stats.last_7_days_sessions;
                document.getElementById('today-sessions').textContent = stats.today_sessions;
                
                // Load recent conversations
                this.loadRecentConversations();
            }
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.showError('Failed to load dashboard data');
        }
    }
    
    async loadRecentConversations() {
        try {
            const response = await fetch('/admin/api/conversations?limit=5');
            const data = await response.json();
            
            if (data.success) {
                const container = document.getElementById('recent-conversations');
                container.innerHTML = '';
                
                data.conversations.forEach(conv => {
                    const messageClass = conv.message_type === 'human' ? 'message-human' : 'message-ai';
                    const icon = conv.message_type === 'human' ? 'fa-user' : 'fa-robot';
                    
                    const div = document.createElement('div');
                    div.className = `conversation-card p-3 mb-2 ${messageClass}`;
                    div.innerHTML = `
                        <div class="d-flex justify-content-between align-items-start">
                            <div class="flex-grow-1">
                                <div class="d-flex align-items-center mb-1">
                                    <i class="fas ${icon} me-2"></i>
                                    <strong>${conv.message_type.toUpperCase()}</strong>
                                    <small class="text-muted ms-2">${conv.session_id.substring(0, 8)}...</small>
                                </div>
                                <p class="mb-1">${this.truncateText(conv.message_content, 100)}</p>
                                <small class="text-muted">${this.formatTimestamp(conv.timestamp)}</small>
                            </div>
                        </div>
                    `;
                    container.appendChild(div);
                });
                
                if (data.conversations.length === 0) {
                    container.innerHTML = '<p class="text-muted text-center">No conversations yet</p>';
                }
            }
        } catch (error) {
            console.error('Error loading recent conversations:', error);
        }
    }
    
    // Users/Sessions functionality
    async loadUsers() {
        try {
            const startDate = document.getElementById('user-start-date').value;
            const endDate = document.getElementById('user-end-date').value;
            
            const params = new URLSearchParams();
            if (startDate) params.append('start_date', startDate);
            if (endDate) params.append('end_date', endDate);
            
            const response = await fetch(`/admin/api/users?${params}`);
            const data = await response.json();
            
            if (data.success) {
                this.displayUsers(data.users);
            } else {
                this.showError('Failed to load users: ' + data.message);
            }
        } catch (error) {
            console.error('Error loading users:', error);
            this.showError('Failed to load users');
        }
    }
    
    displayUsers(users) {
        const container = document.getElementById('users-list');
        const countElement = document.getElementById('users-count');
        
        if (!container) return;
        
        countElement.textContent = users.length;
        
        if (users.length === 0) {
            container.innerHTML = '<div class="text-center text-muted py-4">No sessions found for the selected date range</div>';
            return;
        }
        
        container.innerHTML = '';
        users.forEach(user => {
            const sessionCard = document.createElement('div');
            sessionCard.className = 'session-card p-3 session-main';
            sessionCard.onclick = () => this.viewUserConversation(user.session_id);
            
            sessionCard.innerHTML = `
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="mb-2">
                            <i class="fas fa-comments me-2"></i>
                            Session: <code>${user.session_id.substring(0, 12)}...</code>
                        </h6>
                        ${user.user_phone ? `<div class="text-muted mb-2"><i class="fas fa-phone me-2"></i>${user.user_phone}</div>` : ''}
                        <div class="session-stats text-muted">
                            <div class="session-stat">
                                <i class="fas fa-envelope"></i>
                                <span>${user.message_count} messages</span>
                            </div>
                            <div class="session-stat">
                                <i class="fas fa-clock"></i>
                                <span>First: ${this.formatTimestamp(user.first_activity)}</span>
                            </div>
                            <div class="session-stat">
                                <i class="fas fa-calendar"></i>
                                <span>Last: ${this.formatTimestamp(user.last_activity)}</span>
                            </div>
                        </div>
                    </div>
                    <div class="text-end">
                        <div class="badge  rounded-pill mb-2">
                            ${user.message_count} msgs
                        </div>
                        <div class="text-muted small">
                            Click to view chat
                        </div>
                    </div>
                </div>
            `;
            
            container.appendChild(sessionCard);
        });
    }
    
    async viewUserConversation(sessionId) {
        try {
            // Set modal session info
            document.getElementById('modal-session-id').textContent = sessionId.substring(0, 12) + '...';
            document.getElementById('session-full-id').textContent = sessionId;
            
            // Show the modal
            const modal = new bootstrap.Modal(document.getElementById('userConversationModal'));
            modal.show();
            
            // Load conversation data
            await this.loadUserConversationData(sessionId);
            
        } catch (error) {
            console.error('Error viewing user conversation:', error);
            this.showError('Failed to load conversation');
        }
    }
    
    async loadUserConversationData(sessionId, startDate = null, endDate = null) {
        try {
            const params = new URLSearchParams();
            if (startDate) params.append('start_date', startDate);
            if (endDate) params.append('end_date', endDate);
            
            const response = await fetch(`/admin/api/users/${sessionId}/conversation?${params}`);
            const data = await response.json();
            
            if (data.success) {
                this.displayUserConversation(data.conversation);
                
                // Update session info
                if (data.conversation.length > 0) {
                    const firstMessage = data.conversation[0];
                    
                    // Extract phone number from conversation messages
                    let phoneNumber = firstMessage.user_phone || 'N/A';
                    
                    // If no phone in metadata, look for phone number in messages
                    if (phoneNumber === 'N/A') {
                        phoneNumber = this.extractPhoneFromMessages(data.conversation);
                    }
                    
                    document.getElementById('session-phone').textContent = phoneNumber;
                    document.getElementById('session-message-count').textContent = data.conversation.length;
                }
            } else {
                this.showError('Failed to load conversation: ' + data.message);
            }
        } catch (error) {
            console.error('Error loading user conversation data:', error);
            this.showError('Failed to load conversation data');
        }
    }
    
    displayUserConversation(messages) {
        const container = document.getElementById('user-conversation-content');
        
        if (messages.length === 0) {
            container.innerHTML = '<div class="text-center text-muted py-4">No messages found for the selected date range</div>';
            return;
        }
        
        container.innerHTML = '';
        messages.forEach((message, index) => {
            const messageDiv = document.createElement('div');
            messageDiv.className = `chat-message ${message.message_type}`;
            
            const messageContent = message.message_type === 'ai' && message.response_metadata ? 
                this.formatAIMessage(message.response_metadata) : 
                message.message_content;
            
            // Add message number for easy reference
            const messageNumber = index + 1;
            const typeIcon = message.message_type === 'human' ? '👤' : '🤖';
            const typeLabel = message.message_type === 'human' ? 'User' : 'AI Assistant';
            
            messageDiv.innerHTML = `
                <div class="d-flex align-items-start mb-2">
                    <span class="badge text-${message.message_type === 'human' ? 'white' : 'success'} me-2">
                        ${typeIcon} ${typeLabel}
                    </span>
                    <div class="chat-timestamp ms-auto">${this.formatTimestamp(message.timestamp || message.created_at)}</div>
                </div>
                <div class="message-content">${messageContent}</div>
            `;
            
            container.appendChild(messageDiv);
        });
        
        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
    }
    
    formatAIMessage(metadata) {
        if (typeof metadata === 'string') {
            try {
                metadata = JSON.parse(metadata);
            } catch (e) {
                return metadata;
            }
        }
        
        if (metadata && metadata.answer) {
            let formatted = metadata.answer;
            
            // Add product information if available
            if (metadata.products && metadata.products.length > 0) {
                formatted += '<div class="mt-3"><div class="badge bg-info me-2">📦 Products</div>';
                formatted += '<small class="text-muted">' + metadata.products.length + ' products shown:</small>';
                formatted += '<div class="mt-2">';
                
                // Show ALL products with details
                metadata.products.forEach(product => {
                    formatted += `
                        <div class="card mt-2" style="max-width: 100%; font-size: 0.85rem;">
                            <div class="card-body p-2">
                                <div class="d-flex">
                                    <img src="${product.product_image}" alt="${product.product_name}" 
                                         style="width: 60px; height: 60px; object-fit: cover; border-radius: 4px;" class="me-2">
                                    <div class="flex-grow-1">
                                        <h6 class="card-title mb-1" style="font-size: 0.8rem;">${this.truncateText(product.product_name, 50)}</h6>
                                        <div class="text-primary fw-bold mb-1">${product.product_mrp}</div>
                                        <div class="text-muted small">
                                            ${product.features ? product.features.slice(0, 2).map(f => `<span class="badge bg-light text-dark me-1">${f}</span>`).join('') : ''}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                });
                
                formatted += '</div></div>';
            }
            
            // Add comparison information if available
            if (metadata.comparison && metadata.comparison.table && metadata.comparison.table.length > 0) {
                formatted += '<div class="mt-2"><div class="badge bg-warning me-2">📊 Comparison</div>';
                formatted += '<small class="text-muted">Product comparison table with ' + metadata.comparison.table.length + ' features</small></div>';
            }
            
            // Add store information if available
            if (metadata.stores && metadata.stores.length > 0) {
                formatted += '<div class="mt-2"><div class="badge bg-success me-2">🏪 Stores</div>';
                formatted += '<small class="text-muted">' + metadata.stores.length + ' store location(s)</small></div>';
            }
            
            // Add policy information if available
            if (metadata.policy_info && Object.keys(metadata.policy_info).length > 0) {
                formatted += '<div class="mt-2"><div class="badge bg-secondary me-2">📋 Policy</div>';
                formatted += '<small class="text-muted">Policy information provided</small></div>';
            }
            
            // Add end message if available
            if (metadata.end) {
                formatted += '<div class="mt-2 p-2 bg-light rounded"><small class="text-muted"><strong>Follow-up:</strong> ' + metadata.end + '</small></div>';
            }
            
            return formatted;
        }
        
        return JSON.stringify(metadata, null, 2);
    }

    async loadConversations(page = 1) {
        try {
            const sessionId = document.getElementById('session-search').value.trim();
            const params = new URLSearchParams({
                page: page,
                limit: this.pageSize
            });
            
            if (sessionId) {
                params.append('session_id', sessionId);
            }
            
            const response = await fetch(`/admin/api/conversations?${params}`);
            const data = await response.json();
            
            if (data.success) {
                this.renderConversationsTable(data.conversations);
                this.renderPagination('conversations', data.pagination);
                this.currentPage = page;
            }
        } catch (error) {
            console.error('Error loading conversations:', error);
            this.showError('Failed to load conversations');
        }
    }
    
    renderConversationsTable(conversations) {
        const tbody = document.getElementById('conversations-table');
        tbody.innerHTML = '';
        
        conversations.forEach(conv => {
            const typeClass = conv.message_type === 'human' ? 'text-primary' : 'text-purple';
            const typeIcon = conv.message_type === 'human' ? 'fa-user' : 'fa-robot';
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><code>${conv.session_id.substring(0, 12)}...</code></td>
                <td>
                    <span class="badge bg-${conv.message_type === 'human' ? 'primary' : 'secondary'}">
                        <i class="fas ${typeIcon} me-1"></i>
                        ${conv.message_type.toUpperCase()}
                    </span>
                </td>
                <td>${this.truncateText(conv.message_content, 80)}</td>
                <td>${conv.user_phone || '-'}</td>
                <td><small>${this.formatTimestamp(conv.timestamp)}</small></td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="dashboard.viewConversationDetails('${conv.id}')">
                        <i class="fas fa-eye"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
        
        if (conversations.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No conversations found</td></tr>';
        }
    }
    
    async loadLogs(page = 1) {
        try {
            const level = document.getElementById('log-level-filter').value;
            const params = new URLSearchParams({
                page: page,
                limit: this.pageSize
            });
            
            if (level) {
                params.append('level', level);
            }
            
            const response = await fetch(`/admin/api/logs?${params}`);
            const data = await response.json();
            
            if (data.success) {
                this.renderLogsTable(data.logs);
                this.renderPagination('logs', data.pagination);
                this.currentPage = page;
            }
        } catch (error) {
            console.error('Error loading logs:', error);
            this.showError('Failed to load logs');
        }
    }
    
    renderLogsTable(logs) {
        const tbody = document.getElementById('logs-table');
        tbody.innerHTML = '';
        
        logs.forEach(log => {
            const levelClass = this.getLogLevelClass(log.level);
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <span class="badge bg-${this.getLogLevelBadge(log.level)} ${levelClass}">
                        ${log.level}
                    </span>
                </td>
                <td><small>${log.logger_name}</small></td>
                <td>${this.truncateText(log.message, 80)}</td>
                <td>${log.session_id ? `<code>${log.session_id.substring(0, 8)}...</code>` : '-'}</td>
                <td><small>${this.formatTimestamp(log.timestamp)}</small></td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="dashboard.viewLogDetails('${log.id}')">
                        <i class="fas fa-eye"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
        
        if (logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No logs found</td></tr>';
        }
    }
    
    renderPagination(type, pagination) {
        const container = document.getElementById(`${type}-pagination`);
        container.innerHTML = '';
        
        if (pagination.total_pages <= 1) return;
        
        // Previous button
        const prevLi = document.createElement('li');
        prevLi.className = `page-item ${pagination.current_page === 1 ? 'disabled' : ''}`;
        prevLi.innerHTML = `<a class="page-link" href="#" onclick="dashboard.${type === 'conversations' ? 'loadConversations' : 'loadLogs'}(${pagination.current_page - 1})">Previous</a>`;
        container.appendChild(prevLi);
        
        // Page numbers
        for (let i = Math.max(1, pagination.current_page - 2); i <= Math.min(pagination.total_pages, pagination.current_page + 2); i++) {
            const li = document.createElement('li');
            li.className = `page-item ${i === pagination.current_page ? 'active' : ''}`;
            li.innerHTML = `<a class="page-link" href="#" onclick="dashboard.${type === 'conversations' ? 'loadConversations' : 'loadLogs'}(${i})">${i}</a>`;
            container.appendChild(li);
        }
        
        // Next button
        const nextLi = document.createElement('li');
        nextLi.className = `page-item ${pagination.current_page === pagination.total_pages ? 'disabled' : ''}`;
        nextLi.innerHTML = `<a class="page-link" href="#" onclick="dashboard.${type === 'conversations' ? 'loadConversations' : 'loadLogs'}(${pagination.current_page + 1})">Next</a>`;
        container.appendChild(nextLi);
    }
    
    async viewConversationDetails(id) {
        try {
            const response = await fetch(`/admin/api/conversations/${id}`);
            const data = await response.json();
            
            if (data.success) {
                const conv = data.conversation;
                const modalBody = document.getElementById('conversation-details');
                
                modalBody.innerHTML = `
                    <div class="row">
                        <div class="col-md-6">
                            <h6>Basic Information</h6>
                            <table class="table table-sm">
                                <tr><td><strong>Session ID:</strong></td><td><code>${conv.session_id}</code></td></tr>
                                <tr><td><strong>Type:</strong></td><td><span class="badge">${conv.message_type.toUpperCase()}</span></td></tr>
                                <tr><td><strong>Phone:</strong></td><td>${conv.user_phone || '-'}</td></tr>
                                <tr><td><strong>Timestamp:</strong></td><td>${this.formatTimestamp(conv.timestamp)}</td></tr>
                            </table>
                        </div>
                        <div class="col-md-6">
                            <h6>Message Content</h6>
                            <div class="border rounded p-3 bg-light">
                                <pre style="white-space: pre-wrap; word-wrap: break-word;">${conv.message_content}</pre>
                            </div>
                        </div>
                    </div>
                    ${conv.response_metadata ? `
                        <div class="mt-3">
                            <h6>Response Metadata</h6>
                            <div class="border rounded p-3 bg-light">
                                <pre><code>${JSON.stringify(JSON.parse(conv.response_metadata), null, 2)}</code></pre>
                            </div>
                        </div>
                    ` : ''}
                `;
                
                new bootstrap.Modal(document.getElementById('conversationModal')).show();
            }
        } catch (error) {
            console.error('Error loading conversation details:', error);
            this.showError('Failed to load conversation details');
        }
    }
    
    async viewLogDetails(id) {
        try {
            const response = await fetch(`/admin/api/logs/${id}`);
            const data = await response.json();
            
            if (data.success) {
                const log = data.log;
                const modalBody = document.getElementById('log-details');
                
                modalBody.innerHTML = `
                    <div class="row">
                        <div class="col-md-6">
                            <h6>Log Information</h6>
                            <table class="table table-sm">
                                <tr><td><strong>Level:</strong></td><td><span class="badge bg-${this.getLogLevelBadge(log.level)}">${log.level}</span></td></tr>
                                <tr><td><strong>Logger:</strong></td><td>${log.logger_name}</td></tr>
                                <tr><td><strong>Session ID:</strong></td><td>${log.session_id ? `<code>${log.session_id}</code>` : '-'}</td></tr>
                                <tr><td><strong>Timestamp:</strong></td><td>${this.formatTimestamp(log.timestamp)}</td></tr>
                            </table>
                        </div>
                        <div class="col-md-6">
                            <h6>Message</h6>
                            <div class="border rounded p-3 bg-light">
                                <pre style="white-space: pre-wrap; word-wrap: break-word;">${log.message}</pre>
                            </div>
                        </div>
                    </div>
                    ${log.error_details ? `
                        <div class="mt-3">
                            <h6>Error Details</h6>
                            <div class="border rounded p-3 bg-light">
                                <pre><code>${log.error_details}</code></pre>
                            </div>
                        </div>
                    ` : ''}
                `;
                
                new bootstrap.Modal(document.getElementById('logModal')).show();
            }
        } catch (error) {
            console.error('Error loading log details:', error);
            this.showError('Failed to load log details');
        }
    }
    
    async loadAnalytics() {
        // Placeholder for analytics charts
        console.log('Loading analytics...');
    }
    
    async exportConversations() {
        try {
            const sessionId = document.getElementById('session-search').value.trim();
            const params = new URLSearchParams();
            
            if (sessionId) {
                params.append('session_id', sessionId);
            }
            
            const response = await fetch(`/admin/api/export/conversations?${params}`);
            const blob = await response.blob();
            
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `conversations_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Error exporting conversations:', error);
            this.showError('Failed to export conversations');
        }
    }
    
    async exportLogs() {
        try {
            const level = document.getElementById('log-level-filter').value;
            const params = new URLSearchParams();
            
            if (level) {
                params.append('level', level);
            }
            
            const response = await fetch(`/admin/api/export/logs?${params}`);
            const blob = await response.blob();
            
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `logs_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Error exporting logs:', error);
            this.showError('Failed to export logs');
        }
    }
    
    // Utility functions
    truncateText(text, length) {
        if (text.length <= length) return text;
        return text.substring(0, length) + '...';
    }
    
    formatTimestamp(timestamp) {
        // Add 5.5 hours (5 hours 30 minutes) to adjust for server timezone difference
        const date = new Date(timestamp);
        const adjustedDate = new Date(date.getTime() + (5.5 * 60 * 60 * 1000)); // Add 5.5 hours in milliseconds
        return adjustedDate.toLocaleString();
    }
    
    getLogLevelClass(level) {
        const classes = {
            'INFO': 'log-level-info',
            'WARNING': 'log-level-warning',
            'ERROR': 'log-level-error',
            'CRITICAL': 'log-level-critical'
        };
        return classes[level] || '';
    }
    
    getLogLevelBadge(level) {
        const badges = {
            'INFO': 'info',
            'WARNING': 'warning',
            'ERROR': 'danger',
            'CRITICAL': 'dark'
        };
        return badges[level] || 'secondary';
    }
    
    showError(message) {
        // Create a toast notification
        const toast = document.createElement('div');
        toast.className = 'toast position-fixed top-0 end-0 m-3';
        toast.innerHTML = `
            <div class="toast-header bg-danger text-white">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong class="me-auto">Error</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">${message}</div>
        `;
        document.body.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 5000);
    }
    
    // Extract phone number from conversation messages
    extractPhoneFromMessages(messages) {
        // Look for phone number patterns in user messages
        const phoneRegex = /^[6-9]\d{9}$/; // Indian phone number pattern (10 digits starting with 6-9)
        const phoneRegexWithCode = /^(?:\+91|91)?[6-9]\d{9}$/; // With country code
        const phoneInTextRegex = /(?:\+91|91)?([6-9]\d{9})/; // Phone number within text
        
        // Check first few user messages (phone number is usually in first 2-3 messages)
        const userMessages = messages.filter(msg => 
            msg.message_type === 'human' || 
            msg.message_type === 'user' || 
            msg.type === 'human' ||
            msg.type === 'user'
        ).slice(0, 5); // Check first 5 user messages
        
        for (let message of userMessages) {
            // Handle different possible message content fields
            let text = '';
            
            if (message.message_content) {
                text = message.message_content.toString().trim();
            } else if (message.message) {
                text = message.message.toString().trim();
            } else if (message.content) {
                text = message.content.toString().trim();
            } else if (message.text) {
                text = message.text.toString().trim();
            } else {
                continue;
            }
            
            // Check if the entire message is a phone number
            if (phoneRegex.test(text)) {
                return text;
            }
            
            if (phoneRegexWithCode.test(text)) {
                const cleanedPhone = text.replace(/^(?:\+91|91)/, '');
                return cleanedPhone; // Remove country code if present
            }
            
            // Look for phone numbers within the message text
            const phoneMatch = text.match(phoneInTextRegex);
            if (phoneMatch) {
                return phoneMatch[1]; // Return the captured group (without country code)
            }
        }
        
        return 'N/A';
    }
}

// Global functions for onclick handlers
window.loadConversations = (page = 1) => dashboard.loadConversations(page);
window.loadLogs = (page = 1) => dashboard.loadLogs(page);
window.exportConversations = () => dashboard.exportConversations();
window.exportLogs = () => dashboard.exportLogs();

// Users section functions
window.filterUsers = () => dashboard.loadUsers();
window.clearUserFilters = () => {
    document.getElementById('user-start-date').value = '';
    document.getElementById('user-end-date').value = '';
    dashboard.loadUsers();
};
window.filterModalConversation = () => {
    const sessionId = document.getElementById('session-full-id').textContent;
    const startDate = document.getElementById('modal-start-date').value;
    const endDate = document.getElementById('modal-end-date').value;
    dashboard.loadUserConversationData(sessionId, startDate, endDate);
};
window.clearModalFilters = () => {
    document.getElementById('modal-start-date').value = '';
    document.getElementById('modal-end-date').value = '';
    const sessionId = document.getElementById('session-full-id').textContent;
    dashboard.loadUserConversationData(sessionId);
};
window.exportUserConversation = () => {
    const sessionId = document.getElementById('session-full-id').textContent;
    const startDate = document.getElementById('modal-start-date').value;
    const endDate = document.getElementById('modal-end-date').value;
    
    const params = new URLSearchParams();
    params.append('session_id', sessionId);
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    
    window.open(`/admin/api/export/conversations?${params}`, '_blank');
};

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.dashboard = new AdminDashboard();
});
