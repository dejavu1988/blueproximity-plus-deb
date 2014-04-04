#!/usr/bin/env python
# Logs debug /status messages

import Queue
import threading
import time
import os

DEBUG = True


class Logging(threading.Thread):
    def __init__(self, log_dir, log_queue, log_lock):
        threading.Thread.__init__(self)
        self.path = os.path.join(log_dir, 'log.txt')
        self._stop = threading.Event()
        self.lock = log_lock
        self.queue = log_queue
        self.set_permission()

    def run(self):
        if DEBUG:
            print "Log started."
        while not self._stop.is_set():
            try:
                self.lock.acquire()
                if not self.queue.empty():
                    entry = self.queue.get(False)
                    with open(self.path, 'a') as f:
                        f.write(entry[0] + ":\t[" + entry[1] + "]: " + entry[2] + "\n")
                    self.queue.task_done()
                    if DEBUG:
                        print "Log dequeued.."
            except IOError as e:
                print "Log Dequeue IOError(%d)-%s:%s" % (e.errno, e.strerror, e.message)
            finally:
                self.lock.release()
            self._stop.wait(1)

    def stop(self):
        if DEBUG:
            print "Log stopped."
        self._stop.set()

    def set_permission(self):
        if not os.path.isfile(self.path):
            f = open(self.path, 'a')
            f.close()
            os.chmod(self.path, 0664)


def log(queue, lock, tag, msg):
        """
        Enqueues log into log_queue
        :param queue: log_queue
        :param lock: log_lock
        :param tag: log tag
        :param msg: log message
        """
        try:
            lock.acquire()
            queue.put((str(time.time()), tag, msg))
            if DEBUG:
                print "Log enqueued."
        except IOError as e:
                print "Log Enqueue IOError(%d)-%s:%s" % (e.errno, e.strerror, e.message)
        finally:
            lock.release()


if __name__ == "__main__":
    TAG = 'test'
    l = Logging(os.getcwd())
    l.start()
    time.sleep(3)
    l.log(TAG, '1st msg')
    time.sleep(3)
    l.log(TAG, '2nd msg')
    l.stop()
