/**
 * M3U Processor - Authentication Module
 */

// Use relative URLs for API calls - Nginx proxies /api/ to the backend
// Only use absolute URL for external production API
const API_URL = window.location.hostname.includes('m3uprocessor.xyz')
    ? 'https://api.m3uprocessor.xyz'
    : '';  // Empty = relative URLs, works with Nginx proxy

const Auth = {
    TOKEN_KEY: 'm3u_token',
    USER_KEY: 'm3u_user',

    getToken() {
        return localStorage.getItem(this.TOKEN_KEY);
    },

    setToken(token) {
        localStorage.setItem(this.TOKEN_KEY, token);
    },

    getUser() {
        const user = localStorage.getItem(this.USER_KEY);
        return user ? JSON.parse(user) : null;
    },

    setUser(user) {
        localStorage.setItem(this.USER_KEY, JSON.stringify(user));
    },

    isLoggedIn() {
        return !!this.getToken();
    },

    isAdmin() {
        const user = this.getUser();
        return user && user.role === 'admin';
    },

    logout() {
        localStorage.removeItem(this.TOKEN_KEY);
        localStorage.removeItem(this.USER_KEY);
        window.location.href = '/login.html';
    },

    async login(email, password) {
        const response = await fetch(`${API_URL}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Login failed');
        }
        
        this.setToken(data.access_token);
        this.setUser(data.user);
        
        return data;
    },

    async register(email, username, password) {
        const response = await fetch(`${API_URL}/api/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, username, password })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Registration failed');
        }
        
        return data;
    },

    async getMe() {
        const response = await this.fetch('/api/auth/me');
        return response;
    },

    async fetch(endpoint, options = {}) {
        const token = this.getToken();
        const headers = {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` }),
            ...options.headers
        };

        const response = await fetch(`${API_URL}${endpoint}`, {
            ...options,
            headers
        });

        if (response.status === 401) {
            this.logout();
            throw new Error('Session expired');
        }

        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Request failed');
        }

        return data;
    },

    updateNavigation() {
        const user = this.getUser();
        const navUser = document.getElementById('nav-user');
        const navLinks = document.getElementById('nav-links');
        
        if (!navUser) return;

        if (user) {
            navUser.innerHTML = `
                <div class="user-badge">
                    <div class="avatar">${user.username[0].toUpperCase()}</div>
                    <span>${user.username}</span>
                    ${user.role === 'admin' ? '<span class="badge badge-info">Admin</span>' : ''}
                </div>
                <button class="btn btn-ghost btn-sm" onclick="Auth.logout()">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                        <polyline points="16 17 21 12 16 7"></polyline>
                        <line x1="21" y1="12" x2="9" y2="12"></line>
                    </svg>
                </button>
            `;
            
            if (navLinks) {
                const myPlaylistsLink = document.createElement('a');
                myPlaylistsLink.href = '/my-playlists.html';
                myPlaylistsLink.textContent = 'My Playlists';
                if (window.location.pathname.includes('my-playlists')) {
                    myPlaylistsLink.classList.add('active');
                }
                
                const boardLink = navLinks.querySelector('a[href*="board"]');
                if (boardLink && !navLinks.querySelector('a[href*="my-playlists"]')) {
                    navLinks.insertBefore(myPlaylistsLink, boardLink.nextSibling);
                }
                
                if (user.role === 'admin') {
                    const adminLink = document.createElement('a');
                    adminLink.href = '/admin.html';
                    adminLink.textContent = 'Admin';
                    if (window.location.pathname.includes('admin')) {
                        adminLink.classList.add('active');
                    }
                    if (!navLinks.querySelector('a[href*="admin"]')) {
                        navLinks.appendChild(adminLink);
                    }
                }
            }
        } else {
            navUser.innerHTML = `
                <a href="/login.html" class="btn btn-secondary btn-sm">Login</a>
                <a href="/register.html" class="btn btn-primary btn-sm">Register</a>
            `;
        }
    },

    requireAuth() {
        if (!this.isLoggedIn()) {
            window.location.href = '/login.html';
            return false;
        }
        return true;
    },

    requireAdmin() {
        if (!this.isLoggedIn()) {
            window.location.href = '/login.html';
            return false;
        }
        if (!this.isAdmin()) {
            window.location.href = '/';
            return false;
        }
        return true;
    }
};

// Toast notification system
const Toast = {
    container: null,

    init() {
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        }
    },

    show(message, type = 'info') {
        this.init();
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icons = {
            success: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`,
            error: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`,
            info: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`
        };
        
        toast.innerHTML = `
            ${icons[type] || icons.info}
            <span>${message}</span>
        `;
        
        this.container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s ease reverse forwards';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    },

    success(message) {
        this.show(message, 'success');
    },

    error(message) {
        this.show(message, 'error');
    },

    info(message) {
        this.show(message, 'info');
    }
};

// Initialize auth on page load
document.addEventListener('DOMContentLoaded', () => {
    Auth.updateNavigation();
});

// Export for use in other scripts
window.Auth = Auth;
window.Toast = Toast;
window.API_URL = API_URL;
