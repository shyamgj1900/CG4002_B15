import sys
import threading
import zmq


class Ultra96Server(threading.Thread):
    def __init__(self):
        super(Ultra96Server, self).__init__()
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.message = ""

    def init_socket_connection(self):
        self.socket.bind("tcp://*:5550")

    def receive_message(self):
        self.message = self.socket.recv()
        self.message = self.message.decode("utf8")
        print(f"Received Message: {self.message}")
        self.socket.send(b"ACK")
        if self.message == "logout":
            sys.exit()

    def get_new_message(self):
        return self.message

    def run(self):
        self.init_socket_connection()
        while True:
            self.receive_message()


def main():
    u96_server = Ultra96Server()
    u96_server.start()


if __name__ == "__main__":
    main()

