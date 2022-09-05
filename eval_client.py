import base64
import json
import socket
import threading
import time

from Crypto import Random
from Crypto.Util.Padding import pad
from Crypto.Cipher import AES

HEADER = 64
PORT_OUT = 5050
IP_SERVER = socket.gethostbyname(socket.gethostname())
FORMAT = 'utf-8'
DISCONNECT_MSG = "!DISCONNECT"
ADDR_OUT = (IP_SERVER, PORT_OUT)


class EvalClient(threading.Thread):
    def __init__(self):
        super(EvalClient, self).__init__()

        self.SECRET_KEY = "PLSPLSPLSPLSWORK"
        self.message = {
            'p1': {'hp': 100, 'action': 'none', 'bullets': 6, 'grenades': 2, 'shield_time': 0, 'shield_health': 0,
                   'num_deaths': 0, 'num_shield': 3},
            'p2': {'hp': 100, 'action': 'none', 'bullets': 6, 'grenades': 2, 'shield_time': 0, 'shield_health': 0,
                   'num_deaths': 0, 'num_shield': 3}}
        self.client_out = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.init_socket_connection()
        self.connected = True
        self.new_time = 0
        self.curr_time = 0
        self.shield_time = 10
        self.shield_active = False

    def update_shield_time(self):
        """
        This function updates the shield time when it is active.
        """
        self.curr_time = time.time() - self.new_time
        self.shield_time -= self.curr_time

    def init_socket_connection(self):
        """
        This function connects the client to the eval server.
        """
        try:
            self.client_out.connect(ADDR_OUT)
        except socket.error as err:
            print("Socket error: " + str(err))

    def encrypt_message(self, msg):
        """
        This function encrypts the response message which is to be sent to the Ultra96 using the secret encryption key.
        """
        try:
            padded_raw_message = pad(msg.encode(FORMAT), 16)
            iv = Random.new().read(AES.block_size)
            secret_key = bytes(str(self.SECRET_KEY), encoding="utf8")
            cipher = AES.new(secret_key, AES.MODE_CBC, iv)
            encrypted_message = base64.b64encode(iv + cipher.encrypt(padded_raw_message))
            return encrypted_message
        except Exception as e:
            print(f"Could not encrypt message due to {e}")

    def update_game_state(self, new_action):
        """
        This function updates the players game state based on the action it has received from the client side. (For now
        this function only updates game state based on 1 player mode).
        """
        self.message["p1"]["action"] = new_action
        if new_action == "shoot" and self.message["p1"]["bullets"] > 0:
            self.message["p1"]["bullets"] -= 1
            self.message["p2"]["hp"] -= 10
            if self.message["p2"]["hp"] <= 0:
                self.message["p2"]["hp"] = 100
                self.message["p2"]["num_deaths"] += 1
        elif new_action == "grenade" and self.message["p1"]["grenades"] > 0:
            self.message["p1"]["grenades"] -= 1
            self.message["p2"]["hp"] -= 30
            if self.message["p2"]["hp"] <= 0:
                self.message["p2"]["hp"] = 100
                self.message["p2"]["num_deaths"] += 1
        elif new_action == "shield" and self.message["p1"]["num_shield"] > 0 and self.shield_active is False:
            self.new_time = time.time()
            self.message["p1"]["num_shield"] -= 1
            self.message["p1"]["shield_health"] = 30
            self.shield_active = True
        elif new_action == "reload" and self.message["p1"]["bullets"] == 0:
            self.message["p1"]["bullets"] = 6

        if self.shield_active is True:
            self.update_shield_time()
            if self.shield_time > 0:
                self.message["p1"]["shield_time"] = self.shield_time
            elif self.shield_time <= 0:
                self.shield_active = False
                self.message["p1"]["shield_time"] = 0
                self.message["p1"]["shield_health"] = 0

    def send_encrypted_message(self):
        """
        This function takes the message which is a dictionary and converts it to JSON format which will then by
        encrypted and then sends the message through sockets.
        """
        try:
            json_message = json.dumps(self.message)
            encrypted_message = self.encrypt_message(json_message)
            msg_length = str(len(encrypted_message)) + "_"
            self.client_out.send(msg_length.encode(FORMAT) + encrypted_message)
        except Exception as err:
            print(f"Error sending encrypted message: {err}")

    def receive_game_state(self):
        try:
            data = b''
            while not data.endswith(b'_'):
                _d = self.client_out.recv(1)
                if not _d:
                    data = b''
                    break
                data += _d
            data = data.decode("utf-8")
            length = int(data[:-1])
            data = b''
            while len(data) < length:
                _d = self.client_out.recv(length - len(data))
                if not _d:
                    data = b''
                    break
                data += _d
            msg = data.decode("utf8")
            return json.loads(msg)
        except Exception as err:
            print(f"Error receiving message from eval server: {err}")

    def handle_eval_server(self, new_action):
        """
        This function updates the game state and sends the encrypted JSON message.
        """
        self.update_game_state(new_action)
        self.send_encrypted_message()
