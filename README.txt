# P2P Chat Project

## Description
This project implements a simple chat application using Python sockets. It consists of a server (`server-cryp.py`) and a client (`client-cryp.py`) allowing users to communicate with each other in real-time.

## Features
- Real-time messaging between clients.
- Basic command-line interface.
- Support for multiple clients connecting to the server simultaneously.
- Real time status of users (online/offline).
- Private chat option between users
- Encrypted message in private sessions.

## Installation
1. Clone the repository: `git clone https://github.com/yourusername/NetworkProject.git`
2. Navigate to the project directory: `cd chat-project`
3. Install dependencies (if any): `pip install -r requirements.txt`

## Usage
### Server
1. Run the server: `python server.py`
2. The server will start listening for connections on a specified port.
3. Once the server is running, clients can connect to it.

### Client
1. Run the client: `python client-cryp.py`
2. The client will prompt you to enter your username.
4. Once connected, you can start sending and receiving messages.

## Usage Example
1. Start the server:
2. Start a client and connect to the server:
3. Another client connects and sends a message:
4. Messages are exchanged between clients and displayed on the server terminal.

## Commands
1. /users (type to see users and their status)
2. /private username (type to send private chat request to the spesified user)
3. /accept or /reject (accept or reject the private chat request)
4. /end (type to end the private chat session)

# P2P Chat Project