#!/usr/bin/env python
# This is for calculating decision

import threading
from sensor import *
import time
from log import *

DEBUG = True
TAG = 'CAL'


class Calculate(threading.Thread):
    def __init__(self, log_queue, log_lock, dec_queue, dec_lock, sample):
        threading.Thread.__init__(self)
        self.sample = sample
        self.log_queue = log_queue
        self.log_lock = log_lock
        self.queue = dec_queue # decision queue
        self.lock = dec_lock # decision lock
        self._stop = threading.Event()

    def run(self):
        while not self._stop.is_set():
            try:
                self.lock.acquire()
                if not self.queue.empty():
                    tag = self.queue.get(False)
                    if DEBUG:
                        print "Dec dequeue"
                    if self.sample.getStatus() and (self.sample.decisiontime < self.sample.time):
                        self.log(TAG,'New Calculation')
                        self.sample.calculateDecision()
                        self.queue.task_done()
                    if DEBUG:
                        print "Decision calculated."
            except:
                pass
            finally:
                self.lock.release()
            self._stop.wait(0.5)

    def log(self, tag, msg):
        log(self.log_queue, self.log_lock, tag, msg)

    def stop(self):
        if DEBUG:
            print "Calculate stopped."
        self._stop.set()


def dec_enqueue(queue, lock, tag):
    try:
        lock.acquire()
        queue.put(tag)
        if DEBUG:
            print "DEC enqueued."
    except:
            pass
    finally:
        lock.release()