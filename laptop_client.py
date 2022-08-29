import sys
import threading
import zmq


class LaptopClient(threading.Thread):
    def __init__(self):
        super(LaptopClient, self).__init__()
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)

    def init_socket_connection(self):
        #  Socket to talk to server
        print("Connecting to Ultra96 server…")
        self.socket.connect("tcp://localhost:5550")

    def send_message(self):
        while True:
            new_action = input("[Type] New Action: ")
            new_action = new_action.encode("utf8")
            self.socket.send(new_action)
            message = self.socket.recv()
            message = message.decode("utf8")
            print(message)


def main():
    lp_client = LaptopClient()
    lp_client.init_socket_connection()
    lp_client.send_message()
    sys.exit()


if __name__ == "__main__":
    main()
