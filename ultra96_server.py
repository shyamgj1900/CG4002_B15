import sys
import threading
import zmq
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from queue import Queue

from hardware_ai.pynq_overlay import Process
from external_comms.game_state import GameState
from external_comms.eval_client import EvalClient
from external_comms.visualizer_broadcast import VisualizerBroadcast

game_manager = GameState()
detected_action = ""
eval_message_event = threading.Event()
visualizer_message_event = threading.Event()
exit_event = threading.Event()
q = Queue()

PORT_OUT = 0
IP_SERVER = ""


class Ultra96Server(threading.Thread):
    def __init__(self):
        super(Ultra96Server, self).__init__()
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.send_to_ai = Process()
        self.raw_data = ""
        self.counter = 0
        self.turn_counter = 0

    def init_socket_connection(self):
        """
        This function initialises the socket connection.
        """
        try:
            print("Establishing connection through port 5550")
            self.socket.bind("tcp://*:5550")
        except Exception as e:
            print(f"Socket err: {e}")

    def add_raw_data_to_queue(self):
        q.put(self.raw_data)
        self.counter += 1
        if self.counter % 600 != 0:
            return False

    def get_action(self):
        global game_manager
        global detected_action
        if self.raw_data[0] == "G":
            print(f"in u96 g: {self.raw_data}")
            detected_action = "shoot"
            self.turn_counter += 1
            game_manager.detected_game_state(detected_action)
            self.send_to_ai.process("")
            eval_message_event.set()
            visualizer_message_event.set()
        elif self.raw_data[0] == "W":
            detected_action = self.send_to_ai.process(self.raw_data)
            print(f"In u96: {self.raw_data}")
            if detected_action != "":
                print(f"Detected action: {detected_action}")
                self.turn_counter += 1
                game_manager.detected_game_state(detected_action)
                eval_message_event.set()
                visualizer_message_event.set()
            elif detected_action == "":
                return
        if detected_action == "logout" and self.turn_counter >= 19:
            print("Disconnecting BYE.....")
            exit_event.set()
        return

    def receive_message_from_laptop(self):
        """
        This function receives a message from the laptop client through message queues and sends an ACK message back to
        the laptop client.
        """
        try:
            padded_raw_data = self.socket.recv()
            self.raw_data = unpad(padded_raw_data, AES.block_size)
            self.raw_data = self.raw_data.decode("utf8")
            self.raw_data = json.loads(self.raw_data)
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
            self.get_action()


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
        global detected_action
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
    comm_eval_server = CommWithEvalServer()
    comm_visualizer = CommWithVisualizer()
    u96_server.start()
    comm_eval_server.start()
    comm_visualizer.start()


if __name__ == "__main__":
    main()


