import sys
import threading
import zmq
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from queue import Queue
import time

# from hardware_ai.pynq_overlay import Process
from external_comms.test_ai import TestAI
from external_comms.game_state import GameState
from external_comms.eval_client import EvalClient
from external_comms.visualizer_broadcast import VisualizerBroadcast

game_manager = GameState()
player1_action_q = Queue()
player2_action_q = Queue()
received_raw_data = ""
player1_detected_action = ""
player2_detected_action = ""
eval_message_event = threading.Event()
visualizer_message_event = threading.Event()
detect_action_event = threading.Event()
exit_event = threading.Event()
q = Queue()

PORT_OUT = 0
IP_SERVER = ""


class DetectActionFromAI(threading.Thread):
    def __init__(self):
        super(DetectActionFromAI, self).__init__()
        # self.send_to_ai = Process()
        self.send_to_ai = TestAI()
        self.counter = 0
        self.turn_counter_p1 = 0
        self.turn_counter_p2 = 0

    def get_action_player1(self, action):
        global game_manager, player1_detected_action
        if action[0] == "G1":
            player1_detected_action = "shoot"
            self.turn_counter_p1 += 1
            print(f"Detected action for player 1: {player1_detected_action}")
            print(f"Turn count for player 1: {self.turn_counter_p1}")
        elif action[0] == "W1":
            player1_detected_action = self.send_to_ai.process(action)
            print(f"Player 1 detected action: {player1_detected_action}")
            if player1_detected_action != "":
                self.turn_counter_p1 += 1
                print(f"Detected action for player 1: {player1_detected_action}")
                print(f"Turn count for player 1: {self.turn_counter_p1}")
            elif player1_detected_action == "":
                return ""
        if player1_detected_action == "logout" and self.turn_counter_p1 >= 19:
            print("Disconnecting BYE.....")
            exit_event.set()
        return

    def get_action_player2(self, action):
        global game_manager, player2_detected_action
        if action[0] == "G2":
            player2_detected_action = "shoot"
            self.turn_counter_p2 += 1
            print(f"Detected action for Player 2: {player2_detected_action}")
            print(f"Turn count for player 2: {self.turn_counter_p2}")
        elif action[0] == "W2":
            player2_detected_action = self.send_to_ai.process(action)
            print(f"Player 2 detected action: {player2_detected_action}")
            if player1_detected_action != "":
                self.turn_counter_p2 += 1
                print(f"Detected action for Player 2: {player2_detected_action}")
                print(f"Turn count for player 2: {self.turn_counter_p2}")
            elif player2_detected_action == "":
                return ""
        if player2_detected_action == "logout" and self.turn_counter_p2 >= 19:
            print("Disconnecting BYE.....")
            exit_event.set()
        return

    def run(self):
        global player1_action_q, player2_action_q
        action1_flag = False
        action2_flag = False
        while not exit_event.is_set():
            while not player1_action_q.empty():
                action = player1_action_q.get()
                # print(f"In run player 1: {action}")
                self.get_action_player1(action)
                if action != "":
                    action1_flag = True

            while not player2_action_q.empty():
                action = player2_action_q.get()
                # print(f"In run player 2: {action}")
                self.get_action_player2(action)
                if action != "":
                    action2_flag = True

            if action1_flag is True and action2_flag is True:
                game_manager.detected_game_state(player1_detected_action, player2_detected_action)
                action1_flag = False
                action2_flag = False
                eval_message_event.set()
                visualizer_message_event.set()


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


class CommWithEvalServer(threading.Thread):
    def __init__(self):
        super(CommWithEvalServer, self).__init__()
        self.eval_client = EvalClient(IP_SERVER, PORT_OUT)
        self.updated_state = {}

    def run(self):
        global game_manager
        while not exit_event.is_set():
            message_received = eval_message_event.wait()
            if message_received:
                self.updated_state = self.eval_client.handle_eval_server(game_manager.get_dict())
                game_manager.update_game_state(self.updated_state)
                eval_message_event.clear()


class CommWithVisualizer(threading.Thread):
    def __init__(self):
        super(CommWithVisualizer, self).__init__()
        self.visualizer_publish = VisualizerBroadcast()

    def run(self):
        global game_manager
        global player1_detected_action
        while not exit_event.is_set():
            message_received = visualizer_message_event.wait()
            if message_received:
                self.visualizer_publish.publish_message(json.dumps(game_manager.get_dict()))
                visualizer_message_event.clear()


def main():
    global PORT_OUT, IP_SERVER
    IP_SERVER = sys.argv[1]
    PORT_OUT = sys.argv[2]
    PORT_OUT = int(PORT_OUT)
    u96_server = Ultra96Server()
    detect_action_from_ai = DetectActionFromAI()
    comm_eval_server = CommWithEvalServer()
    comm_visualizer = CommWithVisualizer()
    u96_server.start()
    detect_action_from_ai.start()
    comm_eval_server.start()
    comm_visualizer.start()


if __name__ == "__main__":
    main()

