// AiTril Web Interface - Real-time Agent Visualization

class AiTrilApp {
    constructor() {
        this.ws = null;
        this.currentMode = 'tri';
        this.agents = {
            gpt: { name: 'GPT-5.1', status: 'idle', response: '' },
            claude: { name: 'Claude Opus 4.5', status: 'idle', response: '' },
            gemini: { name: 'Gemini 3 Pro', status: 'idle', response: '' }
        };
        this.currentPhase = null;
        this.messages = [];

        this.init();
    }

    init() {
        this.render();
        this.connectWebSocket();
        this.setupEventListeners();
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
        }
    }

    setupEventListeners() {
        // Mode selector
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.setMode(e.target.dataset.mode);
            });
        });

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

    renderAgents() {
        const container = document.querySelector('.agents-container');
        if (!container) return;

        container.innerHTML = Object.entries(this.agents).map(([key, agent]) => `
            <div class="agent-card ${key} ${agent.status === 'active' ? 'active' : ''}">
                <div class="agent-header">
                    <div class="agent-name">
                        <div class="agent-icon ${key}">${key[0].toUpperCase()}</div>
                        <span>${agent.name}</span>
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
            { key: 'review', label: 'Review' }
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
                        <button class="mode-btn active" data-mode="tri">Tri-Lam</button>
                        <button class="mode-btn" data-mode="sequential">Sequential</button>
                        <button class="mode-btn" data-mode="consensus">Consensus</button>
                        <button class="mode-btn" data-mode="debate">Debate</button>
                        <button class="mode-btn" data-mode="build">Build</button>
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
