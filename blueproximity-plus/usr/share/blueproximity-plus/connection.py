#!/usr/bin/env python
# This is for rabbitmq demo file

import sys 
import threading
import json
import subprocess 
import time
from uuid_helper import *
import pika
from sensor import *
from dbhelper import *
from calculate import *
from log import *

TAG = 'CONN'

class Client(threading.Thread):
    def __init__(self, udir, db, db_queue, db_lock, log_queue, log_lock, deviceUuid, sample, dec_queue, dec_lock):
        threading.Thread.__init__(self)
        self.uuid = deviceUuid
        self.path = udir
        self.dbhelper = db
        self.db_queue = db_queue
        self.db_lock = db_lock
        self.inqueue = deviceUuid
        self.outqueue = ''
        self.connection = None
        self.channel = None
        self.sample = sample
        self.statusResponse = 0
        self.log_queue = log_queue
        self.log_lock = log_lock
        self.dec_queue = dec_queue # decision queue
        self.dec_lock = dec_lock # decision lock
        self.running = False

    def run(self):
        while not self.outqueue:
            time.sleep(1)
        flag = True
        while flag:
            self.log(TAG,'Start Connection')
            try:
                self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='54.229.32.28'))
            except:
                self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='54.229.32.28'))
            self.channel = self.connection.channel()
            print 'Connection and Channel ready.'
            self.log(TAG,'Connection & Channel Ready')

            self.channel.queue_declare(queue=self.inqueue)  #Queue from Device to Terminal: named with TerminalUUID
            self.channel.queue_declare(queue=self.outqueue) #Queue from Terminal to Device: named with TerminalUUID+'-r'
            print 'Queues declared.'
            self.log(TAG,'Queues declared')

            self.channel.queue_purge(queue=self.inqueue)    # clear msg in queue
            self.channel.queue_purge(queue=self.outqueue)
            print 'Queues purged.'
            self.log(TAG,'Queues purged')

            self.channel.basic_consume(self.callback,
                              queue=self.inqueue,
                              no_ack=True)
            print 'Start consuming...'
            self.log(TAG,'Start consuming')
            try:
                self.running = True
                self.channel.start_consuming()
            except:
                self.running = False
                #self.channel.stop_consuming()
            self.connection.close()

    def callback(self, ch, method, properties, body):
        """Callback on reception"""
        #print " [x] Received %r" % (body,)

        dict_msg = self.parse(body)
        print 'Received msg['+dict_msg['id']+']'
        self.log(TAG,'Received msg['+dict_msg['id']+']')

        if dict_msg['id'] == 'FB':
            self.handleFeedback(dict_msg['ts'] ,dict_msg['val'])
        elif dict_msg['id'] == 'CSV':
            tmpts = int(dict_msg['ts'])
            tmppath = os.path.join(self.path,str(tmpts))
            self.sample.remote.updateFromCSV(tmpts, dict_msg['val'])
            self.sample.remote.exportToCsv(os.path.join(tmppath,'1.csv'))
        elif dict_msg['id'] == 'WAV':
            tmpts = int(dict_msg['ts'])
            self.sample.remote.updateFromWAV(tmpts, dict_msg['val'])
            if self.sample.getStatus():
                dec_enqueue(self.dec_queue, self.dec_lock, 'ready')
            self.channel.queue_purge(queue=self.inqueue)
            print 'Queues purged.'

    def send(self, msg):
        """Send message with existing channel"""
        if self.running:
            self.channel.basic_publish(exchange='',
                        routing_key=self.outqueue,
                        body=msg)
            print " [x] Sent %r" % (msg,)

    def purge(self):
        if self.running:
            print 'Purge queues'
            self.channel.queue_purge(queue=self.inqueue)    # clear msg in queue
            self.channel.queue_purge(queue=self.outqueue)
            self.log(TAG,'Queues purged')

    def quit(self):    
        """ Quit thread"""
        if self.running:
            self.channel.stop_consuming()
            self.connection.close()
            self.log(TAG,'Connection & channel closed')

    def parse(self,data):
        """ Parse json string to dict msg"""
        return json.loads(data)

    def sendUUID(self):
        """ Send UUID"""
        dict_msg = {'id':'ID', 'uid':self.uuid}
        json_msg = json.dumps(dict_msg)
        print "Send UUID: "+json_msg
        self.send(json_msg+'\n')
        self.log(TAG,'Send UUID: '+json_msg)

    def sendScan(self, ts):
        """ Send SCAN msg to device-side"""
        dict_msg = {'id':'SCAN', 'ts':str(ts)}
        json_msg = json.dumps(dict_msg)
        print "Send SCAN: "+json_msg
        self.send(json_msg+'\n')
        self.log(TAG,"Send SCAN: "+json_msg)

    def sendResult(self, event, decision, timestamp):
        """
        Send Comparison Result msg to device-side
        :event: Y/N (unlock/lock)
        :decision: T/F (colocated/non-colocated)
        :timestamp: int
        """
        dict_msg = {'id':'RS', 'event': event, 'val':decision, 'ts':timestamp}
        json_msg = json.dumps(dict_msg)
        self.send(json_msg+'\n')
        self.log(TAG,"Send Result: "+json_msg)
        tmp_decision = (1 if 'T' in decision else 0)
        self.db_enqueue('INSERT', (timestamp, tmp_decision))

    def log(self, tag, msg):
        log(self.log_queue, self.log_lock, tag, msg)

    def db_enqueue(self, tag, custom_tuple):
        db_enqueue(self.db_queue, self.db_lock, tag, custom_tuple)

    def dec_enqueue(self, tag):
        dec_enqueue(self.dec_queue, self.dec_lock, tag)

    #def getStatus(self):
    #    return self.statusCSV and self.statusWAV

    #def resetStatus(self):
    #    self.statusCSV = False
    #    self.statusWAV = False
    
    def getResponseStatus(self):
        return self.statusResponse

    def resetResponseStatus(self):
        self.statusResponse = 0

    def handleFeedback(self, ts, val):
        """
        Feedback: TP - 1, FP - 2, TN - 3, FN - 4
        """
        print 'Response: '+ ts + ':' + val
        self.log(TAG,"Got Response: "+ ts + ':' + val)
        self.statusResponse = int(val)
        if ts != "":    #Normal response
            self.db_enqueue('UPDATE', (int(val), int(ts)))
        else:   #Proactive FN response
            curts = int(time.time())
            self.db_enqueue('ADDFN', (curts, int(val)))


if __name__ == "__main__":
    #Logging needed
    l = Logging()
    l.start()
    uuid = get_uuid()
    sample = Sample()
    client = Client(l, uuid, sample)
    client.start()
    time.sleep(5)
    client.sendUUID()
    # Test of sensor/sample:
    sample.clearSensors()
    sample.updateTime()
    client.sendScan(sample.getTime())
    time.sleep(40)
    sample.clearSensors()
    sample.updateTime()
    client.sendScan(sample.getTime())
    # Test of response/feedback events:
    client.sendResult('Y','T', time.time())
    time.sleep(20)
    client.sendResult('Y','F', time.time())
    time.sleep(20)
    client.sendResult('N','T', time.time())
    time.sleep(20)
    #client.sendResult('N','F', time.time())
