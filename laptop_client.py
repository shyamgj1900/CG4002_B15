import json
import threading
import time
import pandas as pd
import numpy as np
import zmq
from sshtunnel import SSHTunnelForwarder
from getpass import getpass
from Crypto.Util.Padding import pad
from Crypto.Cipher import AES
import queue
import json


class LaptopClient(threading.Thread):
    def __init__(self):
        super(LaptopClient, self).__init__()
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.stu_ssh_addr = "stu.comp.nus.edu.sg"
        self.stu_ssh_username = "shyam"
        self.stu_ssh_password = ""
        self.ultra96_ssh_addr = "192.168.95.247"
        self.ultra96_ssh_username = "xilinx"
        self.ultra96_ssh_password = "xilinx"
        self.tunnels = []
        self.bluno_data = queue.Queue()

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
        df = pd.read_csv('./test_data.csv')
        new_actions = df.to_numpy()
        new_actions = new_actions.tolist()
        multi_new_actions = [new_actions[0:10], new_actions[10:20], new_actions[20:30]]
        # multi_new_actions = [[['W1', -97.18, 4.32, -44.16, -107.0, -41.0, 2332.0],
        #                       ['W1', -96.18, 4.51, -43.3, -56.0, 105.0, 2271.0],
        #                       ['W1', -92.38, 3.95, -42.93, 18.0, 25.0, 2161.0],
        #                       ['W1', -90.22, 3.86, -44.14, -13.0, 207.0, 2236.0],
        #                       ['W1', -92.28, 6.86, -46.86, -197.0, 1676.0, 2335.0],
        #                       ['W1', -122.2, 7.98, -60.31, 1615.0, 2119.0, 4144.0],
        #                       ['W1', 93.68, -113.27, -92.62, -6288.0, 3886.0, 4857.0],
        #                       ['W1', 159.87, -162.4, -109.27, -5704.0, -8318.0, -4227.0],
        #                       ['W1', -85.33, 64.57, -88.78, -565.0, -4062.0, 1494.0],
        #                       ['W1', -81.06, 23.38, -48.65, 4861.0, -2878.0, 49.0]],
        #                      [['W1', -70.38, 3.27, -48.11, -121.0, -141.0, 6394.0],
        #                       ['W1', -71.03, 2.55, -48.44, -210.0, 59.0, 6410.0],
        #                       ['W1', -70.43, 2.68, -48.73, -327.0, 302.0, 6501.0],
        #                       ['W1', -60.4, 2.4, -47.49, -491.0, 57.0, 6448.0],
        #                       ['W1', -50.17, -5.85, -46.28, 958.0, 812.0, 5671.0],
        #                       ['W1', -35.65, -4.3, -52.98, 3807.0, 7830.0, 7993.0],
        #                       ['W1', -22.88, 30.97, -63.42, -6733.0, -1358.0, 13112.0],
        #                       ['W1', -159.51, 117.16, -116.31, -14538.0, -10123.0, 5300.0],
        #                       ['W1', -169.66, 132.99, -130.99, -11577.0, -13675.0, -5993.0],
        #                       ['W1', -151.24, 148.84, 163.76, 2119.0, -10807.0, -15103.0]],
        #                      [['W1', -43.55, 1.98, -52.97, 286.0, -461.0, 5009.0],
        #                       ['W1', -41.56, 0.64, -53.96, -556.0, -186.0, 5408.0],
        #                       ['W1', -45.64, 0.58, -53.47, 256.0, 574.0, 5451.0],
        #                       ['W1', -45.84, 1.29, -53.36, 104.0, -84.0, 5358.0],
        #                       ['W1', -46.29, 3.57, -52.32, -5.0, -162.0, 5940.0],
        #                       ['W1', -50.85, 24.36, -38.76, 242.0, -1797.0, 10887.0],
        #                       ['W1', -58.13, 52.28, 27.23, 5482.0, -7265.0, 3068.0],
        #                       ['W1', -46.07, 93.67, 88.56, 3177.0, -2090.0, -10297.0],
        #                       ['W1', -29.74, 151.72, 118.56, 2387.0, 3798.0, -11181.0],
        #                       ['W1', -18.03, 168.7, 135.62, -869.0, 6254.0, -9281.0]]]
        for new_actions in multi_new_actions:
            for i, new_action in enumerate(new_actions):
                new_action = json.dumps(new_action)
                new_action_encode = new_action.encode("utf8")
                new_action_padded_message = pad(new_action_encode, AES.block_size)
                self.socket.send(new_action_padded_message)
                # Receive acknowledge message
                message = self.socket.recv()
                message = message.decode("utf8")
                print(message)
                time.sleep(0.1)
            var = input("Enter any key...")

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