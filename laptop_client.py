import threading
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
        self.stu_ssh_addr = "stu.comp.nus.edu.sg"
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
        while True:
            # Get new action input from user
            new_action = input("[Type] New Action: ")
            new_action_encode = new_action.encode("utf8")
            new_action_padded_message = pad(new_action_encode, AES.block_size)
            self.socket.send(new_action_padded_message)
            # Receive ACK message from server
            message = self.socket.recv()
            message = message.decode("utf8")
            print(message)
            if new_action.lower() == "logout":
                break
        self.socket.close()
        self.stop_tunnels()
        print("BYE......")

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
