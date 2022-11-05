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
from external_comms.visualizer_broadcast import VisualizerReceive

game_manager = GameState()
visualizer_publish = VisualizerBroadcast()
visualizer_receive = VisualizerReceive()
send_to_ai_p1 = None
send_to_ai_p2 = None
player1_action_q = Queue()
player2_action_q = Queue()
player1_hit = False
player2_hit = False
player1_detected_action = ""
player2_detected_action = ""
p1_beetle_id = Queue()
p2_beetle_id = Queue()
p1_connection_status = Queue()
p2_connection_status = Queue()
q = Queue()
exit_event = threading.Event()
turn_counter = 0

PORT_OUT = 0
IP_SERVER = ""


class DetectActionForP1(threading.Thread):
    def __init__(self):
        super(DetectActionForP1, self).__init__()
        self.send_to_ai = Process()

    def get_action_player1(self, data):
        """
        This method passes the data packets received from the relay node for player 1 and gets the detected action.
        """
        if data[1] == 'reload':
            action = 'reload'
            print(f"Detected action for Player 1: {action}")
            print(f"Turn count for player 1: {turn_counter}")
            return action
        if data[0] == 'G1':
            action = "shoot"
            print(f"Detected action for player 1: {action}")
            print(f"Turn count for player 1: {turn_counter}")
            return action
        elif data[0] == 'W1':
            action = self.send_to_ai.process(data)
            if action == "logout" and turn_counter > 19:
                print("Disconnecting BYE.....")
                exit_event.set()
            if action != "":
                print(f"Detected action for player 1: {action}")
                print(f"Turn count for player 1: {turn_counter}")
                if action == "grenade":
                    msg = "p1 " + action
                    visualizer_publish.publish_message(msg)
                    grenade_status = visualizer_receive.receive_message()
                    print(f"Grenade stat: {grenade_status}")
                    if grenade_status == "player 2 hit":
                        global player2_hit
                        player2_hit = True
                return action
            elif action == "":
                return ""
        elif data[0] == 'V1':
            global player1_hit
            player1_hit = True
            return ""
        return ""

    def run(self):
        global player1_detected_action
        while not exit_event.is_set():
            while not player1_action_q.empty():
                data = player1_action_q.get()
                action = self.get_action_player1(data)
                if action != "":
                    player1_detected_action = action
                    while not player1_action_q.empty():
                        player1_action_q.get()


class DetectActionForP2(threading.Thread):
    def __init__(self):
        super(DetectActionForP2, self).__init__()
        self.send_to_ai = Process()

    def get_action_player2(self, data):
        """
        This method passes the data packets received from the relay node for player 2 and gets the detected action.
        """
        if data[1] == 'reload':
            action = "reload"
            print(f"Detected action for Player 2: {action}")
            print(f"Turn count for player 2: {turn_counter}")
            return action
        if data[0] == 'G2':
            action = "shoot"
            print(f"Detected action for Player 2: {action}")
            print(f"Turn count for player 2: {turn_counter}")
            return action
        elif data[0] == 'W2':
            action = self.send_to_ai.process(data)
            if action == "logout" and turn_counter > 19:
                print("Disconnecting BYE.....")
                exit_event.set()
            if action != "":
                print(f"Detected action for Player 2: {action}")
                print(f"Turn count for player 2: {turn_counter}")
                if action == "grenade":
                    msg = "p2 " + action
                    visualizer_publish.publish_message(msg)
                    grenade_status = visualizer_receive.receive_message()
                    print(f"Grenade stat: {grenade_status}")
                    if grenade_status == "player 1 hit":
                        global player1_hit
                        player1_hit = True
                return action
            elif action == "":
                return ""
        elif data[0] == 'V2':
            global player2_hit
            player2_hit = True
            return ""
        return ""

    def run(self):
        global player2_detected_action
        while not exit_event.is_set():
            while not player2_action_q.empty():
                data = player2_action_q.get()
                action = self.get_action_player2(data)
                if action != "":
                    player2_detected_action = action
                    while not player2_action_q.empty():
                        player2_action_q.get()


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
            self.socket.send(b"ACK")
            self.raw_data = unpad(padded_raw_data, AES.block_size)
            self.raw_data = self.raw_data.decode("utf8")
            self.raw_data = json.loads(self.raw_data)
            print(f"Received pkt: {self.raw_data}")
            if self.raw_data[0] == 'G1' or self.raw_data[0] == 'W1' or self.raw_data[0] == 'V1':
                if self.raw_data[1] == 'connected' or self.raw_data[1] == 'disconnected':
                    p1_beetle_id.put(self.raw_data[0])
                    p1_connection_status.put(self.raw_data[1])
                else:
                    player1_action_q.put(self.raw_data)
            elif self.raw_data[0] == 'G2' or self.raw_data[0] == 'W2' or self.raw_data[0] == 'V2':
                if self.raw_data[1] == 'connected' or self.raw_data[1] == 'disconnected':
                    p2_beetle_id.put(self.raw_data[0])
                    p2_connection_status.put(self.raw_data[1])
                else:
                    player2_action_q.put(self.raw_data)
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
        """
        This method helps to send the JSON message when the player actions for both players are detected
        """
        global player1_hit, player2_hit, player1_detected_action, player2_detected_action, turn_counter
        if turn_counter == 0:
            turn_counter += 1
            player1_detected_action = ""
            player2_detected_action = ""
            return
        p1_action = player1_detected_action
        p2_action = player2_detected_action
        if p1_action == "shoot" or p2_action == "shoot" or p1_action == "grenade" or p2_action == "grenade":
            game_manager.detected_game_state(p1_action, p2_action, player2_hit, player1_hit)
        else:
            game_manager.detected_game_state(p1_action, p2_action)
        self.comm_eval_server.send_message_to_eval_server()
        self.comm_visualizer.send_message_to_visualizer()
        player1_detected_action = ""
        player2_detected_action = ""
        player1_hit = False
        player2_hit = False
        turn_counter += 1

    def send_connection_status_p1(self):
        """
        This method sends the connection status regarding p1 wearables to the visualizer
        """
        p1_beetle = p1_beetle_id.get()
        p1_conn = p1_connection_status.get()
        self.comm_visualizer.send_message_to_visualizer(p1_beetle, p1_conn)

    def send_connection_status_p2(self):
        """
        This method sends the connection status regarding p2 wearables to the visualizer
        """
        p2_beetle = p2_beetle_id.get()
        p2_conn = p2_connection_status.get()
        self.comm_visualizer.send_message_to_visualizer(p2_beetle, p2_conn)

    def run(self):
        while not exit_event.is_set():
            if player1_detected_action != "" and player2_detected_action != "":
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
        """
        This sends the JSON message to the eval server and receives the updated JSON message back from the eval server.
        """
        global game_manager
        self.updated_state = self.eval_client.handle_eval_server(game_manager.get_dict())
        game_manager.update_game_state(self.updated_state)


class CommWithVisualizer:
    def __init__(self):
        self.visualizer_publish = VisualizerBroadcast()

    def send_message_to_visualizer(self, beetle_id="", status=""):
        """
        This method sends the connection status regarding the wearables for either players or sends the JSON message
        of the game state.
        """
        if beetle_id != "" and status != "":
            self.visualizer_publish.publish_message(f"{beetle_id} is {status}")
        else:
            self.visualizer_publish.publish_message(json.dumps(game_manager.get_dict()))


def main():
    global PORT_OUT, IP_SERVER, send_to_ai_p1, send_to_ai_p2
    IP_SERVER = sys.argv[1]
    PORT_OUT = sys.argv[2]
    PORT_OUT = int(PORT_OUT)
    send_to_ai_p1 = Process()
    send_to_ai_p2 = Process()
    u96_server = Ultra96Server()
    detect_action_for_p1 = DetectActionForP1()
    detect_action_for_p2 = DetectActionForP2()
    broadcast_message = BroadcastMessage()
    u96_server.start()
    detect_action_for_p1.start()
    detect_action_for_p2.start()
    broadcast_message.start()


if __name__ == "__main__":
    main()
