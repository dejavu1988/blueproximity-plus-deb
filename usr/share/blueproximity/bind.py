#!/usr/bin/python
"""
Bind after BT pairing
via server
exchange entries
"""
from bluetooth import *
import json
import threading
from dbhelper import *
import time
from log import Logging

TAG = 'BIND'

class Bind(threading.Thread):

    def __init__(self, logging, conn):
        threading.Thread.__init__(self)
        self.server_sock = None
        self.serviceUUID = "94f39d29-7d6d-437d-973b-fba39e49d4ee"
        self.client_sock = None
        self.client_info = None
        self.on = True
        self.conn = conn
        self.log = logging

    def run(self):
        print 'Start Binding'
        self.log.log(TAG,'Start Binding')
        self.server_sock=BluetoothSocket( RFCOMM )
        self.server_sock.bind(("",PORT_ANY))
        self.server_sock.listen(1)

        port = self.server_sock.getsockname()[1]

        print "Ready for advertising Service."
        self.log.log(TAG,"Ready for advertising Service.")

        advertise_service( self.server_sock, "BindServer",
                   service_id = self.serviceUUID,
                   service_classes = [ self.serviceUUID, SERIAL_PORT_CLASS ],
                   profiles = [ SERIAL_PORT_PROFILE ],
                   #protocols = [ OBEX_UUID ]
                    )

        print "Waiting for connection on RFCOMM channel %d" % port
        self.log.log(TAG,'Waiting for connection on RFCOMM channel')
        
        #dbhelper.putBind(('104283-6542003011-1103', ''))

        self.client_sock, self.client_info = self.server_sock.accept()
        print "Accepted connection from ", self.client_info
        self.log.log(TAG,'Accepted connection')

#        self.conn.sendUUID()

#        while self.on:
#                print 'in loop'
#                time.sleep(5)
#                #self.conn.sendUUID()
#                bindtuple = dbhelper.getBind()
#                if bindtuple[0]:
#                    self.on = False

#        try:
#            while self.on:
#                data = self.client_sock.recv(1024)
#                if len(data) == 0: break
#                print "received [%s]" % data
#                dict_msg = json.loads(data)
#                if dict_msg.has_key('id') and dict_msg['id'] == 'ID':
#                    #self.dumpToPref(dict_msg)
#                    dbhelper.putBind((dict_msg['uid'],''))
#                    self.on = False
#        except IOError:
#            pass

#        print "disconnected"

        #self.client_sock.close()
        stop_advertising(self.server_sock)
        self.server_sock.close()
        print "all done"

    def dumpToPref(self, dict_msg):
        """ Dump dict msg to json file pref.json"""
        filePath = 'pref.json'
        f = open(filePath,'w')
        json.dump(dict_msg, f)
        f.close()

if __name__ == "__main__":
    b = Bind()
    b.start()
