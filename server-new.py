import socket
import threading
import json
import os
import time

HOST = '127.0.0.1'
PORT = 1234

def load_usernames():
    try:
        with open('usernames.json', 'r') as f:
            usernames = json.load(f)
            print("Usernames loaded successfully:", usernames)
            return usernames
    except FileNotFoundError:
        print("Usernames file not found. Initializing with empty dictionary.")
        return {}
    except json.JSONDecodeError as e:
        print("Error decoding JSON:", e)
        print("Initializing with empty dictionary.")
        return {}

def save_usernames(usernames):
    try:
        with open('usernames.json', 'w') as f:
            json.dump(usernames, f)
    except Exception as e:
        print(f"Error saving usernames: {e}")

# Function to set a user's status as "online"
def set_user_online(usernames, username):
    usernames[username] = {"status": "online"}

# Function to set a user's status as "offline"
def set_user_offline(usernames, username):
    if username in usernames:
        usernames[username]["status"] = "offline"

# Function to update a user's last seen time
def update_last_seen(usernames, username):
    usernames[username]["last_seen"] = time.time()

def write_to_chat_history(username, message, current_time):
    try:
        with open('chat_history.txt', 'a') as history_file:
            history_file.write(f"{username}> {message} - " + current_time + "\n") 
    except Exception as e:
        print(f"Error writing to chat history: {e}")

def broadcast(message):
    with lock:
        print(message)
        for client in clients:
            try:
                client.send(message.encode())
            except:
                clients.remove(client)

def handle_client(conn, addr):
    conn.send("Enter your username: ".encode())
    username = conn.recv(1024).decode().strip()
    broadcast(f"{username} has joined the chat.")
    
    
    # Save the username to usernames.json and set status as "online"
    with lock:
        usernames = load_usernames()
        set_user_online(usernames, username)
        update_last_seen(usernames, username)
        save_usernames(usernames)
    
    
    
    try:
        while True:
            message = conn.recv(1024).decode()
            t = time.localtime()
            current_time_str = time.strftime("%H:%M:%S", t)
            
            if message:
                last_message_time = time.time()  # Update last message time
                print("Last message time updated")
                # Update user's online status
                set_user_online(usernames, username)
                update_last_seen(usernames, username)
                save_usernames(usernames)
            
            if not message:
                break  # Exit loop if client sends empty message (indicating disconnect)
            
            write_to_chat_history(username, message, current_time_str)  # Write to chat history file
            broadcast(f"{username} > {message}")
            
                    
            
            # Check for offline users (20 seconds)
            while True:
                current_time = time.time()
                offline_users_10 = [user for user, data in usernames.items() if data["status"] == "online" and (current_time - data["last_seen"]) > 10]
                for user in offline_users_10:
                    print("User", user, "is considered offline (10s).")
                    # Update status to "offline"
                    set_user_offline(usernames, user)
                    save_usernames(usernames)
                offline_users_20 = [user for user, data in usernames.items() if data["status"] == "offline" and (current_time  - data["last_seen"]) > 20]
                for user in offline_users_20:
                    print("User", user, "is kicked (20s).")
                    # Update status to "offline"
                    del usernames[user]
                    save_usernames(usernames)
                    broadcast(f"{username} has kicked from the chat.")
                    
                    for client in clients:
                        if client.getpeername()[1] == addr[1]:
                            with lock:
                                clients.remove(client)
                            client.send("You have been kicked out of the server due to inactivity.".encode())
                            client.close()
                            break
                    
                break
                
           
            
                
    except Exception as e:
        print(f"[EXCEPTION] {e}")
   


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
clients = []
lock = threading.Lock()

def start_server():
    server.listen()
    print(f"[LISTENING] Server is listening on {HOST}:{PORT}")
    while True:
        conn, addr = server.accept()
        with lock:
            clients.append(conn)
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.activeCount() - 1}")

start_server()
