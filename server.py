import socket
import threading
import json
import time


USER_FILE = "users.json"

PORT = 1234

clients = {}
# Kullanıcılar ve online/offline durumu
user_status = {}


def write_to_chat_history(username, message, current_time):
    try:
        with open('chat_history.txt', 'a') as history_file:
            history_file.write(f"{username}> {message} - " + current_time + "\n") 
    except Exception as e:
        print(f"Error writing to chat history: {e}")
def load_users():
    try:
        with open(USER_FILE, 'r') as file:
            return json.load(file)
            
    except FileNotFoundError:
        return {}
        


def save_users():
    with open(USER_FILE, 'w') as file:
        json.dump(user_status, file)

# Bağlı olan kullanıcıların sürekli izlenmesi
def check_user_activity():
    while True:
        for user, status in user_status.items():
            if status == "online":
                # Check if client sent a message in the last 15 seconds
                if time.time() - clients[user]["last_activity"] > 15:
                    user_status[user] = "offline"
        save_users()
        time.sleep(5)  # Check every 5 seconds

def check_user_available():
    while True:
        for user, status in user_status.items():
            if status == "offline":
                if time.time() - clients[user]["last_activity"] > 25:

                    #JSON dosyasından user key'i silinecek.
                    data = load_users()
                    del data[user]
                    del clients[user]
                    print(f"{user} disconnected")
                    
                    
        save_users()
        time.sleep(5)






def handle_client(client_socket, username):
    clients[username] = {"socket": client_socket, "last_activity": time.time()}
    user_status[username] = "online"
    save_users()
    print(f"{username} connected to the server")

    while True:
        try:
            message = client_socket.recv(1024).decode()

            if message == "/users":
                send_users_list(client_socket)   
                         
            else:
                # Update last activity time
                clients[username]["last_activity"] = time.time()
                # Mesajı diğer istemcilere gönderme
                broadcast_message(username, message)
                t = time.localtime()
                current_time = time.strftime("%H:%M:%S", t)
                write_to_chat_history(username, message, current_time)
                user_status[username] = "online"
                save_users()
        except ConnectionResetError:
            user_status[username] = "offline"
            save_users()
            print(f"{username} disconnected")
            del clients[username]
            break

# Tüm kullanıcı adlarını ve durumlarını gönderme
def send_user_info(client_socket):
    user_info = json.dumps(user_status)
    client_socket.send(user_info.encode())

# Tüm kullanıcı adlarını gönderme
def send_usernames(client_socket):
    usernames = "\n".join(user_status.keys())
    client_socket.send(usernames.encode())

# JSON dosyasındaki kullanıcıları ve durumlarını gönderme
def send_users_list(client_socket):
    users_list = json.dumps(user_status)
    client_socket.send(users_list.encode())

# Mesajı diğer istemcilere gönderme
def broadcast_message(sender, message):
    for username, client_data in clients.items():
        if username != sender:
            try:
                client_socket = client_data["socket"]
                client_socket.send(f"{sender}: {message}".encode())
                print(message)
            except ConnectionResetError:
                del users
                del clients[username]
                user_status[username] = "offline"
                save_users()
                print(f"{username} disconnected")

# Ana program akışı
def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('localhost', PORT))
    server.listen()

    print(f"Server is listening on localhost:{PORT}")
    

    
    
    # Kullanıcı aktivitelerini kontrol etmek için bir thread oluştur
    activity_thread = threading.Thread(target=check_user_activity)
    activity_thread.daemon = True
    activity_thread.start()

    #Kullanıcı kickleme için thread
    kick_thread = threading.Thread(target=check_user_available)
    kick_thread.daemon = True
    kick_thread.start()


    while True:
        client_socket, _ = server.accept()
        username = client_socket.recv(1024).decode()
        thread = threading.Thread(target=handle_client, args=(client_socket, username))
        thread.start()


main()
