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
from log import *

TAG = 'CONN'

class Client(threading.Thread):
    def __init__(self, udir, db, db_queue, db_lock, log_queue, log_lock, deviceUuid, sample):
        threading.Thread.__init__(self)
        self.uuid = deviceUuid
        self.path = udir
        self.dbhelper = db
        self.db_queue = db_queue
        self.db_lock = db_lock
        self.inqueue = 'queue2' #self.uuid
        self.outqueue = 'queue1' #self.uuid + '-r'
        self.connection = None
        self.channel = None
        self.sample = sample
        self.statusResponse = 0
        self.log_queue = log_queue
        self.log_lock = log_lock

    def run(self): 
        self.log(TAG,'Start Connection')
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

        self.sendUUID()
        self.channel.basic_consume(self.callback,
                      queue=self.inqueue,
                      no_ack=True)
        print 'Start consuming...'
        self.log(TAG,'Start consuming')
        self.channel.start_consuming()


    def callback(self, ch, method, properties, body):
        """Callback on reception"""
        #print " [x] Received %r" % (body,)

        dict_msg = self.parse(body)
        print 'Received msg['+dict_msg['id']+']'
        self.log(TAG,'Received msg['+dict_msg['id']+']')

        if dict_msg['id'] == 'ID':
            #not for bind, but for initial connection: 
            #give Device uuid info to declare current Terminal
            #in case of multiple Terminals
            #self.recordBindInfo(dict_msg)
            #record = self.loadFromPref()
            restuple = self.dbhelper.getBind()
            if not restuple[0]:
                self.dbhelper.putBind((dict_msg['uid'],''))
                print 'Put Bind'
        elif dict_msg['id'] == 'FB':
            self.handleFeedback(dict_msg['ts'] ,dict_msg['val'])
        elif dict_msg['id'] == 'CSV':
            tmpts = int(dict_msg['ts'])
            tmppath = self.path+'/pool/'+str(tmpts)
            self.sample.getRemoteSensor().updateFromCSV(tmpts, dict_msg['val'])
            self.sample.getRemoteSensor().exportToCsv(tmppath+'/1.csv')
        elif dict_msg['id'] == 'WAV':
            tmpts = int(dict_msg['ts'])
            self.sample.getRemoteSensor().updateFromWAV(tmpts, dict_msg['val'])
            self.channel.queue_purge(queue=self.inqueue)
            print 'Queues purged.'

    def send(self, msg):
        """Send message with existing channel"""
        self.channel.basic_publish(exchange='',
                      routing_key=self.outqueue,
                      body=msg)
        print " [x] Sent %r" % (msg,)

    def purge(self):
        print 'Purge queues'
        self.channel.queue_purge(queue=self.inqueue)    # clear msg in queue
        self.channel.queue_purge(queue=self.outqueue)
        self.log(TAG,'Queues purged')

    def quit(self):    
        """ Quit thread"""
        self.channel.stop_consuming()
        self.connection.close()
        self.log(TAG,'Connection & channel closed')

    def parse(self,data):
        """ Parse json string to dict msg"""
        return json.loads(data)

    def recordBindInfo(self, data):
        """Record received uuid msg to pref.json, key='id'"""
        #dumpToPref(data)
        pass

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
        print "Send Result: "+json_msg
        self.send(json_msg+'\n')
        self.log(TAG,"Send Result: "+json_msg)
        tmp_decision = (1 if 'T' in decision else 0)
        self.db_enqueue('INSERT', (timestamp, tmp_decision))

    def dumpToPref(self, dict_msg):
        """ Dump dict msg to json file pref.json"""
        filePath = 'pref.json'
        f = open(filePath,'w')
        json.dump(dict_msg, f)
        f.close()

    def loadFromPref(self):
        """ Load json from pref.json"""
        filePath = 'pref.json'
        f = open(filePath,'r')
        data = json.load(f)
        f.close()
        return data

    def log(self, tag, msg):
        log(self.log_queue, self.log_lock, tag, msg)

    def db_enqueue(self, tag, custom_tuple):
        db_enqueue(self.db_queue, self.db_lock, tag, custom_tuple)

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
        self.db_enqueue('UPDATE', (int(val), int(ts)))


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
