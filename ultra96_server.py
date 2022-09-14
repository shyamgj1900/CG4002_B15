import sys
import threading
import zmq

from eval_client import EvalClient
from visualizer_broadcast import VisualizerBroadcast

eval_message_event = threading.Event()
visualizer_message_event = threading.Event()
exit_event = threading.Event()
message = ""


class Ultra96Server(threading.Thread):
    def __init__(self):
        super(Ultra96Server, self).__init__()
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)

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
        global message
        try:
            message = self.socket.recv()
            message = message.decode("utf8")
            print(f"Received Message: {message}")
            self.socket.send(b"ACK")
            if message == "logout":
                print("Disconnecting BYE...")
                exit_event.set()
        except Exception as e:
            print(f"Error receiving message: {e}")

    def run(self):
        """
        This is the main thread for the Ultra96 server.
        """
        self.init_socket_connection()
        while not exit_event.is_set():
            self.receive_message_from_laptop()
            eval_message_event.set()
            visualizer_message_event.set()


class CommWithEvalServer(threading.Thread):
    def __init__(self):
        super(CommWithEvalServer, self).__init__()
        self.eval_client = EvalClient()

    def run(self):
        global message
        while not exit_event.is_set():
            message_received = eval_message_event.wait()
            if message_received:
                self.eval_client.handle_eval_server(message)
                eval_message_event.clear()


class CommWithVisualizer(threading.Thread):
    def __init__(self):
        super(CommWithVisualizer, self).__init__()
        self.visualizer_publish = VisualizerBroadcast()

    def run(self):
        global message
        while not exit_event.is_set():
            message_received = visualizer_message_event.wait()
            if message_received:
                self.visualizer_publish.publish_message(message)
                visualizer_message_event.clear()


def main():
    u96_server = Ultra96Server()
    comm_eval_server = CommWithEvalServer()
    comm_visualizer = CommWithVisualizer()
    u96_server.start()
    comm_eval_server.start()
    comm_visualizer.start()


if __name__ == "__main__":
    main()

