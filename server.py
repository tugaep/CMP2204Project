import socket
import threading
import json
import time
import secrets
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

USER_FILE = "users.json"
PORT = 6000

clients = {}
user_status = {}
def generate_dh_keypair():
    p = int("FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
            "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
            "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
            "E485B576625E7EC6F44C42E9A63A36210000000000090563", 16)
    g = 2
    private_key = secrets.randbelow(p)
    public_key = pow(g, private_key, p)
    return p, g, private_key, public_key

def compute_shared_key(other_public_key, private_key, p):
    shared_key = pow(other_public_key, private_key, p)
    return hashlib.sha256(str(shared_key).encode()).digest()

def encrypt_message(key, message):
    cipher = AES.new(key, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(message.encode(), AES.block_size))
    return cipher.iv + ct_bytes

def decrypt_message(key, message):
    iv = message[:AES.block_size]
    ct = message[AES.block_size:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(ct), AES.block_size).decode()

def handle_dh_key_exchange(client_socket, username, message):
    parts = message.split()
    if len(parts) < 5:
        client_socket.send("Invalid DH key exchange message.".encode())
        return
    target_user = parts[1]
    p = int(parts[2])
    g = int(parts[3])
    other_public_key = int(parts[4])

    if target_user not in clients:
        client_socket.send(f"User {target_user} not found.".encode())
        return

    private_key = clients[username]["dh_private_key"]
    shared_key = compute_shared_key(other_public_key, private_key, p)
    clients[username]["shared_key"] = shared_key

    target_socket = clients[target_user]["socket"]
    target_socket.send(f"/dhkey {username} {p} {g} {clients[username]['dh_public_key']}".encode())

    client_socket.send("Private chat session established. Type /end to finish.".encode())
    target_socket.send("Private chat session established. Type /end to finish.".encode())

    clients[username]["private_with"] = target_user
    clients[target_user]["private_with"] = username

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
            if status == "online" and time.time() - clients[user]["last_activity"] > 10:
                user_status[user] = "away"
        save_users()
        time.sleep(5)

def check_user_available():
    while True:
        for user, status in list(user_status.items()):
            if status == "away" and user in clients and time.time() - clients[user]["last_activity"] > 900:
                del clients[user]
                del user_status[user]
                print(f"{user} disconnected")
        save_users()
        time.sleep(5)

def handle_client(client_socket, username):
    clients[username] = {"socket": client_socket, "last_activity": time.time(), "private_with": None}
    user_status[username] = "online"
    save_users()
    broadcast_message("SERVER", f"{username} connected to the server" )
    print(f"{username} connected to the server")

    try:
        while True:
            message = client_socket.recv(1024)
            if not message:
                break
            if isinstance(message, bytes):
                message = message.decode()

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
        user_status[username] = "away"
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
                user_status[username] = "away"
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
    p, g, private_key, public_key = generate_dh_keypair()
    clients[username]["dh_private_key"] = private_key
    clients[username]["dh_public_key"] = public_key
    private_chat_session(client_socket, target_socket, username, target_user)
    target_socket.send(f"/dhkey {username} {p} {g} {public_key}".encode())

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
        shared_key = clients[username].get("shared_key")
        if shared_key:
            encrypted_message = encrypt_message(shared_key, message)
            print(f'An encrypted message "{encrypted_message.hex()}" has been sent to {target_user} from {username}!')
            target_socket.send(f"Encrypted: {encrypted_message.hex()}".encode())
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
