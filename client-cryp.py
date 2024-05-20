import socket
import threading
import secrets
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

SERVER = "localhost"
PORT = 1111
ADDRESS = (SERVER, PORT)

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(ADDRESS)

username = input("Enter your username: ")
client.send(username.encode())

clients = {}

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

def receive_messages():
    while True:
        try:
            data = client.recv(1024)
            if not data:
                break
            message = data.decode()
            if message.startswith("/dhkey"):
                parts = message.split()
                if len(parts) < 5:
                    print("Invalid DH key exchange message.")
                    continue
                target_user = parts[1]
                p = int(parts[2])
                g = int(parts[3])
                other_public_key = int(parts[4])

                # Generate own key pair and compute shared key
                _, _, private_key, public_key = generate_dh_keypair()
                shared_key = compute_shared_key(other_public_key, private_key, p)
                clients[target_user] = {"shared_key": shared_key, "private_with": target_user}

                print(f"Private chat session with {target_user} established.")
            elif message.startswith("Encrypted:"):
                encrypted_message = bytes.fromhex(message.split(':')[1])
                shared_key = clients[username]["shared_key"]
                decrypted_message = decrypt_message(shared_key, encrypted_message)
                print(f"Decrypted message: {decrypted_message}")
            else:
                print(message)
        except ConnectionResetError:
            print("Server closed the connection.")
            break
        except Exception as e:
            print(f"Error receiving message: {e}")

def send_messages():
    global clients
    while True:
        message = input()
        if username in clients and clients[username].get("private_with"):
            shared_key = clients[username]["shared_key"]
            encrypted_message = encrypt_message(shared_key, message)
            client.send(encrypted_message)
        else:
            client.send(message.encode())

def main():
    global clients
    clients = {username: {"private_with": None, "shared_key": None}}

    receive_thread = threading.Thread(target=receive_messages)
    receive_thread.start()

    send_thread = threading.Thread(target=send_messages)
    send_thread.start()

if __name__ == "__main__":
    main()