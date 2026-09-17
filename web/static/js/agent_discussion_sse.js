/**
 * agent_discussion_sse.js — Agent 讨论 SSE 前端解析模块
 *
 * 用法:
 *   const discussion = new AgentDiscussionSSE({
 *       containerId: 'discussion-container',  // 讨论消息容器元素 ID
 *       apiUrl: '/api/v5/chat/stream',         // SSE 端点
 *   });
 *   discussion.start({ focus: 'JWT vs Session', agents: [...] });
 *
 * 消息类型:
 *   type="round" → 展示 Agent 发言气泡
 *   type="done"  → 展示共识结果面板
 */

class AgentDiscussionSSE {
    constructor(options = {}) {
        this.containerId = options.containerId || 'discussion-container';
        this.apiUrl = options.apiUrl || '/api/v5/chat/stream';
        this.userId = options.userId || 'web_user_' + Date.now();
        this.serverId = options.serverId || 'default';
        this._abortController = null;
        this._rounds = 0;
    }

    /**
     * 启动 Agent 讨论，建立 SSE 连接并实时渲染
     * @param {Object} params - { focus, agents, max_rounds? }
     */
    start(params = {}) {
        const { focus, agents, max_rounds = 8 } = params;
        if (!focus) { console.error('[AgentDiscussionSSE] focus 必填'); return; }
        if (!agents || !agents.length) { console.error('[AgentDiscussionSSE] agents 必填'); return; }

        // 清理容器
        const container = document.getElementById(this.containerId);
        if (!container) { console.error(`[AgentDiscussionSSE] 未找到容器 #${this.containerId}`); return; }
        container.innerHTML = '';

        // 显示讨论标题
        this._addElement('div', 'discussion-header', `<h3>🧠 多 Agent 讨论</h3><p>主题: ${focus}</p>`);

        // 创建 AbortController 用于中断
        this._abortController = new AbortController();

        // 使用 fetch + ReadableStream 读取 SSE
        fetch(this.apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: focus,
                user_id: this.userId,
                plan_status: 'agent_discussion',
                focus: focus,
                agents: agents,
                max_rounds: max_rounds,
                server_id: this.serverId,
            }),
            signal: this._abortController.signal,
        })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            const readChunk = () => {
                reader.read().then(({ done, value }) => {
                    if (done) return;
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    // 保留最后一个可能不完整的行
                    buffer = lines.pop() || '';

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const event = JSON.parse(line.slice(6));
                                this._handleEvent(event);
                            } catch (e) {
                                console.warn('[AgentDiscussionSSE] 解析失败:', line, e);
                            }
                        }
                    }
                    readChunk();
                }).catch(err => {
                    if (err.name !== 'AbortError') {
                        console.error('[AgentDiscussionSSE] 读取错误:', err);
                    }
                });
            };
            readChunk();
        })
        .catch(err => {
            if (err.name !== 'AbortError') {
                console.error('[AgentDiscussionSSE] 连接失败:', err);
                this._addElement('div', 'discussion-error', '⚠️ SSE 连接失败，请检查网络。');
            }
        });
    }

    /**
     * 中断讨论
     */
    stop() {
        if (this._abortController) {
            this._abortController.abort();
            this._abortController = null;
        }
    }

    /**
     * 处理 SSE 事件
     */
    _handleEvent(event) {
        const type = event.type;
        if (type === 'round') {
            this._renderRound(event);
        } else if (type === 'done') {
            this._renderDone(event);
        } else {
            console.debug('[AgentDiscussionSSE] 未知事件类型:', type, event);
        }
    }

    /**
     * 渲染 Agent 发言气泡 (type="round")
     */
    _renderRound(event) {
        const { round, agent, content } = event;
        const container = document.getElementById(this.containerId);
        if (!container) return;

        this._rounds = Math.max(this._rounds, round);

        // 发言气泡
        const bubble = this._addElement('div', `discussion-round round-${round} agent-${agent.replace(/\s+/g, '-')}`, `
            <div class="discussion-agent-name">🤖 ${agent} <span class="discussion-round-label">第 ${round} 轮</span></div>
            <div class="discussion-content">${this._escapeHtml(content)}</div>
        `);
        bubble.classList.add('discussion-message');

        // 滚动到底部
        container.scrollTop = container.scrollHeight;
    }

    /**
     * 渲染共识结果面板 (type="done")
     */
    _renderDone(event) {
        const { consensus, decision, rounds } = event;
        const container = document.getElementById(this.containerId);
        if (!container) return;

        const statusIcon = consensus ? '✅' : '⚠️';
        const statusText = consensus ? '已达成共识' : '未达成共识（使用兜底决策）';

        const panel = this._addElement('div', 'discussion-done', `
            <div class="discussion-consensus-header">${statusIcon} ${statusText}</div>
            <div class="discussion-consensus-body">
                <div class="discussion-decision-label">📋 最终决策</div>
                <div class="discussion-decision-content">${this._escapeHtml(decision)}</div>
                <div class="discussion-rounds-info">共进行了 <strong>${rounds}</strong> 轮讨论</div>
            </div>
        `);
        panel.classList.add('discussion-done-panel');

        container.scrollTop = container.scrollHeight;
    }

    // ========== 辅助方法 ==========

    _addElement(tag, className, innerHTML) {
        const container = document.getElementById(this.containerId);
        if (!container) return null;
        const el = document.createElement(tag);
        if (className) el.className = className;
        if (innerHTML) el.innerHTML = innerHTML;
        container.appendChild(el);
        return el;
    }

    _escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML.replace(/\n/g, '<br>');
    }
}

// 全局导出
window.AgentDiscussionSSE = AgentDiscussionSSE;
