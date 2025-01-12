// 首先声明全局变量
let socket;
let messagesDiv;
let messageInput;
let messageHistory;
let currentRoom;

// 初始化函数
function initializeChat() {
    socket = io();
    messagesDiv = document.getElementById('messages');
    messageInput = document.getElementById('message');
    
    // 从URL获取房间ID
    const pathParts = window.location.pathname.split('/');
    currentRoom = pathParts[pathParts.indexOf('chat') + 1];
    
    console.log('初始化聊天室 - 当前房间ID:', currentRoom);
    console.log('历史消息:', window.CHAT_HISTORY);

    if (currentRoom) {
        setupSocketListeners();
        initializeEventListeners();
        loadChatHistory();
        joinRoom(currentRoom);
    } else {
        console.log('等待选择聊天室');
    }
}

// 加载历史消息
function loadChatHistory() {
    if (!messagesDiv) {
        console.error('消息容器不存在');
        return;
    }

    // 清空消息显示区域
    messagesDiv.innerHTML = '';
    
    // 检查并加载历史消息
    if (window.CHAT_HISTORY && Array.isArray(window.CHAT_HISTORY)) {
        console.log('开始加载历史消息，共', window.CHAT_HISTORY.length, '条');
        window.CHAT_HISTORY.forEach((data, index) => {
            console.log(`加载第 ${index + 1} 条历史消息:`, data);
            addMessage({
                user: data.user,
                message: data.message,
                timestamp: data.timestamp
            });
        });
        // 滚动到最新消息
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        console.log('历史消息加载完成');
    } else {
        console.log('没有历史消息可加载');
    }
}

// 发送消息函数
function sendMessage() {
    if (!messageInput) {
        console.error('找不到消息输入框');
        return;
    }

    const message = messageInput.value.trim();
    if (!message) {
        console.log('消息内容为空');
        return;
    }

    if (!currentRoom) {
        console.error('未选择聊天室，当前房间ID:', currentRoom, '类型:', typeof currentRoom);
        alert('请先选择聊天室');
        return;
    }

    // 防止重复发送
    if (messageInput.disabled) {
        console.log('消息正在发送中，请等待');
        return;
    }

    console.log('发送消息到房间:', currentRoom, '消息内容:', message);

    try {
        // 禁用输入框，防止重复发送
        messageInput.disabled = true;
        
        // 发送消息到服务器
        socket.emit('message', {
            room_id: currentRoom,
            content: message
        }, (response) => {
            // 启用输入框
            messageInput.disabled = false;
            
            if (response && response.error) {
                console.error('服务器返回错误:', response.error);
                alert(response.error);
                return;
            }
            // 清空输入框
            messageInput.value = '';
            console.log('消息已发送到服务器，等待广播');
        });
    } catch (error) {
        // 确保输入框被重新启用
        messageInput.disabled = false;
        console.error('发送消息时出错:', error);
        alert('发送消息失败，请重试');
    }
}

// 加入房间函数
function joinRoom(roomId) {
    if (!roomId) {
        console.error('无效的房间ID');
        return;
    }

    console.log('加入房间:', roomId);
    
    // 发送加入房间请求
    socket.emit('join', { room_id: roomId });
    
    // 加载历史消息
    loadChatHistory();
}

// 初始化事件监听器
function initializeEventListeners() {
    // 输入框回车事件
    if (messageInput) {
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    // 发送按钮点击事件
    const sendBtn = document.querySelector('.chat-input-container button');
    if (sendBtn) {
        sendBtn.addEventListener('click', function(e) {
            e.preventDefault();
            sendMessage();
        });
        console.log('发送按钮事件已绑定');
    }
}

// Socket.IO 事件监听器
function setupSocketListeners() {
    socket.on('connect', () => {
        console.log('WebSocket 已连接');
        // 重新加入房间
        if (currentRoom) {
            joinRoom(currentRoom);
        }
    });

    socket.on('message', (data) => {
        console.log('收到服务器消息:', data);
        // 确保消息来自当前房间
        if (data.room_id && data.room_id.toString() === currentRoom.toString()) {
            console.log('添加消息到显示区域:', data);
            addMessage({
                user: data.user,
                message: data.message,
                timestamp: data.timestamp
            });
            // 滚动到最新消息
            if (messagesDiv) {
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }
        } else {
            console.log('消息不属于当前房间，忽略');
        }
    });

    socket.on('error', (data) => {
        console.error('收到错误消息:', data.message);
        // 启用输入框（如果被禁用）
        if (messageInput && messageInput.disabled) {
            messageInput.disabled = false;
        }
        alert(data.message);
    });

    socket.on('system_message', (data) => {
        console.log('收到系统消息:', data);
        if (data.room_id && data.room_id.toString() === currentRoom.toString()) {
            addSystemMessage(data.message, data.timestamp);
        }
    });

    socket.on('disconnect', () => {
        console.log('WebSocket 已断开');
        // 启用输入框（如果被禁用）
        if (messageInput && messageInput.disabled) {
            messageInput.disabled = false;
        }
    });
}

// 添加系统消息显示函数
function addSystemMessage(message, timestamp) {
    if (!messagesDiv) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'chat-message system-message';
    messageDiv.innerHTML = `
        <div class="text-center">
            <small class="text-muted">${timestamp}</small>
            <p class="mb-0 text-muted"><i>${message}</i></p>
        </div>
    `;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// 添加消息到显示区域
function addMessage(data) {
    if (!messagesDiv) {
        console.error('消息容器不存在');
        return;
    }
    
    try {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chat-message';
        messageDiv.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-1">
                <strong><i class="fa fa-user-circle"></i> ${data.user}</strong>
                <small class="text-muted"><i class="fa fa-clock-o"></i> ${data.timestamp}</small>
            </div>
            <p class="mb-0">${data.message}</p>
        `;
        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        console.log('消息已添加到显示区域');
    } catch (error) {
        console.error('添加消息到显示区域时出错:', error);
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    console.log('开始初始化聊天功能');
    initializeChat();
}); 