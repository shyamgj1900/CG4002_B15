import base64
import json
import socket

from Crypto import Random
from Crypto.Util.Padding import pad
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

SECRET_KEY = "PLSPLSPLSPLSWORK"
HEADER = 64
PORT_OUT = 5050
IP_SERVER = socket.gethostbyname(socket.gethostname())
FORMAT = 'utf-8'
DISCONNECT_MSG = "!DISCONNECT"
ADDR_OUT = (IP_SERVER, PORT_OUT)
ENCRYPT_BLOCK_SIZE = 16

message = {'p1': {'hp': 100, 'action': 'shoot', 'bullets': 5, 'grenades': 2, 'shield_time': 0, 'shield_health': 0, 'num_deaths': 0, 'num_shield': 3},
           'p2': {'hp': 90, 'action': 'none', 'bullets': 6, 'grenades': 2, 'shield_time': 0, 'shield_health': 0, 'num_deaths': 0, 'num_shield': 3}}

try:
    client_out = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_out.connect(ADDR_OUT)
except socket.error as err:
    print("Socket error: " + str(err))


def encrypt_message(msg):
    padded_raw_message = pad(msg.encode(FORMAT), 16)
    iv = Random.new().read(AES.block_size)
    secret_key = bytes(str(SECRET_KEY), encoding="utf8")
    cipher = AES.new(secret_key, AES.MODE_CBC, iv)
    encrypted_message = base64.b64encode(iv + cipher.encrypt(padded_raw_message))
    return encrypted_message


def decrypt_message(cipher_text):
    decoded_message = base64.b64decode(cipher_text)  # Decode message from base64 to bytes
    iv = decoded_message[:AES.block_size]  # Get IV value
    secret_key = bytes(str(SECRET_KEY), encoding="utf8")  # Convert secret key to bytes

    cipher = AES.new(secret_key, AES.MODE_CBC, iv)  # Create new AES cipher object

    decrypted_message = cipher.decrypt(decoded_message[AES.block_size:])  # Perform decryption
    decrypted_message = unpad(decrypted_message, AES.block_size)
    decrypted_message = decrypted_message.decode('utf8')  # Decode bytes into utf-8

    ret = json.loads(decrypted_message)
    return ret


def handle_eval_server():
    send_encrypted_message()
    msg = client_out.recv(2048).decode(FORMAT)
    print("Received msg: " + msg)


def send_encrypted_message():
    json_message = json.dumps(message)
    encrypted_message = encrypt_message(json_message)
    msg_length = str(len(encrypted_message)) + "_"
    client_out.send(msg_length.encode(FORMAT) + encrypted_message)


def main():
    while True:
        handle_eval_server()


if __name__ == "__main__":
    main()
