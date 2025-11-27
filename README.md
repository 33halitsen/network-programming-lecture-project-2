Multi-User Chat System
 Project OverviewThis project implements a robust, multi-threaded chat system in Python, designed to demonstrate socket programming, concurrency, and real-time communication protocols. It features a central server that handles multiple client connections, enforces secure authentication, manages private messaging, and provides a live web-based monitoring console via WebSockets.
 
Key Features
 Multi-Threaded Server: Handles multiple simultaneous client connections using threading.
 
 Secure Authentication: Persistent user registration and login system with password hashing (SHA-256).
 
 Real-Time Messaging: Supports public broadcasting and private messaging (/msg).
 
 Chat Focus Mode: dedicated "focus" mode for private conversations to improve user experience.
 
 Rate Limiting: Spam protection mechanism to block users sending messages too quickly.Graceful Exit: Clean disconnection handling that updates active user lists for all clients immediately.
 
 Web Monitor: Integrated HTTP and WebSocket server to view live chat logs and system events in a web browser.
 
 Symmetric Logging: Detailed logs for every conversation, stored in both sender and recipient directories.
 
 
Project StructureThe project follows a modular architecture for scalability and maintainability:
 
MultiUserChat/
├── chat_server.py           # Entry point for the Chat Server
├── chat_client.py           # Entry point for the Chat Client
├── core/                    # Core logic modules
│   ├── server_classes.py    # ChatServer, ClientHandler, WebServerThread classes
│   ├── client_classes.py    # ChatClient, MessageListener classes
│   ├── protocol.py          # Custom MessageProtocol for data exchange
│   └── utils.py             # Helper classes: Logger, UserDatabase, RateLimiter
├── static/                  # Web assets for the monitoring console
│   ├── index.html           # Web interface for live logs
│   └── websocket_client.js  # WebSocket logic for the browser
├── log/                     # Generated log files
│   ├── system_events.log    # General server events
│   └── user_data/           # User-specific chat logs
├── user_db.json             # Persistent user credential database
└── README.md                # Project documentation

Installation & Setup
    Prerequisites
        Python 3.x installed on your system.
        Basic knowledge of terminal/command line usage.
        
    Dependencies
    Install the required libraries using pip

Testing Guide: Simulating Multiple Users
To test the chat system effectively on a single machine, we will create three separate virtual environments in your computer's root (home) directory. This simulates independent machines for the Server, Client 1, and Client 2.

Step 1: Create Virtual Environments (In Root Directory)
Open your terminal (ensure you are in your home directory ~ or %USERPROFILE%) and run:


# Create environment for the Server
python3 -m venv server_env

# Create environment for Client 1
python3 -m venv client1_env

# Create environment for Client 2
python3 -m venv client2_env

Step 2: Run the Server

Open a new terminal window.Activate the server environment and navigate to the project folder:

# Activate Environment (macOS/Linux)
source ~/server_env/bin/activate
# OR Windows: server_env\Scripts\activate

# Navigate to Project
cd /path/to/your/MultiUserChat

# Install Dependencies (First time only)
pip install websockets

# Start Server
python chat_server.py
You should see: [SERVER]: Server listening on 0.0.0.0:9999

Step 3: Run Client 1

Open a second terminal window.

Activate the first client environment:
# Activate Environment
source ~/client1_env/bin/activate

# Navigate to Project
cd /path/to/your/MultiUserChat

# Start Client
python chat_client.py
Login/Register: Follow the prompts.

Example: Enter halit 123 to register or login as 'halit'.


Step 4: Run Client 2

Open a third terminal window.
Activate the second client environment:
# Activate Environment
source ~/client2_env/bin/activate

# Navigate to Project
cd /path/to/your/MultiUserChat

# Start Client
python chat_client.py
Login/Register: Enter a different nickname (e.g., bassar 456).

Usage & CommandsOnce 

connected, you can use the following commands in the chat client:

Command,Description,Example
Public Message, Send a message to everyone., Hello World
/list, View a list of currently active users., /list
/msg <user> <text>, Send a private message to a specific user., /msg bassar Secret message
/msg <user>, Focus Mode: Lock chat to a specific user. Future messages go to them automatically., /msg bassar
/msg public, Exit Focus Mode and return to public chat., /msg public
/exit, Disconnect gracefully from the server., /exit

 Web Monitoring Console
 
 To monitor the server logs in real-time:
 
 Open your web browser.
 Go to: http://localhost:8000
 Enter the Admin Password (Default: admin123).
 Click Connect. You will see live logs of all chat activity!
 
 Technical Highlights
 
 Protocol Design: A custom MessageProtocol handles encoding/decoding of JSON data over TCP sockets, supporting various message types (AUTH, PUBLIC, PRIVATE, SYSTEM).
 
 Concurrency: The server uses threading for ClientHandlers and asyncio for the WebSocket server, ensuring smooth parallel operation.
 
 Safety: Thread-safe operations are implemented for writing logs and managing active user lists.State Management: The client maintains its own state (connection status, authentication, chat focus) to provide a seamless CLI experience.
 
 Project Owner: Halit ŞEN