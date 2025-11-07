// Secret Vault Dashboard JavaScript

// Global variables
let credentials = [];
let categories = [];
let currentCredentialId = null;
let deleteCredentialId = null;

// API Configuration - use the same origin the page was served from
const API_BASE_URL = window.location.origin;

// Get stored credentials
function getAuthCredentials() {
    const stored = localStorage.getItem('accessToken');
    if (!stored) {
        // Redirect to login if no credentials
        window.location.href = '/login';
        return null;
    }
    return stored;
}

// Check authentication on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, checking authentication...');
    
    if (!localStorage.getItem('accessToken')) {
        console.log('No access token found, redirecting to login');
        window.location.href = '/login';
        return;
    }
    
    console.log('Access token found, initializing app...');
    
    // Set current user
    const userInfo = localStorage.getItem('userInfo');
    if (userInfo) {
        const user = JSON.parse(userInfo);
        document.getElementById('currentUser').textContent = user.username || user.email || 'User';
    } else {
        document.getElementById('currentUser').textContent = 'User';
    }
    
    initializeApp();
});

// Initialize the application
async function initializeApp() {
    try {
        showLoading();
        
        // Initialize Feather icons
        feather.replace();
        
        // Load initial data
        await Promise.all([
            loadCredentials(),
            loadAuditLogs(),
            updateVaultStatusBadge()
        ]);
        
        // Set up event listeners
        setupEventListeners();
        
        // Update dashboard stats
        updateDashboardStats();
        
        hideLoading();
    } catch (error) {
        console.error('Failed to initialize app:', error);
        showToast('Failed to initialize application', 'error');
        hideLoading();
    }
}
async function updateVaultStatusBadge() {
    try {
        // Use public health endpoint (no admin required)
        const response = await fetch(`${API_BASE_URL}/system/health`);
        if (!response.ok) {
            throw new Error('Health request failed');
        }
        const data = await response.json();
        const badge = document.getElementById('vaultStatusBadge');
        if (!badge) return;
        const v = data.vault || {};
        const enabled = !!v.enabled;
        
        if (!enabled) {
            badge.textContent = 'Vault: Disabled';
            badge.className = 'badge bg-secondary';
            return;
        }
        
        // Check for built-in Vault API
        if (v.type === 'built-in' || v.status === 'available') {
            badge.textContent = 'Vault: Available';
            const mounts = v.mounts ? v.mounts.join(', ') : 'secret/';
            badge.title = `Built-in Vault API | Mounts: ${mounts}`;
            badge.className = 'badge bg-success';
            return;
        }
        
        // Legacy external Vault check
        if (v.error) {
            badge.textContent = 'Vault: Error';
            badge.title = v.error;
            badge.className = 'badge bg-danger';
            return;
        }
        
        badge.textContent = 'Vault: Healthy';
        badge.title = `Addr: ${v.addr || 'n/a'} | Mount: ${v.kv_mount || 'n/a'}`;
        badge.className = 'badge bg-success';
    } catch (e) {
        const badge = document.getElementById('vaultStatusBadge');
        if (!badge) return;
        badge.textContent = 'Vault: Unknown';
        badge.className = 'badge bg-warning';
    }
}

function setupEventListeners() {
    // Search functionality
    document.getElementById('searchInput').addEventListener('input', debounce(filterCredentials, 300));
    
    // Filter functionality
    document.getElementById('categoryFilter').addEventListener('change', filterCredentials);
    document.getElementById('statusFilter').addEventListener('change', filterCredentials);
    
    // Form submission
    document.getElementById('credentialForm').addEventListener('submit', function(e) {
        e.preventDefault();
        saveCredential();
    });
}

// API Functions
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const authCredentials = getAuthCredentials();
    if (!authCredentials) return;
    
    const defaultOptions = {
        headers: {
            'Authorization': `Bearer ${authCredentials}`,
            'Content-Type': 'application/json',
        },
    };
    
    const finalOptions = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(url, finalOptions);
        
        if (response.status === 401) {
            // Token is invalid or expired, redirect to login
            console.log('Authentication failed, redirecting to login');
            localStorage.removeItem('accessToken');
            localStorage.removeItem('userInfo');
            localStorage.removeItem('refreshToken');
            window.location.href = '/login';
            return;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

async function loadCredentials() {
    try {
        const data = await apiRequest('/credentials');
        credentials = data;
        renderCredentialsTable();
        updateCategories();
    } catch (error) {
        console.error('Failed to load credentials:', error);
        showToast('Failed to load credentials', 'error');
    }
}

async function loadAuditLogs() {
    try {
        const data = await apiRequest('/audit');
        // Store audit logs for later use
        window.auditLogs = data;
    } catch (error) {
        console.error('Failed to load audit logs:', error);
    }
}

async function createCredential(credentialData) {
    try {
        const data = await apiRequest('/credentials', {
            method: 'POST',
            body: JSON.stringify(credentialData)
        });
        return data;
    } catch (error) {
        console.error('Failed to create credential:', error);
        throw error;
    }
}

async function updateCredential(id, credentialData) {
    try {
        const data = await apiRequest(`/credentials/${id}`, {
            method: 'PUT',
            body: JSON.stringify(credentialData)
        });
        return data;
    } catch (error) {
        console.error('Failed to update credential:', error);
        throw error;
    }
}

async function deleteCredential(id) {
    try {
        await apiRequest(`/credentials/${id}`, {
            method: 'DELETE'
        });
        return true;
    } catch (error) {
        console.error('Failed to delete credential:', error);
        throw error;
    }
}

// UI Functions
function renderCredentialsTable() {
    const tbody = document.getElementById('credentialsTableBody');
    const noCredentials = document.getElementById('noCredentials');
    
    if (credentials.length === 0) {
        tbody.innerHTML = '';
        noCredentials.style.display = 'block';
        return;
    }
    
    noCredentials.style.display = 'none';
    
    tbody.innerHTML = credentials.map(credential => `
        <tr class="fade-in">
            <td>
                <strong>${escapeHtml(credential.title)}</strong>
                ${credential.url ? `<br><small class="text-muted">${escapeHtml(credential.url)}</small>` : ''}
            </td>
            <td>
                <div class="d-flex align-items-center">
                    <span class="me-2">${escapeHtml(credential.username)}</span>
                    <button class="btn btn-sm btn-outline-secondary copy-btn" onclick="copyToClipboard('${escapeHtml(credential.username)}')" title="Copy username">
                        <i data-feather="copy"></i>
                    </button>
                </div>
            </td>
            <td>
                <div class="d-flex align-items-center">
                    <span class="password-field me-2">••••••••</span>
                    <button class="btn btn-sm btn-outline-secondary copy-btn" onclick="copyToClipboard('${credential.password}')" title="Copy password">
                        <i data-feather="copy"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="togglePasswordVisibility(this, '${credential.password}')" title="Show/hide password">
                        <i data-feather="eye"></i>
                    </button>
                </div>
            </td>
            <td>
                ${credential.category ? `<span class="category-tag">${escapeHtml(credential.category)}</span>` : '<span class="text-muted">-</span>'}
            </td>
            <td>
                <span class="badge ${credential.is_active ? 'badge-active' : 'badge-inactive'}">
                    ${credential.is_active ? 'Active' : 'Inactive'}
                </span>
            </td>
            <td>
                ${formatExpirationDate(credential.expires_at)}
            </td>
            <td>
                <div class="btn-group" role="group">
                    <button class="btn btn-sm btn-outline-primary btn-action" onclick="editCredential(${credential.id})" title="Edit">
                        <i data-feather="edit-2"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger btn-action" onclick="showDeleteModal(${credential.id}, '${escapeHtml(credential.title)}')" title="Delete">
                        <i data-feather="trash-2"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-info btn-action" onclick="viewCredentialDetails(${credential.id})" title="View Details">
                        <i data-feather="eye"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
    
    feather.replace();
}

function updateDashboardStats() {
    const total = credentials.length;
    const active = credentials.filter(c => c.is_active).length;
    const expiring = credentials.filter(c => {
        if (!c.expires_at) return false;
        const expiryDate = new Date(c.expires_at);
        const now = new Date();
        const daysUntilExpiry = (expiryDate - now) / (1000 * 60 * 60 * 24);
        return daysUntilExpiry <= 30 && daysUntilExpiry > 0;
    }).length;
    const uniqueCategories = new Set(credentials.map(c => c.category).filter(Boolean)).size;
    
    document.getElementById('totalCredentials').textContent = total;
    document.getElementById('activeCredentials').textContent = active;
    document.getElementById('expiringCredentials').textContent = expiring;
    document.getElementById('totalCategories').textContent = uniqueCategories;
}

function updateCategories() {
    const categories = [...new Set(credentials.map(c => c.category).filter(Boolean))];
    const categoryFilter = document.getElementById('categoryFilter');
    const categoryList = document.getElementById('categoryList');
    
    // Update filter dropdown
    categoryFilter.innerHTML = '<option value="">All Categories</option>' +
        categories.map(cat => `<option value="${escapeHtml(cat)}">${escapeHtml(cat)}</option>`).join('');
    
    // Update datalist for suggestions
    categoryList.innerHTML = categories.map(cat => `<option value="${escapeHtml(cat)}">`).join('');
}

function filterCredentials() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const categoryFilter = document.getElementById('categoryFilter').value;
    const statusFilter = document.getElementById('statusFilter').value;
    
    const filteredCredentials = credentials.filter(credential => {
        const matchesSearch = !searchTerm || 
            credential.title.toLowerCase().includes(searchTerm) ||
            credential.username.toLowerCase().includes(searchTerm) ||
            (credential.category && credential.category.toLowerCase().includes(searchTerm));
        
        const matchesCategory = !categoryFilter || credential.category === categoryFilter;
        
        const matchesStatus = !statusFilter || 
            (statusFilter === 'active' && credential.is_active) ||
            (statusFilter === 'inactive' && !credential.is_active);
        
        return matchesSearch && matchesCategory && matchesStatus;
    });
    
    renderFilteredCredentials(filteredCredentials);
}

function renderFilteredCredentials(filteredCredentials) {
    const tbody = document.getElementById('credentialsTableBody');
    const noCredentials = document.getElementById('noCredentials');
    
    if (filteredCredentials.length === 0) {
        tbody.innerHTML = '';
        noCredentials.style.display = 'block';
        noCredentials.innerHTML = `
            <i data-feather="search" class="text-muted" style="width: 48px; height: 48px;"></i>
            <p class="text-muted mt-2">No credentials match your search criteria.</p>
        `;
        feather.replace();
        return;
    }
    
    noCredentials.style.display = 'none';
    
    tbody.innerHTML = filteredCredentials.map(credential => `
        <tr class="fade-in">
            <td>
                <strong>${escapeHtml(credential.title)}</strong>
                ${credential.url ? `<br><small class="text-muted">${escapeHtml(credential.url)}</small>` : ''}
            </td>
            <td>
                <div class="d-flex align-items-center">
                    <span class="me-2">${escapeHtml(credential.username)}</span>
                    <button class="btn btn-sm btn-outline-secondary copy-btn" onclick="copyToClipboard('${escapeHtml(credential.username)}')" title="Copy username">
                        <i data-feather="copy"></i>
                    </button>
                </div>
            </td>
            <td>
                <div class="d-flex align-items-center">
                    <span class="password-field me-2">••••••••</span>
                    <button class="btn btn-sm btn-outline-secondary copy-btn" onclick="copyToClipboard('${credential.password}')" title="Copy password">
                        <i data-feather="copy"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="togglePasswordVisibility(this, '${credential.password}')" title="Show/hide password">
                        <i data-feather="eye"></i>
                    </button>
                </div>
            </td>
            <td>
                ${credential.category ? `<span class="category-tag">${escapeHtml(credential.category)}</span>` : '<span class="text-muted">-</span>'}
            </td>
            <td>
                <span class="badge ${credential.is_active ? 'badge-active' : 'badge-inactive'}">
                    ${credential.is_active ? 'Active' : 'Inactive'}
                </span>
            </td>
            <td>
                ${formatExpirationDate(credential.expires_at)}
            </td>
            <td>
                <div class="btn-group" role="group">
                    <button class="btn btn-sm btn-outline-primary btn-action" onclick="editCredential(${credential.id})" title="Edit">
                        <i data-feather="edit-2"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger btn-action" onclick="showDeleteModal(${credential.id}, '${escapeHtml(credential.title)}')" title="Delete">
                        <i data-feather="trash-2"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-info btn-action" onclick="viewCredentialDetails(${credential.id})" title="View Details">
                        <i data-feather="eye"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
    
    feather.replace();
}

// Modal Functions
function showAddCredentialModal() {
    currentCredentialId = null;
    document.getElementById('modalTitle').textContent = 'Add New Credential';
    document.getElementById('credentialForm').reset();
    document.getElementById('credentialId').value = '';
    
    const modal = new bootstrap.Modal(document.getElementById('credentialModal'));
    modal.show();
}

function editCredential(id) {
    const credential = credentials.find(c => c.id === id);
    if (!credential) return;
    
    currentCredentialId = id;
    document.getElementById('modalTitle').textContent = 'Edit Credential';
    document.getElementById('credentialId').value = id;
    document.getElementById('title').value = credential.title;
    document.getElementById('username').value = credential.username;
    document.getElementById('password').value = credential.password;
    document.getElementById('url').value = credential.url || '';
    document.getElementById('category').value = credential.category || '';
    document.getElementById('notes').value = credential.notes || '';
    document.getElementById('isActive').checked = credential.is_active;
    
    if (credential.expires_at) {
        const date = new Date(credential.expires_at);
        const localDateTime = new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
        document.getElementById('expiresAt').value = localDateTime;
    } else {
        document.getElementById('expiresAt').value = '';
    }
    
    const modal = new bootstrap.Modal(document.getElementById('credentialModal'));
    modal.show();
}

async function saveCredential() {
    try {
        showLoading();
        
        const formData = {
            title: document.getElementById('title').value,
            username: document.getElementById('username').value,
            password: document.getElementById('password').value,
            url: document.getElementById('url').value || null,
            category: document.getElementById('category').value || null,
            notes: document.getElementById('notes').value || null,
            is_active: document.getElementById('isActive').checked,
            expires_at: document.getElementById('expiresAt').value || null
        };
        
        let result;
        if (currentCredentialId) {
            result = await updateCredential(currentCredentialId, formData);
            showToast('Credential updated successfully', 'success');
        } else {
            result = await createCredential(formData);
            showToast('Credential created successfully', 'success');
        }
        
        // Reload data
        await loadCredentials();
        updateDashboardStats();
        
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('credentialModal'));
        modal.hide();
        
        hideLoading();
    } catch (error) {
        console.error('Failed to save credential:', error);
        showToast('Failed to save credential', 'error');
        hideLoading();
    }
}

function showDeleteModal(id, title) {
    deleteCredentialId = id;
    document.getElementById('deleteCredentialTitle').textContent = title;
    
    const modal = new bootstrap.Modal(document.getElementById('deleteModal'));
    modal.show();
}

async function confirmDelete() {
    if (!deleteCredentialId) return;
    
    try {
        showLoading();
        
        await deleteCredential(deleteCredentialId);
        showToast('Credential deleted successfully', 'success');
        
        // Reload data
        await loadCredentials();
        updateDashboardStats();
        
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('deleteModal'));
        modal.hide();
        
        deleteCredentialId = null;
        hideLoading();
    } catch (error) {
        console.error('Failed to delete credential:', error);
        showToast('Failed to delete credential', 'error');
        hideLoading();
    }
}

function viewCredentialDetails(id) {
    const credential = credentials.find(c => c.id === id);
    if (!credential) return;
    
    // For now, just show an alert with details
    // In a real application, you might want to show a detailed modal
    const details = `
Title: ${credential.title}
Username: ${credential.username}
Password: ${credential.password}
URL: ${credential.url || 'N/A'}
Category: ${credential.category || 'N/A'}
Notes: ${credential.notes || 'N/A'}
Status: ${credential.is_active ? 'Active' : 'Inactive'}
Created: ${new Date(credential.created_at).toLocaleString()}
${credential.updated_at ? `Updated: ${new Date(credential.updated_at).toLocaleString()}` : ''}
${credential.expires_at ? `Expires: ${new Date(credential.expires_at).toLocaleString()}` : ''}
    `;
    
    alert(details);
}

// Utility Functions
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard', 'success');
    }).catch(() => {
        showToast('Failed to copy to clipboard', 'error');
    });
}

function togglePasswordVisibility(button, password) {
    const icon = button.querySelector('i');
    const passwordField = button.parentElement.querySelector('.password-field');
    
    if (passwordField.textContent === '••••••••') {
        passwordField.textContent = password;
        icon.setAttribute('data-feather', 'eye-off');
    } else {
        passwordField.textContent = '••••••••';
        icon.setAttribute('data-feather', 'eye');
    }
    
    feather.replace();
}

function togglePassword() {
    const passwordInput = document.getElementById('password');
    const icon = document.getElementById('passwordToggleIcon');
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        icon.setAttribute('data-feather', 'eye-off');
    } else {
        passwordInput.type = 'password';
        icon.setAttribute('data-feather', 'eye');
    }
    
    feather.replace();
}

function generatePassword() {
    const length = 16;
    const charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*';
    let password = '';
    
    for (let i = 0; i < length; i++) {
        password += charset.charAt(Math.floor(Math.random() * charset.length));
    }
    
    document.getElementById('password').value = password;
}

function formatExpirationDate(dateString) {
    if (!dateString) return '<span class="text-muted">-</span>';
    
    const date = new Date(dateString);
    const now = new Date();
    const daysUntilExpiry = (date - now) / (1000 * 60 * 60 * 24);
    
    let className = '';
    if (daysUntilExpiry < 0) {
        className = 'expiration-danger';
    } else if (daysUntilExpiry <= 30) {
        className = 'expiration-warning';
    }
    
    return `<span class="${className}">${date.toLocaleDateString()}</span>`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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

function showLoading() {
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.innerHTML = '<div class="loading-spinner"></div>';
    document.body.appendChild(overlay);
}

function hideLoading() {
    const overlay = document.querySelector('.loading-overlay');
    if (overlay) {
        overlay.remove();
    }
}

function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }
    
    const toastId = 'toast-' + Date.now();
    const bgClass = type === 'success' ? 'bg-success' : type === 'error' ? 'bg-danger' : 'bg-info';
    
    const toastHtml = `
        <div id="${toastId}" class="toast" role="alert">
            <div class="toast-header ${bgClass} text-white">
                <strong class="me-auto">Secret Vault</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${escapeHtml(message)}
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (toastElement.parentNode) {
            toastElement.remove();
        }
    }, 5000);
}

function logout() {
    console.log('Logout function called');
    
    // Clear all storage immediately
    localStorage.clear();
    sessionStorage.clear();
    
    // Redirect to logout page which will handle the redirect
    window.location.href = '/logout';
}

// Force logout function - bypasses all checks and directly clears and redirects
function forceLogout() {
    // Clear all storage immediately
    localStorage.clear();
    sessionStorage.clear();
    
    // Force immediate redirect with multiple methods
    try {
        window.location.replace('/login');
    } catch (e) {
        window.location.href = '/login';
    }
    
    // Final fallback - force reload and redirect
    setTimeout(() => {
        if (window.location.pathname !== '/login') {
            window.location.reload();
        }
    }, 100);
}

// Test logout function - for debugging
function testLogout() {
    alert('Testing logout...\n\nCurrent tokens:\n' + 
          'accessToken: ' + (localStorage.getItem('accessToken') ? 'EXISTS' : 'NOT FOUND') + '\n' +
          'userInfo: ' + (localStorage.getItem('userInfo') ? 'EXISTS' : 'NOT FOUND') + '\n\n' +
          'Click OK to proceed with logout');
    
    // Clear everything
    localStorage.clear();
    sessionStorage.clear();
    
    // Force redirect
    window.location.replace('/login');
}

// Show audit logs
function showAuditLogs() {
    const auditLogs = window.auditLogs || [];
    const tbody = document.getElementById('auditTableBody');
    
    tbody.innerHTML = auditLogs.map(log => `
        <tr>
            <td>${new Date(log.timestamp).toLocaleString()}</td>
            <td>${escapeHtml(log.user)}</td>
            <td><span class="badge bg-secondary">${escapeHtml(log.action)}</span></td>
            <td>${escapeHtml(log.details || '-')}</td>
        </tr>
    `).join('');
    
    const modal = new bootstrap.Modal(document.getElementById('auditModal'));
    modal.show();
}
