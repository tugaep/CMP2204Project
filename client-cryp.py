import socket
import threading

SERVER = "localhost"
PORT = 1234
ADDRESS = (SERVER, PORT)

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(ADDRESS)

username = input("Enter your username: ")
client.send(username.encode())

def receive_messages():
    while True:
        try:
            data = client.recv(1024)
            if not data:
                break
            message = data.decode()
            print(message)
        except ConnectionResetError:
            print("Server closed the connection.")
            break
        except Exception as e:
            print(f"Error receiving message: {e}")

def send_messages():
    while True:
        message = input()
        client.send(message.encode())

def main():
    receive_thread = threading.Thread(target=receive_messages)
    receive_thread.start()

    send_thread = threading.Thread(target=send_messages)
    send_thread.start()

if __name__ == "__main__":
    main()
