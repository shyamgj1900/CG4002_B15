import base64
import json
import socket
import threading

from Crypto import Random
from Crypto.Util.Padding import pad
from Crypto.Cipher import AES

SECRET_KEY = "PLSPLSPLSPLSWORK"
HEADER = 64
PORT_OUT = 5050
IP_SERVER = socket.gethostbyname(socket.gethostname())
FORMAT = 'utf-8'
DISCONNECT_MSG = "!DISCONNECT"
ADDR_OUT = (IP_SERVER, PORT_OUT)
ENCRYPT_BLOCK_SIZE = 16

message = {'p1': {'hp': 100, 'action': 'none', 'bullets': 6, 'grenades': 2, 'shield_time': 0, 'shield_health': 0, 'num_deaths': 0, 'num_shield': 3},
           'p2': {'hp': 100, 'action': 'none', 'bullets': 6, 'grenades': 2, 'shield_time': 0, 'shield_health': 0, 'num_deaths': 0, 'num_shield': 3}}

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


def receive_game_state():
    data = b''
    while not data.endswith(b'_'):
        _d = client_out.recv(1)
        if not _d:
            data = b''
            break
        data += _d
    data = data.decode("utf-8")
    length = int(data[:-1])
    data = b''
    while len(data) < length:
        _d = client_out.recv(length - len(data))
        if not _d:
            data = b''
            break
        data += _d
    msg = data.decode("utf8")
    return json.loads(msg)


def update_game_state(new_action):
    message["p1"]["action"] = new_action
    if new_action == "shoot":
        message["p1"]["bullets"] -= 1
        message["p2"]["hp"] -= 10
    elif new_action == "grenade":
        message["p1"]["grenades"] -= 1
        message["p2"]["hp"] -= 30
    elif new_action == "shield":
        message["p1"]["num_shield"] -= 1
    elif new_action == "reload":
        message["p1"]["bullets"] = 6

    # for key in message["p1"].keys():
    #     message["p1"][key] = new_msg["p1"][key]
    #
    # for key in message["p2"].keys():
    #     message["p2"][key] = new_msg["p2"][key]


def handle_eval_server():
    new_action = input("[Type] New Action: ")
    update_game_state(new_action)
    send_encrypted_message()
    new_msg = receive_game_state()


def send_encrypted_message():
    json_message = json.dumps(message)
    encrypted_message = encrypt_message(json_message)
    msg_length = str(len(encrypted_message)) + "_"
    client_out.send(msg_length.encode(FORMAT) + encrypted_message)


def main():
    while True:
        thread = threading.Thread(target=handle_eval_server(), args=())
        thread.start()


if __name__ == "__main__":
    main()