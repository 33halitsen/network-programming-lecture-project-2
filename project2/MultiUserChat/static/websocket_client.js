// static/websocket_client.js

const WS_PORT = 8001; // Sunucunuzdaki WebSocket portuyla eşleşmeli
const WS_URL = `ws://localhost:${WS_PORT}`;

let socket;

function connectWebSocket() {
    const password = document.getElementById('password').value;
    const statusElement = document.getElementById('status');
    const logContainer = document.getElementById('log-container');

    if (socket) {
        statusElement.textContent = 'Already connected or connecting.';
        return;
    }

    statusElement.textContent = 'Connecting...';
    logContainer.innerHTML = 'Attempting to establish WebSocket connection...';

    try {
        socket = new WebSocket(WS_URL);

        socket.onopen = () => {
            statusElement.textContent = 'Authenticating...';
            // 1. Bağlantı açıldığında ADMIN ŞİFRESİNİ gönder
            socket.send(password);
        };

        socket.onmessage = (event) => {
            const data = event.data;
            let logEntry = document.createElement('div');
            logEntry.className = 'log-entry';

            // 2. Sunucudan gelen mesajı işle
            if (data.startsWith('Authentication Success')) {
                statusElement.textContent = 'Connected & Streaming (Authenticated)';
                logContainer.innerHTML = ''; // Eski mesajları temizle
            } else if (data.startsWith('Authentication Failed')) {
                statusElement.textContent = 'Authentication Failed. Retrying...';
                disconnectWebSocket();
            } else {
                // Canlı log girişi
                logEntry.textContent = data;

                // Log seviyesini (ERROR, LOGIN, vb.) renklendirmek için
                const match = data.match(/\[([A-Z_]+)\]/);
                if (match) {
                    logEntry.classList.add(match[1]);
                }

                logContainer.appendChild(logEntry);
                // En alta kaydır
                logContainer.scrollTop = logContainer.scrollHeight;
            }
        };

        socket.onclose = () => {
            statusElement.textContent = 'Disconnected';
            socket = null;
        };

        socket.onerror = (error) => {
            console.error('WebSocket Error:', error);
            statusElement.textContent = 'Connection Error';
        };

    } catch (e) {
        statusElement.textContent = `Error: ${e.message}`;
    }
}

function disconnectWebSocket() {
    if (socket) {
        socket.close();
    }
}