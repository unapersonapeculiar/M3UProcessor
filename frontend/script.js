/**
 * M3U Processor - Main Editor Script
 */

const Editor = {
    mode: 'paste',
    rules: [],
    originalContent: '',
    processedContent: '',
    sourceUrl: '',

    init() {
        this.bindEvents();
        this.addRule();
    },

    bindEvents() {
        // Mode tabs
        document.querySelectorAll('.mode-tab').forEach(tab => {
            tab.addEventListener('click', () => this.setMode(tab.dataset.mode));
        });

        // Content input
        const contentInput = document.getElementById('content-input');
        if (contentInput) {
            contentInput.addEventListener('input', () => this.updateStats());
        }

        // URL input
        const urlInput = document.getElementById('url-input');
        const fetchBtn = document.getElementById('fetch-btn');
        if (fetchBtn) {
            fetchBtn.addEventListener('click', () => this.fetchFromUrl());
        }

        // Add rule button
        const addRuleBtn = document.getElementById('add-rule-btn');
        if (addRuleBtn) {
            addRuleBtn.addEventListener('click', () => this.addRule());
        }

        // Preview button
        const previewBtn = document.getElementById('preview-btn');
        if (previewBtn) {
            previewBtn.addEventListener('click', () => this.preview());
        }

        // Generate button
        const generateBtn = document.getElementById('generate-btn');
        if (generateBtn) {
            generateBtn.addEventListener('click', () => this.generate());
        }

        // Auto-update toggle
        const autoUpdateToggle = document.getElementById('auto-update-toggle');
        if (autoUpdateToggle) {
            autoUpdateToggle.addEventListener('change', () => this.toggleAutoUpdate());
        }

        // Interval presets
        document.querySelectorAll('.interval-preset').forEach(btn => {
            btn.addEventListener('click', () => this.selectInterval(btn));
        });

        // Custom interval input
        const customIntervalInput = document.getElementById('custom-interval');
        if (customIntervalInput) {
            customIntervalInput.addEventListener('input', () => {
                document.querySelectorAll('.interval-preset').forEach(b => b.classList.remove('active'));
            });
        }
    },

    setMode(mode) {
        this.mode = mode;
        document.querySelectorAll('.mode-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.mode === mode);
        });
        document.getElementById('paste-mode').classList.toggle('hidden', mode !== 'paste');
        document.getElementById('url-mode').classList.toggle('hidden', mode !== 'url');
        
        // Show/hide auto-update option
        const autoUpdateSection = document.getElementById('auto-update-section');
        if (autoUpdateSection) {
            autoUpdateSection.classList.toggle('hidden', mode !== 'url');
        }
    },

    addRule() {
        const ruleId = Date.now();
        this.rules.push({
            id: ruleId,
            search: '',
            replace: '',
            is_regex: false,
            case_sensitive: true
        });
        this.renderRules();
    },

    removeRule(id) {
        this.rules = this.rules.filter(r => r.id !== id);
        this.renderRules();
    },

    updateRule(id, field, value) {
        const rule = this.rules.find(r => r.id === id);
        if (rule) {
            rule[field] = value;
        }
    },

    renderRules() {
        const container = document.getElementById('rules-container');
        if (!container) return;

        container.innerHTML = this.rules.map((rule, index) => `
            <div class="rule-item" data-rule-id="${rule.id}">
                <div class="rule-header">
                    <span class="rule-number">Rule ${index + 1}</span>
                    <button class="btn btn-ghost btn-sm" onclick="Editor.removeRule(${rule.id})">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
                <div class="rule-fields">
                    <div class="form-group" style="margin-bottom: 0;">
                        <label class="form-label">Search</label>
                        <input type="text" class="form-input mono" placeholder="Text to find..."
                               value="${this.escapeHtml(rule.search)}"
                               onchange="Editor.updateRule(${rule.id}, 'search', this.value)">
                    </div>
                    <div class="form-group" style="margin-bottom: 0;">
                        <label class="form-label">Replace</label>
                        <input type="text" class="form-input mono" placeholder="Replace with..."
                               value="${this.escapeHtml(rule.replace)}"
                               onchange="Editor.updateRule(${rule.id}, 'replace', this.value)">
                    </div>
                </div>
                <div class="rule-options">
                    <label class="form-checkbox">
                        <input type="checkbox" ${rule.is_regex ? 'checked' : ''}
                               onchange="Editor.updateRule(${rule.id}, 'is_regex', this.checked)">
                        <span>Use Regex</span>
                    </label>
                    <label class="form-checkbox">
                        <input type="checkbox" ${rule.case_sensitive ? 'checked' : ''}
                               onchange="Editor.updateRule(${rule.id}, 'case_sensitive', this.checked)">
                        <span>Case Sensitive</span>
                    </label>
                </div>
            </div>
        `).join('');
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    getContent() {
        if (this.mode === 'paste') {
            return document.getElementById('content-input')?.value || '';
        }
        return this.originalContent;
    },

    async fetchFromUrl() {
        const urlInput = document.getElementById('url-input');
        const fetchBtn = document.getElementById('fetch-btn');
        const url = urlInput?.value?.trim();
        
        if (!url) {
            Toast.error('Please enter a URL');
            return;
        }

        fetchBtn.disabled = true;
        fetchBtn.innerHTML = '<span class="spinner"></span>';

        try {
            const response = await fetch(`${API_URL}/api/fetch-m3u`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Failed to fetch URL');
            }

            this.originalContent = data.content;
            this.sourceUrl = url;
            this.updateUrlStats(data.stats);
            Toast.success('Content loaded successfully');
        } catch (error) {
            Toast.error(error.message);
        } finally {
            fetchBtn.disabled = false;
            fetchBtn.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7 10 12 15 17 10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
                Fetch
            `;
        }
    },

    updateStats() {
        const content = this.getContent();
        const channels = (content.match(/#EXTINF:/gi) || []).length;
        const lines = content.split('\n').length;
        const size = new Blob([content]).size;

        document.getElementById('stat-channels').textContent = channels;
        document.getElementById('stat-lines').textContent = lines;
        document.getElementById('stat-size').textContent = this.formatSize(size);
    },

    updateUrlStats(stats) {
        document.getElementById('url-stat-channels').textContent = stats.channels;
        document.getElementById('url-stat-lines').textContent = stats.lines;
        document.getElementById('url-stat-size').textContent = this.formatSize(stats.size);
        document.getElementById('url-stats').classList.remove('hidden');
    },

    formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    },

    async preview() {
        const content = this.getContent();
        if (!content.trim()) {
            Toast.error('Please provide M3U content');
            return;
        }

        const previewBtn = document.getElementById('preview-btn');
        previewBtn.disabled = true;
        previewBtn.innerHTML = '<span class="spinner"></span> Processing...';

        try {
            const rules = this.rules.filter(r => r.search.trim());
            
            const response = await fetch(`${API_URL}/api/process`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content, rules })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Processing failed');
            }

            this.processedContent = data.full_content;
            this.showPreview(data);
        } catch (error) {
            Toast.error(error.message);
        } finally {
            previewBtn.disabled = false;
            previewBtn.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                    <circle cx="12" cy="12" r="3"></circle>
                </svg>
                Preview
            `;
        }
    },

    showPreview(data) {
        const container = document.getElementById('preview-section');
        container.classList.remove('hidden');
        
        document.getElementById('preview-channels').textContent = data.processed.channels;
        document.getElementById('preview-groups').textContent = data.processed.groups;
        document.getElementById('preview-size').textContent = this.formatSize(data.processed.size);
        
        const previewContent = document.getElementById('preview-content');
        previewContent.textContent = data.preview;
        
        if (data.full_content.length > data.preview.length) {
            previewContent.textContent += '\n\n... (content truncated for preview)';
        }

        container.scrollIntoView({ behavior: 'smooth', block: 'start' });
    },

    toggleAutoUpdate() {
        const section = document.getElementById('interval-section');
        const toggle = document.getElementById('auto-update-toggle');
        section.classList.toggle('hidden', !toggle.checked);
    },

    selectInterval(btn) {
        document.querySelectorAll('.interval-preset').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('custom-interval').value = '';
    },

    getInterval() {
        const activePreset = document.querySelector('.interval-preset.active');
        if (activePreset) {
            return parseInt(activePreset.dataset.seconds);
        }
        const custom = parseInt(document.getElementById('custom-interval')?.value);
        if (custom && custom >= 30 && custom <= 86400) {
            return custom;
        }
        return 3600;
    },

    async generate() {
        const content = this.getContent();
        if (!content.trim()) {
            Toast.error('Please provide M3U content');
            return;
        }

        const generateBtn = document.getElementById('generate-btn');
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<span class="spinner"></span> Generating...';

        try {
            const rules = this.rules.filter(r => r.search.trim());
            const name = document.getElementById('playlist-name')?.value || null;
            const showOnBoard = document.getElementById('show-on-board')?.checked || false;
            const autoUpdate = document.getElementById('auto-update-toggle')?.checked || false;
            const interval = this.getInterval();

            const payload = {
                content,
                rules,
                name,
                show_on_board: showOnBoard,
                auto_update: autoUpdate,
                auto_update_interval: interval
            };

            if (this.mode === 'url' && this.sourceUrl) {
                payload.source_url = this.sourceUrl;
            }

            const response = await fetch(`${API_URL}/api/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(Auth.getToken() && { 'Authorization': `Bearer ${Auth.getToken()}` })
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Generation failed');
            }

            this.showResult(data);
            Toast.success('Playlist generated successfully!');
        } catch (error) {
            Toast.error(error.message);
        } finally {
            generateBtn.disabled = false;
            generateBtn.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
                </svg>
                Generate Link
            `;
        }
    },

    showResult(data) {
        const modal = document.getElementById('result-modal');
        document.getElementById('result-raw-url').value = data.raw_url;
        document.getElementById('result-view-url').value = data.view_url;
        modal.classList.add('active');
    },

    copyUrl(inputId) {
        const input = document.getElementById(inputId);
        input.select();
        document.execCommand('copy');
        
        const btn = input.nextElementSibling;
        btn.classList.add('copy-success');
        btn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
        `;
        
        setTimeout(() => {
            btn.classList.remove('copy-success');
            btn.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
            `;
        }, 2000);
        
        Toast.success('Copied to clipboard!');
    },

    closeModal() {
        document.getElementById('result-modal').classList.remove('active');
    }
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    Editor.init();
});

// Close modal on escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        Editor.closeModal();
    }
});

// Close modal on overlay click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        Editor.closeModal();
    }
});

window.Editor = Editor;
