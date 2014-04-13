#!/usr/bin/env python
# This is for calculating decision

import threading
from sensor import *
import time
from log import *

TAG = 'CAL'

class Calculate(threading.Thread):
    def __init__(self, log_queue, log_lock, sample):
        threading.Thread.__init__(self)
        self.sample = sample
        self.log_queue = log_queue
        self.log_lock = log_lock

    def run(self):
        while True:
            if self.sample.getStatus() and (self.sample.decisiontime < self.sample.time):
                self.log(TAG,'New Calculation')
                self.sample.calculateDecision()
            time.sleep(1)

    def log(self, tag, msg):
        log(self.log_queue, self.log_lock, tag, msg)