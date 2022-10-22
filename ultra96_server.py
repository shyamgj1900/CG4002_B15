import sys
import threading
import zmq
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from queue import Queue
import time

from hardware_ai.pynq_overlay import Process
# from external_comms.test_ai import TestAI
from external_comms.game_state import GameState
from external_comms.eval_client import EvalClient
from external_comms.visualizer_broadcast import VisualizerBroadcast

game_manager = GameState()
player1_action_q = Queue()
player2_action_q = Queue()
player1_detected_action = ""
player2_detected_action = ""
eval_message_event = threading.Event()
visualizer_message_event = threading.Event()
detect_action_event = threading.Event()
exit_event = threading.Event()

PORT_OUT = 0
IP_SERVER = ""


class DetectActionForP1(threading.Thread):
    def __init__(self):
        super(DetectActionForP1, self).__init__()
        self.send_to_ai = Process()
        # self.send_to_ai = TestAI()
        self.turn_counter_p1 = 0

    def get_action_player1(self, data):
        if data[0] == "G1":
            action = "shoot"
            self.turn_counter_p1 += 1
            print(f"Detected action for player 1: {action}")
            print(f"Turn count for player 1: {self.turn_counter_p1}")
            return action
        elif data[0] == "W1":
            action = self.send_to_ai.process(data)
            print(f"Player 1 detected action: {action}")
            if action == "logout" and self.turn_counter_p1 > 19:
                print("Disconnecting BYE.....")
                exit_event.set()
            if action != "":
                self.turn_counter_p1 += 1
                print(f"Detected action for player 1: {action}")
                print(f"Turn count for player 1: {self.turn_counter_p1}")
                return action
            elif action == "":
                return ""
        return

    def run(self):
        global player1_detected_action
        while not exit_event.is_set():
            while not player1_action_q.empty():
                data = player1_action_q.get()
                # print(f"In run player 1: {action}")
                action = self.get_action_player1(data)
                if action != "":
                    player1_detected_action = action


class DetectActionForP2(threading.Thread):
    def __init__(self):
        super(DetectActionForP2, self).__init__()
        self.send_to_ai = Process()
        # self.send_to_ai = TestAI()
        self.turn_counter_p2 = 0

    def get_action_player2(self, data):
        if data[0] == "G2":
            action = "shoot"
            self.turn_counter_p2 += 1
            print(f"Detected action for Player 2: {action}")
            print(f"Turn count for player 2: {self.turn_counter_p2}")
            return action
        elif data[0] == "W2":
            action = self.send_to_ai.process(data)
            print(f"Player 2 detected action: {action}")
            if action == "logout" and self.turn_counter_p2 > 19:
                print("Disconnecting BYE.....")
                exit_event.set()
            if action != "":
                self.turn_counter_p2 += 1
                print(f"Detected action for Player 2: {action}")
                print(f"Turn count for player 2: {self.turn_counter_p2}")
                return action
            elif action == "":
                return ""
        return

    def run(self):
        global player2_detected_action
        while not exit_event.is_set():
            while not player2_action_q.empty():
                data = player2_action_q.get()
                # print(f"In run player 2: {action}")
                action = self.get_action_player2(data)
                if action != "":
                    player2_detected_action = action


class Ultra96Server(threading.Thread):
    def __init__(self):
        super(Ultra96Server, self).__init__()
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.raw_data = ""

    def init_socket_connection(self):
        """
        This function initialises the socket connection.
        """
        try:
            print("Establishing connection through port 5550")
            self.socket.bind("tcp://*:5550")
        except Exception as e:
            print(f"Socket err: {e}")

    def receive_message_from_laptop(self):
        """
        This function receives a message from the laptop client through message queues and sends an ACK message back to
        the laptop client.
        """
        global player1_action_q, player2_action_q
        try:
            padded_raw_data = self.socket.recv()
            self.raw_data = unpad(padded_raw_data, AES.block_size)
            self.raw_data = self.raw_data.decode("utf8")
            self.raw_data = json.loads(self.raw_data)
            if self.raw_data[0] == 'G1' or self.raw_data[0] == 'W1' or self.raw_data[0] == 'V1':
                player1_action_q.put(self.raw_data)
            elif self.raw_data[0] == 'G2' or self.raw_data[0] == 'W2' or self.raw_data[0] == 'V2':
                player2_action_q.put(self.raw_data)
            self.socket.send(b"ACK")
        except Exception as e:
            print(f"Error receiving message: {e}")

    def run(self):
        """
        This is the main thread for the Ultra96 server.
        """
        self.init_socket_connection()
        while not exit_event.is_set():
            self.receive_message_from_laptop()


class BroadcastMessage(threading.Thread):
    def __init__(self):
        super(BroadcastMessage, self).__init__()
        self.comm_eval_server = CommWithEvalServer()
        self.comm_visualizer = CommWithVisualizer()

    def send_message(self):
        global game_manager, player1_detected_action, player2_detected_action
        game_manager.detected_game_state(player1_detected_action, player2_detected_action)
        self.comm_eval_server.send_message_to_eval_server()
        self.comm_visualizer.send_message_to_visualizer()
        player1_detected_action = ""
        player2_detected_action = ""

    def run(self):
        while not exit_event.is_set():
            if player1_detected_action != "" and player2_detected_action != "":
                self.send_message()


class CommWithEvalServer:
    def __init__(self):
        self.eval_client = EvalClient(IP_SERVER, PORT_OUT)
        self.updated_state = {}

    def send_message_to_eval_server(self):
        global game_manager
        self.updated_state = self.eval_client.handle_eval_server(game_manager.get_dict())
        game_manager.update_game_state(self.updated_state)


class CommWithVisualizer:
    def __init__(self):
        self.visualizer_publish = VisualizerBroadcast()

    def send_message_to_visualizer(self):
        self.visualizer_publish.publish_message(json.dumps(game_manager.get_dict()))


def main():
    global PORT_OUT, IP_SERVER
    IP_SERVER = sys.argv[1]
    PORT_OUT = sys.argv[2]
    PORT_OUT = int(PORT_OUT)
    u96_server = Ultra96Server()
    detect_action_for_p1 = DetectActionForP1()
    detect_action_for_p2 = DetectActionForP2()
    u96_server.start()
    detect_action_for_p1.start()
    detect_action_for_p2.start()


if __name__ == "__main__":
    main()

