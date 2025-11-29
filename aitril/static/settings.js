// AiTril Settings Management

class SettingsManager {
    constructor(app) {
        this.app = app;
        this.settings = null;
        this.currentTab = 'providers';
        this.isOpen = false;
    }

    async load() {
        try {
            const response = await fetch('/api/settings');
            this.settings = await response.json();
            return this.settings;
        } catch (error) {
            console.error('Failed to load settings:', error);
            return null;
        }
    }

    async saveProvider(providerId, config) {
        try {
            const response = await fetch(`/api/settings/providers/${providerId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            const result = await response.json();
            if (result.status === 'success') {
                await this.load();
                return true;
            }
            return false;
        } catch (error) {
            console.error('Failed to save provider:', error);
            return false;
        }
    }

    async saveDeploymentTarget(targetId, config) {
        try {
            const response = await fetch(`/api/settings/deployments/${targetId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            const result = await response.json();
            if (result.status === 'success') {
                await this.load();
                return true;
            }
            return false;
        } catch (error) {
            console.error('Failed to save deployment target:', error);
            return false;
        }
    }

    open() {
        this.isOpen = true;
        this.render();
    }

    close() {
        this.isOpen = false;
        const modal = document.getElementById('settings-modal');
        if (modal) {
            modal.remove();
        }
    }

    switchTab(tabName) {
        this.currentTab = tabName;
        this.renderContent();
    }

    render() {
        if (!this.isOpen) return;

        // Remove existing modal if present
        const existing = document.getElementById('settings-modal');
        if (existing) {
            existing.remove();
        }

        const modal = document.createElement('div');
        modal.id = 'settings-modal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content settings-panel">
                <div class="modal-header">
                    <h2>⚙️ Settings</h2>
                    <button class="close-btn" onclick="window.app.settings.close()">&times;</button>
                </div>
                <div class="settings-tabs">
                    <button class="tab-btn ${this.currentTab === 'providers' ? 'active' : ''}"
                            onclick="window.app.settings.switchTab('providers')">
                        🤖 LLM Providers
                    </button>
                    <button class="tab-btn ${this.currentTab === 'deployments' ? 'active' : ''}"
                            onclick="window.app.settings.switchTab('deployments')">
                        🚀 Deployment Targets
                    </button>
                    <button class="tab-btn ${this.currentTab === 'general' ? 'active' : ''}"
                            onclick="window.app.settings.switchTab('general')">
                        ⚡ General
                    </button>
                </div>
                <div id="settings-content" class="settings-content">
                    <!-- Content will be rendered here -->
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        this.renderContent();
    }

    renderContent() {
        const content = document.getElementById('settings-content');
        if (!content) return;

        if (this.currentTab === 'providers') {
            content.innerHTML = this.renderProvidersTab();
        } else if (this.currentTab === 'deployments') {
            content.innerHTML = this.renderDeploymentsTab();
        } else if (this.currentTab === 'general') {
            content.innerHTML = this.renderGeneralTab();
        }

        // Update tab active states
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`.tab-btn[onclick*="${this.currentTab}"]`)?.classList.add('active');
    }

    renderProvidersTab() {
        if (!this.settings || !this.settings.llm_providers) {
            return '<p>Loading providers...</p>';
        }

        const providers = this.settings.llm_providers;
        let html = '<div class="providers-list">';

        for (const [id, config] of Object.entries(providers)) {
            html += `
                <div class="provider-card">
                    <div class="provider-header">
                        <h3>${config.name}</h3>
                        <label class="toggle">
                            <input type="checkbox"
                                   ${config.enabled ? 'checked' : ''}
                                   onchange="window.app.settings.toggleProvider('${id}', this.checked)">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                    <div class="provider-details">
                        <div class="form-group">
                            <label>Model</label>
                            <input type="text"
                                   id="model-${id}"
                                   value="${config.model || ''}"
                                   placeholder="e.g., gpt-4o">
                        </div>
                        <div class="form-group">
                            <label>API Key Environment Variable</label>
                            <input type="text"
                                   value="${config.api_key_env || ''}"
                                   readonly
                                   placeholder="Set via environment">
                        </div>
                        ${config.base_url !== null ? `
                        <div class="form-group">
                            <label>Base URL (Optional)</label>
                            <input type="text"
                                   id="baseurl-${id}"
                                   value="${config.base_url || ''}"
                                   placeholder="https://api.example.com">
                        </div>
                        ` : ''}
                        <button class="btn-primary" onclick="window.app.settings.saveProviderChanges('${id}')">
                            Save Changes
                        </button>
                    </div>
                </div>
            `;
        }

        html += '</div>';
        return html;
    }

    renderDeploymentsTab() {
        if (!this.settings || !this.settings.deployment_targets) {
            return '<p>Loading deployment targets...</p>';
        }

        const targets = this.settings.deployment_targets;
        let html = '<div class="deployments-list">';

        for (const [id, config] of Object.entries(targets)) {
            html += `
                <div class="deployment-card">
                    <div class="deployment-header">
                        <h3>${config.name}</h3>
                        <label class="toggle">
                            <input type="checkbox"
                                   ${config.enabled ? 'checked' : ''}
                                   onchange="window.app.settings.toggleDeployment('${id}', this.checked)">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                    <div class="deployment-details">
                        ${this.renderDeploymentFields(id, config)}
                        <button class="btn-primary" onclick="window.app.settings.saveDeploymentChanges('${id}')">
                            Save Changes
                        </button>
                    </div>
                </div>
            `;
        }

        html += '</div>';
        return html;
    }

    renderDeploymentFields(id, config) {
        let fields = '';

        if (id === 'github') {
            fields = `
                <div class="form-group">
                    <label>Repository URL</label>
                    <input type="text" id="github-repo" value="${config.repo_url || ''}"
                           placeholder="https://github.com/username/repo">
                </div>
                <div class="form-group">
                    <label>Branch</label>
                    <input type="text" id="github-branch" value="${config.branch || 'gh-pages'}"
                           placeholder="gh-pages">
                </div>
                <div class="form-group">
                    <label>Access Token (Environment Variable)</label>
                    <input type="text" value="${config.access_token_env}" readonly>
                </div>
            `;
        } else if (id === 'ec2') {
            fields = `
                <div class="form-group">
                    <label>AWS Region</label>
                    <input type="text" id="ec2-region" value="${config.region || 'us-east-1'}"
                           placeholder="us-east-1">
                </div>
                <div class="form-group">
                    <label>Instance ID</label>
                    <input type="text" id="ec2-instance" value="${config.instance_id || ''}"
                           placeholder="i-1234567890abcdef0">
                </div>
                <div class="form-group">
                    <label>SSH Key Path</label>
                    <input type="text" id="ec2-ssh-key" value="${config.ssh_key_path || ''}"
                           placeholder="/path/to/key.pem">
                </div>
            `;
        } else if (id === 'docker') {
            fields = `
                <div class="form-group">
                    <label>Docker Host</label>
                    <input type="text" id="docker-host" value="${config.host || 'unix:///var/run/docker.sock'}"
                           placeholder="unix:///var/run/docker.sock">
                </div>
                <div class="form-group">
                    <label>Platform</label>
                    <select id="docker-platform">
                        <option value="linux/amd64" ${config.platform === 'linux/amd64' ? 'selected' : ''}>
                            Linux/AMD64 (x86-64)
                        </option>
                        <option value="linux/arm64" ${config.platform === 'linux/arm64' ? 'selected' : ''}>
                            Linux/ARM64 (Raspberry Pi, Apple Silicon)
                        </option>
                        <option value="linux/arm/v7" ${config.platform === 'linux/arm/v7' ? 'selected' : ''}>
                            Linux/ARM v7 (Older Raspberry Pi)
                        </option>
                    </select>
                </div>
            `;
        } else if (id === 'local') {
            fields = `
                <div class="form-group">
                    <label>Output Directory</label>
                    <input type="text" id="local-dir" value="${config.output_dir || './output'}"
                           placeholder="./output">
                </div>
            `;
        }

        return fields;
    }

    renderGeneralTab() {
        if (!this.settings || !this.settings.general) {
            return '<p>Loading general settings...</p>';
        }

        const general = this.settings.general;
        const planner = general.initial_planner || 'none';
        return `
            <div class="general-settings">
                <div class="form-group">
                    <label>Theme</label>
                    <select id="general-theme">
                        <option value="dark" ${general.theme === 'dark' ? 'selected' : ''}>Dark</option>
                        <option value="light" ${general.theme === 'light' ? 'selected' : ''}>Light</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Default Mode</label>
                    <select id="general-mode">
                        <option value="tri" ${general.default_mode === 'tri' ? 'selected' : ''}>Tri-Lam</option>
                        <option value="build" ${general.default_mode === 'build' ? 'selected' : ''}>Build</option>
                        <option value="consensus" ${general.default_mode === 'consensus' ? 'selected' : ''}>Consensus</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Initial Planner Agent</label>
                    <select id="general-planner">
                        <option value="none" ${planner === 'none' ? 'selected' : ''}>None (Chaotic Collaboration)</option>
                        <option value="openai" ${planner === 'openai' ? 'selected' : ''}>🟢 OpenAI</option>
                        <option value="anthropic" ${planner === 'anthropic' ? 'selected' : ''}>🔵 Anthropic</option>
                        <option value="gemini" ${planner === 'gemini' ? 'selected' : ''}>🟡 Gemini</option>
                    </select>
                    <small style="color: var(--text-secondary); display: block; margin-top: 0.5rem;">
                        When set, this agent will create the initial plan/design, then other agents will improve and build on it.
                    </small>
                </div>
                <div class="form-group">
                    <label>Log Level</label>
                    <select id="general-log-level">
                        <option value="debug" ${general.log_level === 'debug' ? 'selected' : ''}>Debug</option>
                        <option value="info" ${general.log_level === 'info' ? 'selected' : ''}>Info</option>
                        <option value="warning" ${general.log_level === 'warning' ? 'selected' : ''}>Warning</option>
                        <option value="error" ${general.log_level === 'error' ? 'selected' : ''}>Error</option>
                    </select>
                </div>
                <button class="btn-primary" onclick="window.app.settings.saveGeneralChanges()">
                    Save Changes
                </button>
            </div>
        `;
    }

    async toggleProvider(id, enabled) {
        const config = {...this.settings.llm_providers[id]};
        config.enabled = enabled;
        await this.saveProvider(id, config);
        this.app.showStatus(`${config.name} ${enabled ? 'enabled' : 'disabled'}`, 'success');
    }

    async toggleDeployment(id, enabled) {
        const config = {...this.settings.deployment_targets[id]};
        config.enabled = enabled;
        await this.saveDeploymentTarget(id, config);
        this.app.showStatus(`${config.name} ${enabled ? 'enabled' : 'disabled'}`, 'success');
    }

    async saveProviderChanges(id) {
        const config = {...this.settings.llm_providers[id]};
        const modelInput = document.getElementById(`model-${id}`);
        const baseUrlInput = document.getElementById(`baseurl-${id}`);

        if (modelInput) config.model = modelInput.value;
        if (baseUrlInput) config.base_url = baseUrlInput.value || null;

        const success = await this.saveProvider(id, config);
        if (success) {
            this.app.showStatus(`${config.name} settings saved`, 'success');
        } else {
            this.app.showStatus(`Failed to save ${config.name} settings`, 'error');
        }
    }

    async saveDeploymentChanges(id) {
        const config = {...this.settings.deployment_targets[id]};

        // Update config based on deployment type
        if (id === 'github') {
            config.repo_url = document.getElementById('github-repo')?.value || '';
            config.branch = document.getElementById('github-branch')?.value || 'gh-pages';
        } else if (id === 'ec2') {
            config.region = document.getElementById('ec2-region')?.value || 'us-east-1';
            config.instance_id = document.getElementById('ec2-instance')?.value || '';
            config.ssh_key_path = document.getElementById('ec2-ssh-key')?.value || '';
        } else if (id === 'docker') {
            config.host = document.getElementById('docker-host')?.value || 'unix:///var/run/docker.sock';
            config.platform = document.getElementById('docker-platform')?.value || 'linux/amd64';
        } else if (id === 'local') {
            config.output_dir = document.getElementById('local-dir')?.value || './output';
        }

        const success = await this.saveDeploymentTarget(id, config);
        if (success) {
            this.app.showStatus(`${config.name} settings saved`, 'success');
        } else {
            this.app.showStatus(`Failed to save ${config.name} settings`, 'error');
        }
    }

    async saveGeneralChanges() {
        const config = {
            theme: document.getElementById('general-theme')?.value || 'dark',
            default_mode: document.getElementById('general-mode')?.value || 'tri',
            log_level: document.getElementById('general-log-level')?.value || 'info',
            initial_planner: document.getElementById('general-planner')?.value || 'none',
            auto_save: this.settings.general.auto_save
        };

        try {
            const response = await fetch('/api/settings/general', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            const result = await response.json();
            if (result.status === 'success') {
                await this.load();
                this.app.showStatus('General settings saved', 'success');
                return true;
            }
            return false;
        } catch (error) {
            console.error('Failed to save general settings:', error);
            this.app.showStatus('Failed to save general settings', 'error');
            return false;
        }
    }
}
