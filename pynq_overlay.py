#!/usr/bin/env python
# coding: utf-8

# In[ ]:
import random
from queue import Queue

class Process:
    def __init__(self):
        self.q = Queue()
        self.raw_data = ""
        self.counter = 0

    def add_raw_data_to_queue(self, raw_data):
        self.q.put(raw_data)

    def check_time(self):
        self.counter += 1
        if self.counter < 25:
            return False
        self.counter = 0
        return True
    
    def detect_action(self):
        while not self.q.empty():
            message = self.q.get()
            print(f"Raw msg: {message}")
        actions = ["shoot", "reload", "grenade", "shield"]
        i = random.randint(0,3)
        return actions[i]
    
    def process(self, raw_data):
        self.raw_data = raw_data
        self.add_raw_data_to_queue(self.raw_data)
        if self.check_time() is False:
            return ""
        detected_action = self.detect_action()
        return detected_action
