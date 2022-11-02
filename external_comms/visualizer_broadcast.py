import time
import paho.mqtt.client as mqtt
import threading
from queue import Queue

q = Queue()
q1 = Queue()


class VisualizerBroadcast(threading.Thread):
    def __init__(self):
        super(VisualizerBroadcast, self).__init__()
        self.publisher = mqtt.Client()
        # self.broker_address = "b1386744d1594b29a88d72d9bab70fbe.s1.eu.hivemq.cloud"
        self.broker_address = "broker.hivemq.com"
        # self.username = "cg4002_b15"
        # self.password = "CG4002_B15"
        self.topic_viz_recv = "Ultra96/visualizer/receive"
        self.topic_viz_send = "Ultra96/visualizer/send2"
        self.init_message_queue_connection()

    def init_message_queue_connection(self):
        self.publisher.on_connect = self.on_connect
        self.publisher.on_message = self.on_message
        self.publisher.connect(self.broker_address, 1883)
        self.publisher.subscribe(self.topic_viz_send)
        self.publisher.loop_start()

    @staticmethod
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected")
        else:
            print(f"Connection failed, RC err: {rc}")

    @staticmethod
    def on_message(client, userdata, msg):
        # print(f"In on message: {msg.payload}")
        message = msg.payload.decode("utf-8")
        q.put(message)

    @staticmethod
    def receive_message():
        while not q.empty():
            message = q.get()
            if message is None:
                continue
            print(f"Received from visualizer: {message}") 
            return message

    def publish_message(self, message):
        self.publisher.publish(self.topic_viz_recv, message)


class VisualizerReceive:
    def __init__(self):
        self.publisher = mqtt.Client()
        # self.broker_address = "b1386744d1594b29a88d72d9bab70fbe.s1.eu.hivemq.cloud"
        self.broker_address = "broker.hivemq.com"
        # self.username = "cg4002_b15"
        # self.password = "CG4002_B15"
        self.topic_viz_recv = "Ultra96/visualizer/receive2"
        self.topic_viz_send = "Ultra96/visualizer/send"
        self.init_message_queue_connection()

    def init_message_queue_connection(self):
        self.publisher.on_connect = self.on_connect
        self.publisher.on_message = self.on_message
        self.publisher.connect(self.broker_address, 1883)
        self.publisher.subscribe(self.topic_viz_send)
        self.publisher.loop_start()

    @staticmethod
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected")
        else:
            print(f"Connection failed, RC err: {rc}")

    @staticmethod
    def on_message(client, userdata, msg):
        print(f"In on message: {msg.payload}")
        message = msg.payload.decode("utf-8")
        q1.put(message)

    @staticmethod
    def receive_message():
        # while not q1.empty():
            message = q1.get()
            # if message is None:
            #    continue
            print(f"Received from visualizer: {message}")
            return message

# if __name__ == "__main__":
#     vis_broad = VisualizerBroadcast()
#     while True:
#         data = input("type: ")
#         vis_broad.publish_message(data)
#         if data == "grenade":
#            time.sleep(1)
#            vis_broad.receive_message()
