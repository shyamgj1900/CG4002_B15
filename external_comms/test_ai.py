from queue import Queue
import time


class TestAI:
    def __init__(self):
        self.q = Queue()
        self.raw_buffer = []
        self.counter = 0

    def process(self, raw_data):
        if len(self.raw_buffer) < 20:
            self.raw_buffer.append(raw_data)
            return ""
        elif len(self.raw_buffer) >= 20:
            actions = ['shield', 'shoot', 'grenade', 'reload']
            idx = self.counter % 4
            self.counter += 1
            self.raw_buffer.clear()
            time.sleep(1)
            return actions[idx]
