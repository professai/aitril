// AiTril Web Interface - Real-time Agent Visualization

class AiTrilApp {
    constructor() {
        this.ws = null;
        this.currentMode = 'build';
        this.agents = {}; // Will be populated from settings API
        this.currentPhase = null;
        this.messages = [];
        this.modeInfo = {
            build: {
                title: 'Build - Collaborative Code Generation',
                description: 'Useful if you are trying to create or modify code with thorough planning and review. Uses a 3-phase approach: Planning (all agents collaborate), Implementation (sequential execution), and Review (all agents validate).'
            },
            tri: {
                title: 'Tri-Lam - Multiple Perspectives',
                description: 'Useful if you are trying to get diverse viewpoints on a question or problem. All agents respond in parallel and you see each provider\'s unique perspective separately.'
            },
            consensus: {
                title: 'Consensus - Unified Answer',
                description: 'Useful if you are trying to get a single best answer. All agents respond in parallel, and their responses are synthesized into one unified, well-rounded answer.'
            }
        };

        this.init();
    }

    async init() {
        // Initialize settings manager
        this.settings = new SettingsManager(this);
        await this.settings.load();

        // Load initial planner setting
        this.initialPlanner = this.settings.settings?.general?.initial_planner || 'none';

        await this.loadProviders();
        this.render();
        this.connectWebSocket();
        this.setupEventListeners();

        // Expose to window for settings button
        window.app = this;
    }

    async loadProviders() {
        try {
            const response = await fetch('/api/settings/providers');
            const providers = await response.json();

            // Initialize agents from settings (up to 8 providers)
            this.agents = {};

            // Add initial planner as first agent if configured
            if (this.initialPlanner && this.initialPlanner !== 'none' && providers[this.initialPlanner]?.enabled) {
                const plannerConfig = providers[this.initialPlanner];
                this.agents[`planner_${this.initialPlanner}`] = {
                    name: `📋 Planner (${plannerConfig.name})`,
                    model: plannerConfig.model,
                    status: 'idle',
                    response: '',
                    isPlanner: true
                };
            }

            Object.entries(providers).forEach(([id, config]) => {
                if (config.enabled) {
                    this.agents[id] = {
                        name: config.name || id,
                        model: config.model || 'default',
                        status: 'idle',
                        response: ''
                    };
                }
            });

            // If no providers are enabled, set up defaults for demo
            if (Object.keys(this.agents).length === 0) {
                this.agents = {
                    openai: { name: 'GPT (OpenAI)', model: 'gpt-5.1', status: 'idle', response: '' },
                    anthropic: { name: 'Claude (Anthropic)', model: 'claude-opus-4.5', status: 'idle', response: '' },
                    gemini: { name: 'Gemini (Google)', model: 'gemini-3-pro', status: 'idle', response: '' }
                };
            }
        } catch (error) {
            console.error('Failed to load providers:', error);
            // Fall back to defaults
            this.agents = {
                openai: { name: 'GPT (OpenAI)', model: 'gpt-5.1', status: 'idle', response: '' },
                anthropic: { name: 'Claude (Anthropic)', model: 'claude-opus-4.5', status: 'idle', response: '' },
                gemini: { name: 'Gemini (Google)', model: 'gemini-3-pro', status: 'idle', response: '' }
            };
        }
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.showStatus('Connected', 'success');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleEvent(data);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.showStatus('Connection error', 'error');
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.showStatus('Disconnected', 'error');
            // Attempt to reconnect after 3 seconds
            setTimeout(() => this.connectWebSocket(), 3000);
        };
    }

    handleEvent(event) {
        console.log('Event received:', event.type, event);

        switch (event.type) {
            case 'connected':
                this.showStatus('Ready', 'success');
                break;

            case 'message_received':
                this.addUserMessage(event.prompt);
                break;

            case 'agent_started':
                this.setAgentStatus(event.agent, 'active');
                this.addAgentMessage(event.agent);
                break;

            case 'agent_chunk':
                this.appendAgentChunk(event.agent, event.chunk);
                break;

            case 'agent_completed':
                this.setAgentStatus(event.agent, 'completed');
                break;

            case 'trilam_started':
                this.resetAgents();
                break;

            case 'trilam_completed':
                this.setAllAgentsCompleted();
                break;

            case 'phase_changed':
                this.setPhase(event.phase, event.description);
                break;

            case 'build_started':
                this.resetPhases();
                break;

            case 'build_completed':
                this.clearPhase();
                break;

            case 'coordination_started':
                this.resetAgents();
                break;

            case 'coordination_completed':
                this.setAllAgentsCompleted();
                break;

            case 'deployment_options':
                this.showDeploymentOptions(event.options);
                break;

            case 'deployment_started':
                this.messages.push({
                    type: 'status',
                    content: `🚀 Starting deployment: ${event.name}`,
                    timestamp: new Date()
                });
                this.renderMessages();
                this.scrollToBottom();
                break;

            case 'status_message':
                this.messages.push({
                    type: 'status',
                    content: event.message,
                    timestamp: new Date()
                });
                this.renderMessages();
                this.scrollToBottom();
                break;

            case 'deployment_completed':
                this.messages.push({
                    type: 'status',
                    content: '✅ Deployment completed!',
                    timestamp: new Date()
                });
                this.renderMessages();
                this.scrollToBottom();
                // Re-enable send button
                document.querySelector('.send-btn').disabled = false;
                break;
        }
    }

    showDeploymentOptions(options) {
        // Add deployment selector to the messages
        const optionsHTML = options.map(opt => `
            <div class="deployment-option" data-id="${opt.id}">
                <div class="deployment-option-header">
                    <input type="radio" name="deployment" value="${opt.id}" id="deploy-${opt.id}" />
                    <label for="deploy-${opt.id}">
                        <strong>${opt.name}</strong>
                    </label>
                </div>
                <p class="deployment-option-description">${opt.description}</p>
            </div>
        `).join('');

        this.messages.push({
            type: 'deployment-selector',
            options: optionsHTML
        });

        this.renderMessages();
        this.scrollToBottom();

        // Add event listeners for radio buttons
        setTimeout(() => {
            document.querySelectorAll('.deployment-option input[type="radio"]').forEach(radio => {
                radio.addEventListener('change', (e) => {
                    this.selectDeploymentTarget(e.target.value);
                });
            });
        }, 100);
    }

    selectDeploymentTarget(targetId) {
        console.log('Selected deployment target:', targetId);

        // Send deployment selection to backend
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'deployment_selected',
                target: targetId
            }));
        }

        // Add a status message to show selection
        this.messages.push({
            type: 'status',
            content: `Deployment target selected: ${targetId}`,
            timestamp: new Date()
        });
        this.renderMessages();
        this.scrollToBottom();
    }

    setupEventListeners() {
        // Mode selector
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.setMode(e.target.dataset.mode);
            });
        });

        // Info buttons
        document.querySelectorAll('.info-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.showModeInfo(e.target.dataset.mode);
            });
        });

        // Close modal on background click
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.closeModal();
            }
        });

        // Close button
        const closeBtn = document.querySelector('.modal-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeModal());
        }

        // Send button
        const sendBtn = document.querySelector('.send-btn');
        const inputField = document.querySelector('.input-field');

        sendBtn.addEventListener('click', () => this.sendMessage());
        inputField.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }

    showModeInfo(mode) {
        const info = this.modeInfo[mode];
        if (!info) return;

        const modal = document.querySelector('.modal');
        const title = document.querySelector('.modal-title');
        const content = document.querySelector('.modal-description');

        title.textContent = info.title;
        content.textContent = info.description;
        modal.classList.add('active');
    }

    closeModal() {
        const modal = document.querySelector('.modal');
        modal.classList.remove('active');
    }

    setMode(mode) {
        this.currentMode = mode;

        // Update UI
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === mode);
        });
    }

    sendMessage() {
        const input = document.querySelector('.input-field');
        const prompt = input.value.trim();

        if (!prompt || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
            return;
        }

        // Send message via WebSocket
        this.ws.send(JSON.stringify({
            prompt,
            mode: this.currentMode
        }));

        // Clear input
        input.value = '';
        input.style.height = 'auto';

        // Disable send button
        document.querySelector('.send-btn').disabled = true;
    }

    addUserMessage(text) {
        this.messages.push({
            type: 'user',
            content: text,
            timestamp: new Date()
        });
        this.renderMessages();
        this.scrollToBottom();
    }

    addAgentMessage(agent) {
        // Check if we already have a message group for this agent in the current batch
        const lastMessage = this.messages[this.messages.length - 1];

        if (lastMessage && lastMessage.type === 'agent-group') {
            // Add to existing group
            if (!lastMessage.agents[agent]) {
                lastMessage.agents[agent] = {
                    name: this.agents[agent].name,
                    content: '',
                    timestamp: new Date()
                };
            }
        } else {
            // Create new agent group
            this.messages.push({
                type: 'agent-group',
                agents: {
                    [agent]: {
                        name: this.agents[agent].name,
                        content: '',
                        timestamp: new Date()
                    }
                }
            });
        }

        this.renderMessages();
        this.scrollToBottom();
    }

    appendAgentChunk(agent, chunk) {
        const lastMessage = this.messages[this.messages.length - 1];

        if (lastMessage && lastMessage.type === 'agent-group' && lastMessage.agents[agent]) {
            lastMessage.agents[agent].content += chunk;
            this.renderMessages();
            this.scrollToBottom();
        }
    }

    setAgentStatus(agent, status) {
        this.agents[agent].status = status;
        this.renderAgents();
    }

    setAllAgentsCompleted() {
        Object.keys(this.agents).forEach(agent => {
            this.agents[agent].status = 'completed';
        });
        this.renderAgents();

        // Re-enable send button
        document.querySelector('.send-btn').disabled = false;
    }

    resetAgents() {
        Object.keys(this.agents).forEach(agent => {
            this.agents[agent].status = 'idle';
            this.agents[agent].response = '';
        });
        this.renderAgents();
    }

    setPhase(phase, description) {
        this.currentPhase = phase;
        this.renderPhases();
    }

    clearPhase() {
        this.currentPhase = null;
        this.renderPhases();
    }

    resetPhases() {
        this.currentPhase = 'planning';
        this.renderPhases();
    }

    showStatus(message, type) {
        // Could show a toast notification
        console.log(`Status: ${message} (${type})`);
    }

    scrollToBottom() {
        const container = document.querySelector('.messages-container');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }

    getAgentIcon(agentId) {
        // Return appropriate icon for each agent type
        const icons = {
            openai: 'G',
            anthropic: 'C',
            gemini: 'Gm',
            ollama: 'O',
            llamacpp: 'L',
            custom1: 'C1',
            custom2: 'C2',
            custom3: 'C3'
        };
        return icons[agentId] || agentId[0].toUpperCase();
    }

    getAgentBadge(agent) {
        // Add badge for local models
        if (agent.model && (agent.model.includes('ollama') || agent.model.includes('llama'))) {
            return '<span class="local-badge">LOCAL</span>';
        }
        return '';
    }

    renderAgents() {
        const container = document.querySelector('.agents-container');
        if (!container) return;

        container.innerHTML = Object.entries(this.agents).map(([key, agent]) => `
            <div class="agent-card ${key} ${agent.status === 'active' ? 'active' : ''}">
                <div class="agent-header">
                    <div class="agent-name">
                        <div class="agent-icon ${key}">${this.getAgentIcon(key)}</div>
                        <div class="agent-info">
                            <span class="agent-title">${agent.name}</span>
                            ${agent.model ? `<span class="agent-model">${agent.model}</span>` : ''}
                        </div>
                        ${this.getAgentBadge(agent)}
                    </div>
                    <div class="agent-status">
                        <div class="status-dot ${agent.status === 'active' ? 'active' : ''}"></div>
                        <span>${agent.status}</span>
                    </div>
                </div>
                ${agent.status === 'active' ? `
                    <div class="agent-progress">Generating response...</div>
                ` : ''}
            </div>
        `).join('');
    }

    renderPhases() {
        const container = document.querySelector('.phases');
        if (!container) return;

        const phases = [
            { key: 'planning', label: 'Planning' },
            { key: 'implementation', label: 'Implementation' },
            { key: 'review', label: 'Review' },
            { key: 'deployment', label: 'Deployment' }
        ];

        container.innerHTML = phases.map(phase => `
            <div class="phase ${phase.key} ${this.currentPhase === phase.key ? 'active' : ''}">
                <div class="phase-dot"></div>
                <span>${phase.label}</span>
            </div>
        `).join('');
    }

    renderMessages() {
        const container = document.querySelector('.messages-container');
        if (!container) return;

        container.innerHTML = this.messages.map(msg => {
            if (msg.type === 'user') {
                return `
                    <div class="message user">
                        <div class="message-header">
                            <div class="message-avatar user">U</div>
                            <span>You</span>
                        </div>
                        <div class="message-content">${this.escapeHtml(msg.content)}</div>
                    </div>
                `;
            } else if (msg.type === 'agent-group') {
                return `
                    <div class="agent-response-group">
                        ${Object.entries(msg.agents).map(([agent, data]) => `
                            <div class="agent-response ${agent}">
                                <div class="message-avatar ${agent}">${agent[0].toUpperCase()}</div>
                                <div class="agent-response-content">
                                    <div class="message-header">
                                        <span>${data.name}</span>
                                    </div>
                                    <div class="message-content">
                                        ${data.content ? this.formatResponse(data.content) : `
                                            <div class="loading-indicator">
                                                <div class="loading-dot"></div>
                                                <div class="loading-dot"></div>
                                                <div class="loading-dot"></div>
                                            </div>
                                        `}
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `;
            } else if (msg.type === 'deployment-selector') {
                return `
                    <div class="deployment-selector">
                        <h3>Choose Deployment Target</h3>
                        <div class="deployment-options">
                            ${msg.options}
                        </div>
                    </div>
                `;
            }
            return '';
        }).join('');
    }

    formatResponse(text) {
        // Basic markdown-like formatting
        let formatted = this.escapeHtml(text);

        // Code blocks
        formatted = formatted.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
            return `<pre><code>${code.trim()}</code></pre>`;
        });

        // Inline code
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');

        // Bold
        formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

        // Line breaks
        formatted = formatted.replace(/\n/g, '<br>');

        return formatted;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    render() {
        const app = document.getElementById('app');

        app.innerHTML = `
            <!-- Sidebar -->
            <div class="sidebar">
                <div class="sidebar-header">
                    <div class="logo">🧬</div>
                    <div>
                        <div class="app-title">AiTril</div>
                        <div class="app-subtitle">Multi-Agent Orchestration</div>
                    </div>
                    <button class="settings-btn" onclick="window.app.settings.open()" title="Settings">
                        ⚙️
                    </button>
                </div>

                <div class="agents-container"></div>

                <div class="phase-indicator">
                    <div class="phase-header">BUILD PHASES</div>
                    <div class="phases"></div>
                </div>
            </div>

            <!-- Main Content -->
            <div class="main-content">
                <div class="chat-header">
                    <div class="mode-selector">
                        <div class="mode-option">
                            <button class="mode-btn active" data-mode="build">Build</button>
                            <button class="info-btn" data-mode="build" title="Learn about Build mode">ⓘ</button>
                        </div>
                        <div class="mode-option">
                            <button class="mode-btn" data-mode="tri">Tri-Lam</button>
                            <button class="info-btn" data-mode="tri" title="Learn about Tri-Lam mode">ⓘ</button>
                        </div>
                        <div class="mode-option">
                            <button class="mode-btn" data-mode="consensus">Consensus</button>
                            <button class="info-btn" data-mode="consensus" title="Learn about Consensus mode">ⓘ</button>
                        </div>
                    </div>
                </div>

                <div class="messages-container"></div>

                <div class="input-container">
                    <div class="input-wrapper">
                        <textarea
                            class="input-field"
                            placeholder="Send a message to all agents..."
                            rows="1"
                        ></textarea>
                        <button class="send-btn">Send</button>
                    </div>
                </div>
            </div>

            <!-- Modal -->
            <div class="modal">
                <div class="modal-content">
                    <button class="modal-close">×</button>
                    <h2 class="modal-title"></h2>
                    <p class="modal-description"></p>
                </div>
            </div>
        `;

        // Auto-resize textarea
        const textarea = document.querySelector('.input-field');
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 200) + 'px';
        });

        // Initial render of agents and phases
        this.renderAgents();
        this.renderPhases();
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new AiTrilApp();
});
