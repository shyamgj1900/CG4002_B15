import base64
import json
import socket
import time

from Crypto import Random
from Crypto.Util.Padding import pad
from Crypto.Cipher import AES
from player_state import PlayerStateBase
from player_state import PlayerState

HEADER = 64
PORT_OUT = 5050
IP_SERVER = socket.gethostbyname(socket.gethostname())
FORMAT = 'utf-8'
DISCONNECT_MSG = "!DISCONNECT"
ADDR_OUT = (IP_SERVER, PORT_OUT)


class EvalClient:
    def __init__(self):
        self.SECRET_KEY = "PLSPLSPLSPLSWORK"
        self.message = {}
        self.client_out = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.init_socket_connection()
        self.connected = True
        self.new_time = 0
        self.curr_time = 0
        self.shield_time = 10
        self.shield_active = False
        self.player1 = PlayerState()
        self.player2 = PlayerState()

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
            padded_raw_message = pad(msg.encode(FORMAT), AES.block_size)
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
        self.player1.update(new_action, 'none', False)
        self.player2.update('none', new_action, True)
        player1_dict = self.player1.get_dict()
        player2_dict = self.player2.get_dict()
        self.message = {'p1': player1_dict, 'p2': player2_dict}

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
