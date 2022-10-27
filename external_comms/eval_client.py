import base64
import json
import socket

from Crypto import Random
from Crypto.Util.Padding import pad
from Crypto.Cipher import AES

HEADER = 64
# PORT_OUT = 5050
# IP_SERVER = socket.gethostbyname(socket.gethostname())
FORMAT = 'utf-8'
# ADDR_OUT = (IP_SERVER, PORT_OUT)


class EvalClient:
    def __init__(self, eval_server_ip, eval_server_port):
        self.server_ip = eval_server_ip
        self.port_num = eval_server_port
        self.addr_out = (self.server_ip, self.port_num)
        self.SECRET_KEY = "PLSPLSPLSPLSWORK"
        self.message_dict = {}
        self.updated_state = {}
        self.client_out = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.init_socket_connection()

    def init_socket_connection(self):
        """
        This function connects the client to the eval server.
        """
        try:
            self.client_out.connect(self.addr_out)
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

    def send_encrypted_message(self):
        """
        This function takes the message which is a dictionary and converts it to JSON format which will then by
        encrypted and then sends the message through sockets.
        """
        try:
            print("before encrypt message")
            json_message = json.dumps(self.message_dict)
            encrypted_message = self.encrypt_message(json_message)
            msg_length = str(len(encrypted_message)) + "_"
            self.client_out.send(msg_length.encode(FORMAT) + encrypted_message)
            print("Sent encrypted msg")
        except Exception as err:
            print(f"Error sending encrypted message: {err}")

    def receive_game_state(self):
        try:
            print("before recv from eval server")
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
            print("recv msg from eval server")
        except Exception as err:
            print(f"Error receiving message from eval server: {err}")

    def handle_eval_server(self, new_action):
        """
        This function updates the game state and sends the encrypted JSON message.
        """
        self.message_dict = new_action
        self.send_encrypted_message()
        self.updated_state = self.receive_game_state()
        return self.updated_state
