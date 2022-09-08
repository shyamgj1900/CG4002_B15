import paho.mqtt.client as mqtt

broker_address = "b1386744d1594b29a88d72d9bab70fbe.s1.eu.hivemq.cloud"

username = "cg4002_b15"
password = "CG4002_B15"

topic = "Ultra96/visualizer"


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected")
    else:
        print(f"Connection failed, RC err: {rc}")


def on_message(client, userdata, msg):
    print("Received Message: " + msg.topic + "->" + msg.payload.decode("utf-8"))


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS)
client.username_pw_set(username, password)
client.connect(broker_address, 8883)

client.subscribe(topic)

client.loop_forever()


