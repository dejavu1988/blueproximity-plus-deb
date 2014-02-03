#!/usr/bin/env python
# This is for calculating decision

import threading
from sensor import *
import time
from log import Logging

TAG = 'CAL'

class Calculate(threading.Thread):
    def __init__(self, logging, sample):
        threading.Thread.__init__(self)
        self.sample = sample
        self.log = logging

    def run(self):
        while True:
            if self.sample.getStatus() and (not self.sample.isDecisionOn()):
                self.log.log(TAG,'New Calculation')
                self.sample.calculateDecision()
            time.sleep(1)
