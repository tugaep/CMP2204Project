import socket
import threading
import json
import time
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import scrypt
from Crypto.Random.random import randint
from Crypto.Util.Padding import pad, unpad

USER_FILE = "users.json"
PORT = 6000

clients = {}
user_status = {}

# Load or create the users file
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
            if status == "online" and time.time() - clients[user]["last_activity"] > 15:
                user_status[user] = "offline"
        save_users()
        time.sleep(5)

def check_user_available():
    while True:
        for user, status in list(user_status.items()):
            if status == "offline" and user in clients and time.time() - clients[user]["last_activity"] > 25:
                del clients[user]
                del user_status[user]
                print(f"{user} disconnected")
        save_users()
        time.sleep(5)

def handle_client(client_socket, username):
    clients[username] = {"socket": client_socket, "last_activity": time.time()}
    user_status[username] = "online"
    save_users()
    print(f"{username} connected to the server")

    try:
        while True:
            message = client_socket.recv(1024).decode()
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
            elif message.startswith("ENCRYPTED"):
                parts = message.split(" ", 2)
                target_user = parts[1]
                encrypted_msg = parts[2]
                send_encrypted_message(target_user, encrypted_msg)
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
    # Perform Diffie-Hellman key exchange
    p = 23
    g = 5
    a = randint(1, p-1)
    A = pow(g, a, p)
    client_socket.send(f"DH {p} {g} {A}".encode())

    B_message = target_socket.recv(1024).decode().split()
    if len(B_message) < 4:
        client_socket.send("Error during Diffie-Hellman key exchange.".encode())
        target_socket.send("Error during Diffie-Hellman key exchange.".encode())
        return

    B = int(B_message[3])
    shared_key_client = pow(B, a, p)

    b = randint(1, p-1)
    B = pow(g, b, p)
    target_socket.send(f"DH {p} {g} {B}".encode())

    A_message = target_socket.recv(1024).decode().split()
    if len(A_message) < 4:
        client_socket.send("Error during Diffie-Hellman key exchange.".encode())
        target_socket.send("Error during Diffie-Hellman key exchange.".encode())
        return

    A = int(A_message[3])
    shared_key_target = pow(A, b, p)

    key_client = scrypt(str(shared_key_client).encode(), salt=get_random_bytes(16), key_len=32, N=2**14, r=8, p=1)
    key_target = scrypt(str(shared_key_target).encode(), salt=get_random_bytes(16), key_len=32, N=2**14, r=8, p=1)

    clients[username]["key"] = key_client
    clients[target_user]["key"] = key_target

    private_chat_session(client_socket, target_socket, key_client, key_target)

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

def private_chat_session(client_socket, target_socket, key_client, key_target):
    def send_encrypted(socket, key, message):
        cipher = AES.new(key, AES.MODE_EAX)
        ciphertext, tag = cipher.encrypt_and_digest(pad(message.encode(), AES.block_size))
        socket.send(cipher.nonce + tag + ciphertext)

    def receive_decrypted(socket, key):
        data = socket.recv(1024)
        nonce = data[:16]
        tag = data[16:32]
        ciphertext = data[32:]
        cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
        message = unpad(cipher.decrypt_and_verify(ciphertext, tag), AES.block_size)
        return message.decode()

    client_socket.send("Private chat session started. Type /end to finish.".encode())
    target_socket.send("Private chat session started. Type /end to finish.".encode())

    while True:
        try:
            message_client = receive_decrypted(client_socket, key_client)
            if message_client == "/end":
                client_socket.send("Private chat session ended.".encode())
                target_socket.send("Private chat session ended.".encode())
                break
            send_encrypted(target_socket, key_target, message_client)

            message_target = receive_decrypted(target_socket, key_target)
            if message_target == "/end":
                client_socket.send("Private chat session ended.".encode())
                target_socket.send("Private chat session ended.".encode())
                break
            send_encrypted(client_socket, key_client, message_target)
        except Exception as e:
            print(f"Error in private chat session: {e}")
            break

def send_encrypted_message(target_user, encrypted_message):
    if target_user in clients:
        target_socket = clients[target_user]["socket"]
        target_socket.send(f"ENCRYPTED {encrypted_message}".encode())

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
        client_socket, _ = server.accept()
        username = client_socket.recv(1024).decode()
        thread = threading.Thread(target=handle_client, args=(client_socket, username))
        thread.start()

if __name__ == "__main__":
    main()