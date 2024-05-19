import socket
import threading
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import scrypt
from Crypto.Random.random import randint
from Crypto.Util.Padding import pad, unpad

SERVER = "localhost"
PORT = 6000
ADDRESS = (SERVER, PORT)

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(ADDRESS)

username = input("Enter your username: ")
client.send(username.encode())

shared_key = None

def receive_messages():
    global shared_key
    while True:
        try:
            data = client.recv(1024)
            if not data:
                break
            message = data.decode()
            if message.startswith("DH"):
                handle_diffie_hellman(message)
            elif shared_key and message.startswith("ENCRYPTED"):
                decrypted_message = decrypt_message(message[9:])
                print(f"Private: {decrypted_message}")
            else:
                print(message)
        except ConnectionResetError:
            print("Server closed the connection.")
            break

def send_messages():
    global shared_key
    while True:
        message = input()
        if message == "/users":
            client.send(message.encode())
        elif message == "/history":
            client.send(message.encode())
        elif message.startswith("/private"):
            client.send(message.encode())
            print(client.recv(1024).decode())
        elif message.startswith("/accept") or message.startswith("/reject"):
            client.send(message.encode())
        elif message == "/end":
            client.send(message.encode())
            shared_key = None  # Clear the shared key after ending private chat
        else:
            if shared_key:
                encrypted_message = encrypt_message(message)
                client.send(f"ENCRYPTED {username} {encrypted_message}".encode())
            else:
                client.send(message.encode())

def handle_diffie_hellman(message):
    global shared_key
    parts = message.split()
    p = int(parts[1])
    g = int(parts[2])
    A = int(parts[3])
    b = randint(1, p-1)
    B = pow(g, b, p)
    client.send(f"DH {p} {g} {B}".encode())
    shared_key = pow(A, b, p)
    key = scrypt(str(shared_key).encode(), salt=get_random_bytes(16), key_len=32, N=2**14, r=8, p=1)
    shared_key = key
    print("Shared key established.")

def encrypt_message(message):
    cipher = AES.new(shared_key, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(pad(message.encode(), AES.block_size))
    return (cipher.nonce + tag + ciphertext).hex()

def decrypt_message(message):
    data = bytes.fromhex(message)
    nonce = data[:16]
    tag = data[16:32]
    ciphertext = data[32:]
    cipher = AES.new(shared_key, AES.MODE_EAX, nonce=nonce)
    plaintext = unpad(cipher.decrypt_and_verify(ciphertext, tag), AES.block_size)
    return plaintext.decode()

def main():
    receive_thread = threading.Thread(target=receive_messages)
    receive_thread.start()

    send_thread = threading.Thread(target=send_messages)
    send_thread.start()

if __name__ == "__main__":
    main()