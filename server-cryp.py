import socket
import threading
import json
import time

USER_FILE = "users.json"
PORT = 1234

clients = {}
user_status = {}

def load_users():
    try:
        with open(USER_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_users():
    with open(USER_FILE, 'w') as file:
        json.dump(user_status, file)

def write_to_chat_history(username, message, current_time):
    try:
        with open('chat_history.txt', 'a') as history_file:
            history_file.write(f"{username}> {message} - " + current_time + "\n")
    except Exception as e:
        print(f"Error writing to chat history: {e}")

def read_chat_history():
    try:
        with open('chat_history.txt', 'r') as history_file:
            return history_file.read()
    except FileNotFoundError:
        return "No chat history available."

def check_user_activity():
    while True:
        for user, status in list(user_status.items()):
            if status == "online" and time.time() - clients[user]["last_activity"] > 45:
                user_status[user] = "offline"
        save_users()
        time.sleep(5)

def check_user_available():
    while True:
        for user, status in list(user_status.items()):
            if status == "offline" and user in clients and time.time() - clients[user]["last_activity"] > 60:
                del clients[user]
                del user_status[user]
                print(f"{user} disconnected")
        save_users()
        time.sleep(5)

def handle_client(client_socket, username):
    clients[username] = {"socket": client_socket, "last_activity": time.time(), "private_with": None}
    user_status[username] = "online"
    save_users()
    print(f"{username} connected to the server")

    try:
        while True:
            message = client_socket.recv(1024).decode()
            if not message:
                break

            if clients[username]["private_with"]:
                # Handle private chat messages
                handle_private_message(client_socket, username, message)
            else:
                # Handle public chat commands and messages
                if message == "/users":
                    send_users_list(client_socket)
                elif message == "/history":
                    send_chat_history(client_socket)
                elif message.startswith("/private"):
                    private_chat(client_socket, username, message)
                elif message.startswith("/accept"):
                    accept_private_chat(client_socket, username, message)
                elif message.startswith("/reject"):
                    reject_private_chat(client_socket, username, message)
                else:
                    clients[username]["last_activity"] = time.time()
                    broadcast_message(username, message)
                    current_time = time.strftime("%H:%M:%S", time.localtime())
                    write_to_chat_history(username, message, current_time)
                    user_status[username] = "online"
                    save_users()
    except (ConnectionResetError, KeyError):
        user_status[username] = "offline"
        save_users()
        print(f"{username} disconnected")
        if username in clients:
            del clients[username]

def send_users_list(client_socket):
    users_list = json.dumps(user_status)
    client_socket.send(users_list.encode())

def send_chat_history(client_socket):
    history = read_chat_history()
    client_socket.send(history.encode())

def broadcast_message(sender, message):
    for username, client_data in clients.items():
        if username != sender:
            try:
                client_data["socket"].send(f"{sender}: {message}".encode())
            except ConnectionResetError:
                user_status[username] = "offline"
                save_users()
                print(f"{username} disconnected")

def private_chat(client_socket, username, message):
    parts = message.split()
    if len(parts) < 2:
        client_socket.send("Usage: /private <username>".encode())
        return
    target_user = parts[1]
    if target_user not in clients:
        client_socket.send(f"User {target_user} not found.".encode())
        return
    target_socket = clients[target_user]["socket"]
    client_socket.send("Requesting private chat...".encode())
    target_socket.send(f"{username} wants to start a private chat. Type /accept {username} or /reject {username}.".encode())

def accept_private_chat(client_socket, username, message):
    parts = message.split()
    if len(parts) < 2:
        client_socket.send("Usage: /accept <username>".encode())
        return
    target_user = parts[1]
    if target_user not in clients:
        client_socket.send(f"User {target_user} not found.".encode())
        return
    target_socket = clients[target_user]["socket"]
    client_socket.send("Private chat accepted.".encode())
    target_socket.send("Private chat accepted.".encode())

    clients[username]["private_with"] = target_user
    clients[target_user]["private_with"] = username

    private_chat_session(client_socket, target_socket, username, target_user)

def reject_private_chat(client_socket, username, message):
    parts = message.split()
    if len(parts) < 2:
        client_socket.send("Usage: /reject <username>".encode())
        return
    target_user = parts[1]
    if target_user not in clients:
        client_socket.send(f"User {target_user} not found.".encode())
        return
    target_socket = clients[target_user]["socket"]
    client_socket.send("Private chat rejected.".encode())
    target_socket.send("Private chat rejected.".encode())

def handle_private_message(client_socket, username, message):
    target_user = clients[username]["private_with"]
    target_socket = clients[target_user]["socket"]

    if message == "/end":
        client_socket.send("Private chat session ended.".encode())
        target_socket.send("Private chat session ended.".encode())
        clients[username]["private_with"] = None
        clients[target_user]["private_with"] = None
    else:
        target_socket.send(f"Private from {username}: {message}".encode())

def private_chat_session(client_socket, target_socket, client_username, target_username):
    client_socket.send("Private chat session started. Type /end to finish.".encode())
    target_socket.send("Private chat session started. Type /end to finish.".encode())

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('localhost', PORT))
    server.listen()
    print(f"Server is listening on localhost:{PORT}")

    activity_thread = threading.Thread(target=check_user_activity)
    activity_thread.daemon = True
    activity_thread.start()

    kick_thread = threading.Thread(target=check_user_available)
    kick_thread.daemon = True
    kick_thread.start()

    while True:
        client_socket, client_address = server.accept()
        username = client_socket.recv(1024).decode()
        thread = threading.Thread(target=handle_client, args=(client_socket, username))
        thread.start()

if __name__ == "__main__":
    main()
