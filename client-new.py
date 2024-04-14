import socket
import threading

SERVER = '127.0.0.1'
PORT = 1234

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((SERVER, PORT))



def receive_messages(client_socket):
    while True:
        try:
            message = client_socket.recv(1024).decode()
            if message:
                print(message)
        except Exception as e:
            print("[EXCEPTION]", e)
            break

receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
receive_thread.start()

while True:
    message = input()
    if message.lower() == 'exit':
        break
    client_socket.send(message.encode())

client_socket.close()
