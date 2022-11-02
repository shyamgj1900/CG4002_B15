import json
import threading
import time

import zmq
from sshtunnel import SSHTunnelForwarder
from getpass import getpass
from Crypto.Util.Padding import pad
from Crypto.Cipher import AES


class LaptopClient(threading.Thread):
    def __init__(self):
        super(LaptopClient, self).__init__()
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.stu_ssh_addr = "sunfire.comp.nus.edu.sg"
        self.stu_ssh_username = "shyam"
        self.stu_ssh_password = ""
        self.ultra96_ssh_addr = "192.168.95.247"
        self.ultra96_ssh_username = "xilinx"
        self.ultra96_ssh_password = "xilinx"
        self.tunnels = []

    def start_tunnels(self):
        """
        This function starts the ssh tunnel to connect the client laptop to the Ultra96.
        """
        # First connection to stu
        self.tunnels.append(SSHTunnelForwarder(remote_bind_address=(self.ultra96_ssh_addr, 22),
                                               ssh_address_or_host=self.stu_ssh_addr,
                                               ssh_username=self.stu_ssh_username,
                                               ssh_password=self.stu_ssh_password))
        try:
            self.tunnels[0].start()
            print("Started tunnel [1]")
        except Exception as e:
            print(f"Tunnel error: {e}")

        # Second connection to Ultra96
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
        """
        This function closes the ssh tunnel connection.
        """
        for tunnel in reversed(self.tunnels):
            tunnel.stop()

    def init_socket_connection(self):
        """
        This function initializes socket connection to connect and talk to the server.
        """
        print("Connecting to Ultra96 server…")
        self.socket.connect("tcp://127.0.0.1:" + str(self.tunnels[1].local_bind_port))

    def send_message(self):
        """
        This function sends the user given input to the Ultra96 server through the message queues.
        """
        multi_new_actions = [[['W2', -70.38, 3.27, -48.11, -121.0, -141.0, 6394.0],
                              ['W2', -71.03, 2.55, -48.44, -210.0, 59.0, 6410.0],
                              ['W2', -70.43, 2.68, -48.73, -327.0, 302.0, 6501.0],
                              ['W2', -60.4, 2.4, -47.49, -491.0, 57.0, 6448.0],
                              ['W2', -50.17, -5.85, -46.28, 958.0, 812.0, 5671.0],
                              ['W2', -35.65, -4.3, -52.98, 3807.0, 7830.0, 7993.0],
                              ['W2', -22.88, 30.97, -63.42, -6733.0, -1358.0, 13112.0],
                              ['W2', -159.51, 117.16, -116.31, -14538.0, -10123.0, 5300.0],
                              ['W2', -169.66, 132.99, -130.99, -11577.0, -13675.0, -5993.0],
                              ['W2', -151.24, 148.84, 163.76, 2119.0, -10807.0, -15103.0]],
                             [['W2', -70.38, 3.27, -48.11, -121.0, -141.0, 6394.0],
                              ['W2', -71.03, 2.55, -48.44, -210.0, 59.0, 6410.0],
                              ['W2', -70.43, 2.68, -48.73, -327.0, 302.0, 6501.0],
                              ['W2', -60.4, 2.4, -47.49, -491.0, 57.0, 6448.0],
                              ['W2', -50.17, -5.85, -46.28, 958.0, 812.0, 5671.0],
                              ['W2', -35.65, -4.3, -52.98, 3807.0, 7830.0, 7993.0],
                              ['W2', -22.88, 30.97, -63.42, -6733.0, -1358.0, 13112.0],
                              ['W2', -159.51, 117.16, -116.31, -14538.0, -10123.0, 5300.0],
                              ['W2', -169.66, 132.99, -130.99, -11577.0, -13675.0, -5993.0],
                              ['W2', -151.24, 148.84, 163.76, 2119.0, -10807.0, -15103.0]],
                             [['W2', -70.38, 3.27, -48.11, -121.0, -141.0, 6394.0],
                              ['W2', -71.03, 2.55, -48.44, -210.0, 59.0, 6410.0],
                              ['W2', -70.43, 2.68, -48.73, -327.0, 302.0, 6501.0],
                              ['W2', -60.4, 2.4, -47.49, -491.0, 57.0, 6448.0],
                              ['W2', -50.17, -5.85, -46.28, 958.0, 812.0, 5671.0],
                              ['W2', -35.65, -4.3, -52.98, 3807.0, 7830.0, 7993.0],
                              ['W2', -22.88, 30.97, -63.42, -6733.0, -1358.0, 13112.0],
                              ['W2', -159.51, 117.16, -116.31, -14538.0, -10123.0, 5300.0],
                              ['W2', -169.66, 132.99, -130.99, -11577.0, -13675.0, -5993.0],
                              ['W2', -151.24, 148.84, 163.76, 2119.0, -10807.0, -15103.0]]]
        for new_actions in multi_new_actions:
            var = input("Enter any key...")
            for new_action in new_actions:
                new_action = json.dumps(new_action)
                new_action_encode = new_action.encode("utf8")
                new_action_padded_message = pad(new_action_encode, AES.block_size)
                self.socket.send(new_action_padded_message)
                # Receive acknowledge message
                message = self.socket.recv()
                message = message.decode("utf8")
                print(message)
                time.sleep(0.1)

    def run(self):
        """
        This is the main function of the client.
        """
        self.stu_ssh_password = getpass()
        self.start_tunnels()
        self.init_socket_connection()
        self.send_message()


def main():
    lp_client = LaptopClient()
    lp_client.start()


if __name__ == "__main__":
    main()