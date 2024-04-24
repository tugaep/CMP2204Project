import socket
import threading
import sys
import json


SERVER = "localhost" 
PORT = 1234
# Bağlanılacak sunucu adresi
ADDRESS = (SERVER, PORT)


client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(ADDRESS)


username = input("Enter your username: ")
client.send(username.encode())


def receive_messages():
    while True:
        try:
            message = client.recv(1024).decode()
            print(message)
        except ConnectionResetError:
            print("Server closed the connection.")
            break

# Sunucudan gelen kullanıcı listesi ve durumlarını al
def receive_users_list():
    while True:
        try:
            users_info = client.recv(1024).decode()
            users_dict = json.loads(users_info)
            print("Users online and their status:")
            for user, status in users_dict.items():
                print(f"{user}: {status}")
        except ConnectionResetError:
            print("Server closed the connection.")
            break

# Kullanıcıdan gelen mesajları sunucuya gönder
def send_messages():
    while True:
        message = input()
        if message == "/users":
            client.send(message.encode())
            receive_users_list()
        else:
            client.send(message.encode())

# Ana program akışı
def main():
    # İstemciye gelen mesajları dinlemek için bir thread
    receive_thread = threading.Thread(target=receive_messages)
    receive_thread.start()

    # Kullanıcıdan mesaj almak için bir thread
    send_thread = threading.Thread(target=send_messages)
    send_thread.start()

if __name__ == "__main__":
    main()
