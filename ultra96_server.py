import sys
import threading
import socket
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
player1_hit = False
player2_hit = False
player1_detected_action = Queue()
player2_detected_action = Queue()
p1_beetle_id = Queue()
p2_beetle_id = Queue()
p1_connection_status = Queue()
p2_connection_status = Queue()
eval_message_event = threading.Event()
visualizer_message_event = threading.Event()
detect_action_event = threading.Event()
exit_event = threading.Event()
start_time_packet = 0
start_time_action_detect = 0
end_time_action_detect = 0
packet_index = 0

PORT_OUT = 0
IP_SERVER = ""
BUF_SIZE = 1024


class DetectActionForP1(threading.Thread):
    def __init__(self):
        super(DetectActionForP1, self).__init__()
        self.send_to_ai = Process()
        self.check_grenade_stat = VisualizerBroadcast()
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
            # print(f"Player 1 detected action: {action}")
            if action == "logout" and self.turn_counter_p1 > 19:
                print("Disconnecting BYE.....")
                exit_event.set()
            if action != "":
                self.turn_counter_p1 += 1
                print(f"Detected action for player 1: {action}")
                print(f"Turn count for player 1: {self.turn_counter_p1}")
                if action == "grenade":
                    msg = "p1 " + action
                    self.check_grenade_stat.publish_message(msg)
                    time.sleep(1)
                    grenade_status = self.check_grenade_stat.receive_message()
                    if grenade_status == "player 2 hit":
                        global player2_hit
                        player2_hit = True
                return action
            elif action == "":
                return ""
        elif data[0] == "V1":
            global player1_hit
            player1_hit = True
            return ""
        return ""

    def run(self):
        global player1_detected_action
        while not exit_event.is_set():
            while not player1_action_q.empty():
                data = player1_action_q.get()
                # print(f"In run player 1: {action}")
                action = self.get_action_player1(data)
                if action != "":
                    player1_detected_action.put(action)
                    # while not player1_action_q.empty():
                    #     data = player1_action_q.get()   # clear any residual data packets


class DetectActionForP2(threading.Thread):
    def __init__(self):
        super(DetectActionForP2, self).__init__()
        self.send_to_ai = Process()
        self.check_grenade_stat = VisualizerBroadcast()
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
            # print(f"Player 2 detected action: {action}")
            if action == "logout" and self.turn_counter_p2 > 19:
                print("Disconnecting BYE.....")
                exit_event.set()
            if action != "":
                self.turn_counter_p2 += 1
                print(f"Detected action for Player 2: {action}")
                print(f"Turn count for player 2: {self.turn_counter_p2}")
                if action == "grenade":
                    msg = "p2 " + action
                    self.check_grenade_stat.publish_message(msg)
                    time.sleep(1)
                    grenade_status = self.check_grenade_stat.receive_message()
                    if grenade_status == "player 1 hit":
                        global player1_hit
                        player1_hit = True
                return action
            elif action == "":
                return ""
        elif data[0] == "V2":
            global player2_hit
            player2_hit = True
            return ""
        return ""

    def run(self):
        global player2_detected_action
        while not exit_event.is_set():
            while not player2_action_q.empty():
                data = player2_action_q.get()
                # print(f"In run player 2: {action}")
                action = self.get_action_player2(data)
                if action != "":
                    player2_detected_action.put(action)
                    # while not player2_action_q.empty():
                    #     data = player2_action_q.get()    # clear any residual data packets


class ReceiveMessageP1(threading.Thread):
    def __init__(self):
        super(ReceiveMessageP1, self).__init__()
        # self.context = zmq.Context()
        # self.socket = self.context.socket(zmq.REP)
        self.socket_p1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.raw_data = ""

    def init_socket_connection(self):
        """
        This function initialises the socket connection.
        """
        try:
            # print("Establishing connection through port 5550")
            # self.socket.bind("tcp://*:5550")
            self.socket_p1.bind(("127.0.0.1", 5550))
            self.socket_p1.listen()
            (conn, address) = self.socket_p1.accept()
            print("Accepted a connection request from %s:%s" % (address[0], address[1]))
        except Exception as e:
            print(f"Socket err: {e}")

    def receive_message_from_laptop(self):
        """
        This function receives a message from the laptop client through message queues and sends an ACK message back to
        the laptop client.
        """
        try:
            padded_raw_data = self.socket_p1.recv(BUF_SIZE)
            self.raw_data = unpad(padded_raw_data, AES.block_size)
            self.raw_data = self.raw_data.decode("utf8")
            self.raw_data = json.loads(self.raw_data)
            if self.raw_data[0] == 'G1' or self.raw_data[0] == 'W1' or self.raw_data[0] == 'V1':
                if self.raw_data[1] == "connected" or self.raw_data[1] == "disconnected":
                    p1_beetle_id.put(self.raw_data[0])
                    p1_connection_status.put(self.raw_data[1])
                else:
                    player1_action_q.put(self.raw_data)
            # elif self.raw_data[0] == 'G2' or self.raw_data[0] == 'W2' or self.raw_data[0] == 'V2':
            #     if self.raw_data[1] == "connected" or self.raw_data[1] == "disconnected":
            #         p2_beetle_id.put(self.raw_data[0])
            #         p2_connection_status.put(self.raw_data[1])
            #     else:
            #         player2_action_q.put(self.raw_data)
            # self.socket_p1.send(b"ACK")
        except Exception as e:
            print(f"Error receiving message: {e}")

    def run(self):
        """
        This is the main thread for the Ultra96 server.
        """
        self.init_socket_connection()
        while not exit_event.is_set():
            self.receive_message_from_laptop()


class ReceiveMessageP2(threading.Thread):
    def __init__(self):
        super(ReceiveMessageP2, self).__init__()
        # self.context = zmq.Context()
        # self.socket = self.context.socket(zmq.REP)
        self.socket_p2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.raw_data = ""

    def init_socket_connection(self):
        """
        This function initialises the socket connection.
        """
        try:
            # print("Establishing connection through port 5550")
            # self.socket.bind("tcp://*:5550")
            self.socket_p2.bind(("127.0.0.1", 5551))
            self.socket_p2.listen()
            (conn, address) = self.socket_p2.accept()
            print("Accepted a connection request from %s:%s" % (address[0], address[1]))
        except Exception as e:
            print(f"Socket err: {e}")

    def receive_message_from_laptop(self):
        """
        This function receives a message from the laptop client through message queues and sends an ACK message back to
        the laptop client.
        """
        try:
            padded_raw_data = self.socket_p2.recv(BUF_SIZE)
            self.raw_data = unpad(padded_raw_data, AES.block_size)
            self.raw_data = self.raw_data.decode("utf8")
            self.raw_data = json.loads(self.raw_data)
            if self.raw_data[0] == 'G2' or self.raw_data[0] == 'W2' or self.raw_data[0] == 'V2':
                if self.raw_data[1] == "connected" or self.raw_data[1] == "disconnected":
                    p2_beetle_id.put(self.raw_data[0])
                    p2_connection_status.put(self.raw_data[1])
                else:
                    player2_action_q.put(self.raw_data)
            # self.socket.send(b"ACK")
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
        # if player1_detected_action != "" and player2_detected_action != "":
        global player1_hit, player2_hit
        p1_action = player1_detected_action.get()
        p2_action = player2_detected_action.get()
        if p1_action == "shoot" or p2_action == "shoot" or p1_action == "grenade" or p2_action == "grenade":
            game_manager.detected_game_state(p1_action, p2_action, player1_hit, player2_hit)
        else:
            game_manager.detected_game_state(p1_action, p2_action)
        self.comm_eval_server.send_message_to_eval_server()
        self.comm_visualizer.send_message_to_visualizer()
        player1_hit = False
        player2_hit = False

    def send_connection_status_p1(self):
        p1_beetle = p1_beetle_id.get()
        p1_conn = p1_connection_status.get()
        self.comm_visualizer.send_message_to_visualizer(p1_beetle, p1_conn)

    def send_connection_status_p2(self):
        p2_beetle = p2_beetle_id.get()
        p2_conn = p2_connection_status.get()
        self.comm_visualizer.send_message_to_visualizer(p2_beetle, p2_conn)

    def run(self):
        while not exit_event.is_set():
            if player1_detected_action.qsize() != 0 and player2_detected_action.qsize() != 0:
                self.send_message()
            if p1_beetle_id.qsize() != 0:
                self.send_connection_status_p1()
            if p2_beetle_id.qsize() != 0:
                self.send_connection_status_p2()


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

    def send_message_to_visualizer(self, beetle_id="", status=""):
        if beetle_id != "" and status != "":
            self.visualizer_publish.publish_message(f"{beetle_id} is {status}")
        else:
            self.visualizer_publish.publish_message(json.dumps(game_manager.get_dict()))


def main():
    global PORT_OUT, IP_SERVER
    IP_SERVER = sys.argv[1]
    PORT_OUT = sys.argv[2]
    PORT_OUT = int(PORT_OUT)
    recv_msg_p1 = ReceiveMessageP1()
    recv_msg_p2 = ReceiveMessageP2()
    detect_action_for_p1 = DetectActionForP1()
    detect_action_for_p2 = DetectActionForP2()
    broadcast_message = BroadcastMessage()
    recv_msg_p1.start()
    recv_msg_p2.start()
    detect_action_for_p1.start()
    detect_action_for_p2.start()
    broadcast_message.start()


if __name__ == "__main__":
    main()
