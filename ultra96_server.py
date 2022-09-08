import sys
import threading
import zmq


from eval_client import EvalClient
from visualizer_broadcast import VisualizerBroadcast


class Ultra96Server(threading.Thread):
    def __init__(self):
        super(Ultra96Server, self).__init__()
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.message = ""
        self.eval_client = EvalClient()
        self.visualizer_publish = VisualizerBroadcast()

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
        try:
            self.message = self.socket.recv()
            self.message = self.message.decode("utf8")
            print(f"Received Message: {self.message}")
            self.socket.send(b"ACK")
            if self.message == "logout":
                print("Disconnecting BYE...")
                sys.exit()
            self.send_messages()
        except Exception as e:
            print(f"Error receiving message: {e}")

    def send_messages(self):
        self.eval_client.handle_eval_server(self.message)
        self.visualizer_publish.publish_message(self.message)

    def run(self):
        """
        This is the main thread for the Ultra96 server.
        """
        self.init_socket_connection()
        while True:
            self.receive_message_from_laptop()


def main():
    u96_server = Ultra96Server()
    u96_server.start()


if __name__ == "__main__":
    main()

