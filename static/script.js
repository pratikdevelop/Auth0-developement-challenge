let currentChatId = null;
let isStreaming = false;

async function loadChats() {
    try {
        const response = await fetch('/api/chats');
        const chats = await response.json();
        
        const chatList = document.getElementById('chat-list');
        chatList.innerHTML = '';
        
        chats.forEach(chat => {
            const chatItem = document.createElement('div');
            chatItem.className = 'chat-item';
            if (chat.id === currentChatId) {
                chatItem.classList.add('active');
            }
            
            chatItem.innerHTML = `
                <span class="chat-item-title">${chat.title}</span>
                <button class="delete-chat-btn" onclick="deleteChat(${chat.id}, event)">×</button>
            `;
            
            chatItem.onclick = (e) => {
                if (!e.target.classList.contains('delete-chat-btn')) {
                    loadChat(chat.id);
                }
            };
            
            chatList.appendChild(chatItem);
        });
    } catch (error) {
        console.error('Error loading chats:', error);
    }
}

async function createNewChat() {
    try {
        const response = await fetch('/api/chats', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: 'New Chat' })
        });
        
        const chat = await response.json();
        await loadChats();
        loadChat(chat.id);
    } catch (error) {
        console.error('Error creating chat:', error);
    }
}

async function deleteChat(chatId, event) {
    event.stopPropagation();
    
    if (!confirm('Are you sure you want to delete this chat?')) {
        return;
    }
    
    try {
        await fetch(`/api/chats/${chatId}`, { method: 'DELETE' });
        
        if (currentChatId === chatId) {
            currentChatId = null;
            document.getElementById('messages').innerHTML = '';
            document.getElementById('chat-header').innerHTML = '<h3>Select or create a new chat</h3>';
        }
        
        await loadChats();
    } catch (error) {
        console.error('Error deleting chat:', error);
    }
}

async function loadChat(chatId) {
    currentChatId = chatId;
    
    try {
        const response = await fetch(`/api/chats/${chatId}/messages`);
        const messages = await response.json();
        
        const messagesContainer = document.getElementById('messages');
        messagesContainer.innerHTML = '';
        
        messages.forEach(msg => {
            addMessageToUI(msg.role, msg.content);
        });
        
        document.getElementById('chat-header').innerHTML = '<h3>Chat</h3>';
        
        await loadChats();
        
        scrollToBottom();
    } catch (error) {
        console.error('Error loading chat:', error);
    }
}

function addMessageToUI(role, content) {
    const messagesContainer = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    messageDiv.innerHTML = `
        <div class="message-role">${role === 'user' ? 'You' : 'AI'}</div>
        <div class="message-content">${content}</div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
    
    return messageDiv;
}

function scrollToBottom() {
    const messagesContainer = document.getElementById('messages');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

async function sendMessage() {
    if (!currentChatId) {
        alert('Please select or create a chat first');
        return;
    }
    
    if (isStreaming) {
        return;
    }
    
    const input = document.getElementById('message-input');
    const message = input.value.trim();
    
    if (!message) {
        return;
    }
    
    input.value = '';
    input.style.height = 'auto';
    
    addMessageToUI('user', message);
    
    const sendBtn = document.getElementById('send-btn');
    sendBtn.disabled = true;
    isStreaming = true;
    
    const assistantMessageDiv = addMessageToUI('assistant', '');
    const contentDiv = assistantMessageDiv.querySelector('.message-content');
    
    try {
        const response = await fetch(`/api/chats/${currentChatId}/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.slice(6));
                    
                    if (data.content) {
                        contentDiv.textContent += data.content;
                        scrollToBottom();
                    }
                    
                    if (data.error) {
                        contentDiv.textContent = 'Error: ' + data.error;
                    }
                }
            }
        }
    } catch (error) {
        console.error('Error sending message:', error);
        contentDiv.textContent = 'Error: Failed to send message';
    } finally {
        sendBtn.disabled = false;
        isStreaming = false;
    }
}

document.getElementById('new-chat-btn').onclick = createNewChat;
document.getElementById('send-btn').onclick = sendMessage;

document.getElementById('message-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

document.getElementById('message-input').addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 150) + 'px';
});

loadChats();
