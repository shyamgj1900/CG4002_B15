import time
import paho.mqtt.client as mqtt
import threading
from queue import Queue

msg_q = Queue()


class VisualizerBroadcast(threading.Thread):
    def __init__(self):
        super(VisualizerBroadcast, self).__init__()
        self.publisher = mqtt.Client()
        self.broker_address = "broker.hivemq.com"
        self.topic_viz_recv = "Ultra96/visualizer/receive"
        self.topic_viz_send = "Ultra96/visualizer/send2"
        self.init_message_queue_connection()

    def init_message_queue_connection(self):
        self.publisher.on_connect = self.on_connect
        self.publisher.connect(self.broker_address, 1883)
        self.publisher.loop_start()

    @staticmethod
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to Viz B-Cast")
        else:
            print(f"Connection failed, RC err: {rc}")

    def publish_message(self, message):
        self.publisher.publish(self.topic_viz_recv, message)


class VisualizerReceive:
    def __init__(self):
        self.publisher = mqtt.Client()
        self.broker_address = "broker.hivemq.com"
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
            print("Connected to Viz Rec")
        else:
            print(f"Connection failed, RC err: {rc}")

    @staticmethod
    def on_message(client, userdata, msg):
        message = msg.payload.decode("utf-8")
        msg_q.put(message)

    @staticmethod
    def receive_message():
        message = msg_q.get()
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
