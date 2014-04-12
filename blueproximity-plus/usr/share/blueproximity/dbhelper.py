#!/usr/bin/env python

import Queue
import sqlite3
import os
import threading
import time

DEBUG = True
TAG = 'DB'


class DBHelper(threading.Thread):
    def __init__(self, udir, db_queue, db_lock):
        threading.Thread.__init__(self)
        self.path = os.path.join(udir, 'record.db')
        self._stop = threading.Event()
        self.lock = db_lock
        self.queue = db_queue
        self.set_permission()
        self.create_db()

    def run(self):
        if DEBUG:
            print "DB started."
        while not self._stop.is_set():
            try:
                self.lock.acquire()
                if not self.queue.empty():
                    entry = self.queue.get(False)
                    if DEBUG:
                        print "DB dequeue " + str(entry)
                    if entry[0] == 'INSERT':
                        self.putRecord(entry[1])
                    elif entry[0] == 'ADDFN':
                        self.putRecordForFN(entry[1])
                    elif entry[0] == 'UPDATE':
                        self.updateRecord(entry[1])
                    self.queue.task_done()
                    if DEBUG:
                        print "DB dequeued."
            except IOError as e:
                print "DB Dequeue IOError(%d)-%s:%s" % (e.errno, e.strerror, e.message)
            finally:
                self.lock.release()
            self._stop.wait(0.5)

    def create_db(self):
        """ Create table local, bind and record """
        if os.path.exists(self.path):
            with sqlite3.connect(self.path) as con:
                con.execute('''CREATE TABLE IF NOT EXISTS record (
                    time INTEGER NOT NULL PRIMARY KEY,
                    decision INTEGER NOT NULL DEFAULT 0,
                    response INTEGER NOT NULL DEFAULT 0
                    )''')
            os.chmod(self.path, 0664)

    def putRecord(self,recordtuple):
        """ Insert entry into record table 
            @param recordtuple: (time, decision) ~ (INTEGER, INTEGER)"""
        with sqlite3.connect(self.path) as con:
            try:
                res = con.execute('INSERT INTO record(time,decision) VALUES (?, ?)', recordtuple)
            except:
                pass

    def putRecordForFN(self,recordtuple):
        """ Insert entry into record table for FN case
            @param recordtuple: (time, response) ~ (INTEGER, INTEGER)"""
        with sqlite3.connect(self.path) as con:
            try:
                res = con.execute('INSERT INTO record(time,response) VALUES (?, ?)', recordtuple)
            except:
                pass

    def updateRecord(self,recordtuple):
        """ Update entry in record table 
            @param recordtuple: (response, time) ~ (INTEGER, INTEGER)"""
        with sqlite3.connect(self.path) as con:
            try:
                res = con.execute('UPDATE record SET response=? WHERE time=?', recordtuple)
            except:
                pass

    def stop(self):
        if DEBUG:
            print "DB stopped."
        self._stop.set()

    def set_permission(self):
        if not os.path.isfile(self.path):
            f = open(self.path, 'wb')
            f.close()
            os.chmod(self.path, 0664)


def db_enqueue(queue, lock, tag, custom_tuple):
    """
    Enqueue database operation into db_queue
    :param queue: db_queue
    :param lock: db_lock
    :param tag: 'INSERT' or 'UPDATE'
    :param custom_tuple: data
    """
    try:
        lock.acquire()
        queue.put((tag, custom_tuple))
        if DEBUG:
            print "DB enqueued."
    except IOError as e:
            print "DB Enqueue IOError(%d)-%s:%s" % (e.errno, e.strerror, e.message)
    finally:
        lock.release()


if __name__ == '__main__':
    db = DBHelper(os.getcwd())
    db.createDB()
    #db.putBind(('asda','sdfsd'))
    #db.clearBind()
    #print getBind()
    import time
    t = int(time.time())
    db.putRecord((t, 1))
    db.updateRecord((2 , t))
