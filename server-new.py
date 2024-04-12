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
    except FileNotFoundError:
        usernames = []
        print("Usernames file not found. Initializing with empty dictionary.")
    except json.JSONDecodeError as e:
        print("Error decoding JSON:", e)
        usernames = []
    return usernames
def save_usernames(usernames):
    try:
        with open('usernames.json', 'w') as f:
            i = json.dump(usernames, f)
            f.write(str(i))
    except Exception as e:
        print(f"Error saving usernames: {e}")

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

    # Save the username to usernames.json
    with lock:
        
        load_usernames()
        usernames.append(str(username))
        save_usernames(usernames)

    try:
        while True:
            message = conn.recv(1024).decode()
            t = time.localtime()
            current_time = time.strftime("%H:%M:%S", t)
            if not message:
                break  # Exit loop if client sends empty message (indicating disconnect)
            
            write_to_chat_history(username, message, current_time)  # Write to chat history file
            broadcast(f"{username} > {message}")
    except Exception as e:
        print(f"[EXCEPTION] {e}")
    finally:
        broadcast(f"{username} has left the chat.")
        with lock:
            clients.remove(conn)
        conn.close()





server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
clients = []
lock = threading.Lock()

usernames = load_usernames() 

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
