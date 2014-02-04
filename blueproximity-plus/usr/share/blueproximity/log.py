#!/usr/bin/env python
# This is for logging

import threading
import time

class Logging(threading.Thread):
    def __init__(self, udir):
        threading.Thread.__init__(self)
        self.logs = []
        self.path = udir+'/log.txt'

    def run(self): 
        print self.path
        while True:
            ts = int(time.time())
            if ts % 300 == 1:   # dump every 15 min
                dump(self.logs, self.path)
                self.logs = []
            time.sleep(1)

    def log(self, TAG, msg):
        self.logs.append((str(time.time()), TAG, msg))


def dump(loglist, path):
    if len(loglist) != 0:
        with open(path, 'a+') as f:
            for entry in loglist:
                f.write(entry[0] + ":\t[" + entry[1] + "]: " + entry[2] + "\n")

if __name__ == "__main__":
    TAG = 'test'
    l = Logging('/home/xzgao/repo/proj-mcbp/blueproximity/blueproximity-1.2.5.orig')
    l.start()
    time.sleep(3)
    l.log(TAG,'1st msg')
    time.sleep(3)
    l.log(TAG,'2nd msg')
