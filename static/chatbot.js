// Chatbot Widget JavaScript
(function() {
    'use strict';
    
    let isMinimized = false;
    let eventSource = null;
    
    // Create chatbot widget HTML
    function createChatbotWidget() {
        const widget = document.createElement('div');
        widget.id = 'chatbot-widget';
        widget.className = 'chatbot-widget minimized';
        widget.innerHTML = `
            <div class="chatbot-header">
                <h3>💬 Chat Assistant</h3>
                <div class="chatbot-header-actions">
                    <button class="chatbot-btn" id="chatbot-minimize" title="Minimize">−</button>
                </div>
            </div>
            <div class="chatbot-messages" id="chatbot-messages"></div>
            <div class="chatbot-input-container">
                <form class="chatbot-input-form" id="chatbot-form">
                    <input 
                        type="text" 
                        class="chatbot-input" 
                        id="chatbot-input" 
                        placeholder="Ask about albums..."
                        autocomplete="off"
                    />
                    <button type="submit" class="chatbot-send-btn" id="chatbot-send">➤</button>
                </form>
            </div>
        `;
        document.body.appendChild(widget);
        
        // Create toggle button
        const toggle = document.createElement('button');
        toggle.className = 'chatbot-toggle';
        toggle.innerHTML = '💬';
        toggle.title = 'Open Chat';
        toggle.onclick = toggleChatbot;
        document.body.appendChild(toggle);
        
        // Setup event listeners
        setupEventListeners();
        
        // Add welcome message
        addBotMessage("Hello! I'm your Metal Music Store assistant. Ask me about albums, artists, or prices!");
    }
    
    function setupEventListeners() {
        const form = document.getElementById('chatbot-form');
        const input = document.getElementById('chatbot-input');
        const minimizeBtn = document.getElementById('chatbot-minimize');
        
        form.addEventListener('submit', handleSubmit);
        minimizeBtn.addEventListener('click', toggleMinimize);
        
        // Allow Enter to send, Shift+Enter for new line
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
            }
        });
    }
    
    function toggleChatbot() {
        const widget = document.getElementById('chatbot-widget');
        const toggle = document.querySelector('.chatbot-toggle');
        
        if (widget.classList.contains('minimized')) {
            widget.classList.remove('minimized');
            isMinimized = false;
            toggle.style.display = 'none';
            document.getElementById('chatbot-input').focus();
        } else {
            widget.classList.add('minimized');
            isMinimized = true;
            toggle.style.display = 'flex';
        }
    }
    
    function toggleMinimize() {
        toggleChatbot();
    }
    
    function handleSubmit(e) {
        e.preventDefault();
        
        const input = document.getElementById('chatbot-input');
        const message = input.value.trim();
        
        if (!message) return;
        
        // Add user message
        addUserMessage(message);
        
        // Clear input
        input.value = '';
        
        // Show typing indicator
        showTypingIndicator();
        
        // Send message to API
        sendMessage(message);
    }
    
    function addUserMessage(text) {
        const messagesContainer = document.getElementById('chatbot-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chatbot-message user';
        messageDiv.innerHTML = `
            <div class="chatbot-message-bubble">${escapeHtml(text)}</div>
            <div class="chatbot-message-time">${getTimeString()}</div>
        `;
        messagesContainer.appendChild(messageDiv);
        scrollToBottom();
    }
    
    function addBotMessage(text) {
        const messagesContainer = document.getElementById('chatbot-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chatbot-message bot';
        messageDiv.innerHTML = `
            <div class="chatbot-message-bubble">${escapeHtml(text)}</div>
            <div class="chatbot-message-time">${getTimeString()}</div>
        `;
        messagesContainer.appendChild(messageDiv);
        scrollToBottom();
    }
    
    function showTypingIndicator() {
        const messagesContainer = document.getElementById('chatbot-messages');
        const typingDiv = document.createElement('div');
        typingDiv.className = 'chatbot-message bot';
        typingDiv.id = 'typing-indicator';
        typingDiv.innerHTML = `
            <div class="chatbot-typing">
                <div class="chatbot-typing-dot"></div>
                <div class="chatbot-typing-dot"></div>
                <div class="chatbot-typing-dot"></div>
            </div>
        `;
        messagesContainer.appendChild(typingDiv);
        scrollToBottom();
    }
    
    function removeTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    function sendMessage(message) {
        // Close any existing EventSource
        if (eventSource) {
            eventSource.close();
        }
        
        const sendBtn = document.getElementById('chatbot-send');
        sendBtn.disabled = true;
        
        // Create a container for the bot's response
        const messagesContainer = document.getElementById('chatbot-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chatbot-message bot';
        messageDiv.id = 'current-bot-message';
        messageDiv.innerHTML = `
            <div class="chatbot-message-bubble"></div>
            <div class="chatbot-message-time">${getTimeString()}</div>
        `;
        messagesContainer.appendChild(messageDiv);
        
        const bubble = messageDiv.querySelector('.chatbot-message-bubble');
        let fullResponse = '';
        
        // Use EventSource for SSE streaming
        const url = `/api/chat?chat=${encodeURIComponent(message)}`;
        eventSource = new EventSource(url);
        
        eventSource.onmessage = function(event) {
            removeTypingIndicator();
            
            try {
                const data = JSON.parse(event.data);
                
                if (data.error) {
                    bubble.textContent = `Error: ${data.error}`;
                    bubble.style.color = '#d32f2f';
                    eventSource.close();
                    sendBtn.disabled = false;
                    return;
                }
                
                if (data.content) {
                    fullResponse += data.content;
                    bubble.innerHTML = escapeHtml(fullResponse).replace(/\n/g, '<br>');
                    scrollToBottom();
                }
            } catch (e) {
                console.error('Error parsing SSE data:', e);
            }
        };
        
        eventSource.addEventListener('error', function(event) {
            console.error('SSE error:', event);
            removeTypingIndicator();
            if (fullResponse === '') {
                bubble.textContent = 'Sorry, I encountered an error. Please try again.';
                bubble.style.color = '#d32f2f';
            }
            eventSource.close();
            sendBtn.disabled = false;
        });
        
        // Handle close event
        eventSource.onerror = function(event) {
            if (eventSource.readyState === EventSource.CLOSED) {
                sendBtn.disabled = false;
                removeTypingIndicator();
            }
        };
    }
    
    function scrollToBottom() {
        const messagesContainer = document.getElementById('chatbot-messages');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    function getTimeString() {
        const now = new Date();
        return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    
    // Initialize chatbot when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', createChatbotWidget);
    } else {
        createChatbotWidget();
    }
})();


