import paho.mqtt.client as mqtt
import threading


class VisualizerBroadcast(threading.Thread):
    def __init__(self):
        super(VisualizerBroadcast, self).__init__()
        self.publisher = mqtt.Client()
        self.broker_address = "b1386744d1594b29a88d72d9bab70fbe.s1.eu.hivemq.cloud"
        self.username = "cg4002_b15"
        self.password = "CG4002_B15"
        self.topic = ["Ultra96/visualizer, Ultra96/AI"]

    def init_message_queue_connection(self):
        self.publisher.on_connect = self.on_connect
        self.publisher.on_message = self.on_message

        self.publisher.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS)
        self.publisher.username_pw_set(self.username, self.password)
        self.publisher.connect(self.broker_address, 8883)

    @staticmethod
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected")
        else:
            print(f"Connection failed, RC err: {rc}")

    @staticmethod
    def on_message(client, userdata, msg):
        print("Received Message: " + msg.topic + "->" + msg.payload.decode("utf-8"))

    def publish_message(self, message):
        self.publisher.publish(self.topic[0], message)
