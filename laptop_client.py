import sys
import threading
import zmq
from sshtunnel import SSHTunnelForwarder


class LaptopClient(threading.Thread):
    def __init__(self):
        super(LaptopClient, self).__init__()
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.sunfire_ssh_addr = "sunfire.comp.nus.edu.sg"
        self.sunfire_ssh_username = "shyam"
        self.sunfire_ssh_password = "yscd100Plus3/1"
        self.ultra96_ssh_addr = "192.168.95.239"
        self.ultra96_ssh_username = "xilinx"
        self.ultra96_ssh_password = "xilinx"
        self.tunnels = []

    def start_tunnels(self):
        self.tunnels.append(SSHTunnelForwarder(remote_bind_address=(self.ultra96_ssh_addr, 22),
                                               ssh_address_or_host=self.sunfire_ssh_addr,
                                               ssh_username=self.sunfire_ssh_username,
                                               ssh_password=self.sunfire_ssh_password))
        try:
            self.tunnels[0].start()
            print("Started tunnel [1]")
        except Exception as e:
            print(f"Tunnel error: {e}")

        self.tunnels.append(SSHTunnelForwarder(remote_bind_address=(self.ultra96_ssh_addr, 5550),
                                               ssh_address_or_host=("127.0.0.1", self.tunnels[0].local_bind_port),
                                               ssh_username=self.ultra96_ssh_username,
                                               ssh_password=self.ultra96_ssh_password))
        try:
            self.tunnels[1].start()
            print("Started tunnel [2]")
        except Exception as e:
            print(f"2nd Tunnel error: {e}")

        return True

    def stop_tunnels(self):
        for tunnel in reversed(self.tunnels):
            tunnel.stop()

    def init_socket_connection(self):
        #  Socket to talk to server
        print("Connecting to Ultra96 server…")
        self.socket.connect("tcp://127.0.0.1:" + str(self.tunnels[-1].local_bind_port))
        # self.socket.connect("tcp://127.0.0.1:5550")

    def send_message(self):
        while True:
            new_action = input("[Type] New Action: ")
            new_action = new_action.encode("utf8")
            self.socket.send(new_action)
            message = self.socket.recv()
            message = message.decode("utf8")
            print(message)
            if new_action.decode("utf8") == "logout":
                break
        self.socket.close()
        self.stop_tunnels()
        print("BYE......")

    def run(self):
        self.start_tunnels()
        self.init_socket_connection()
        self.send_message()


def main():
    lp_client = LaptopClient()
    lp_client.start()


if __name__ == "__main__":
    main()
