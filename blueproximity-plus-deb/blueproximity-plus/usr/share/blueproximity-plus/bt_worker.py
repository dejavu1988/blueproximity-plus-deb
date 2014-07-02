#! /usr/bin/python
# performs a simple device inquiry, followed by a remote name request of each
# discovered device

import os
import sys
import time
import struct
import threading
import bluetooth._bluetooth as bluez
from log import *

TAG = 'BT'

class BluetoothScan(threading.Thread):
    
    def __init__(self, log_queue, log_lock, bt_dict, local_mac):
        threading.Thread.__init__(self)
        self.btDevices = bt_dict
        self.dev_id = 0
        self.scanning = False
        self.time_init = 0
        self.log_queue = log_queue
        self.log_lock = log_lock
        self.local_mac = local_mac
        # Add local BT MAC record with default -40 rssi
        self.btDevices[local_mac] = [local_mac, -40, 1]

    def run(self):
        self.scanning = True
        self.log(TAG,'Bluetooth scan started')
        self.time_init = int(time.time()*1000)
        try:
            sock = bluez.hci_open_dev(self.dev_id)
        except:
            print "error accessing bluetooth device..."
            sys.exit(1)
        self.log(TAG,'BT device accessed')

        mode = 0
        try:
            mode = read_inquiry_mode(sock)
        except Exception, e:
            print "error reading inquiry mode.  "
            #sys.exit(1)
        self.log(TAG,'Read inquiry mode')
        
        if mode != 1:
            #print "writing inquiry mode..."
            try:
                result = write_inquiry_mode(sock, 1)
            except Exception, e:
                print "error writing inquiry mode.  Are you sure you're root?"
                sys.exit(1)
            self.log(TAG,'Write inquiry mode')
        
        while (self.time_init + 10000 >= int(time.time()*1000)):
            
            device_inquiry_with_with_rssi(sock, self.btDevices)
            self.log(TAG,'BT inquiry once')

        self.scanning = False
        self.log(TAG,'Bluetooth scan terminated')

    def log(self, tag, msg):
        log(self.log_queue, self.log_lock, tag, msg)

def read_inquiry_mode(sock):
        """returns the current mode, or -1 on failure"""
        # save current filter
        old_filter = sock.getsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, 14)

        # Setup socket filter to receive only events related to the
        # read_inquiry_mode command
        flt = bluez.hci_filter_new()
        opcode = bluez.cmd_opcode_pack(bluez.OGF_HOST_CTL, bluez.OCF_READ_INQUIRY_MODE)
        bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
        bluez.hci_filter_set_event(flt, bluez.EVT_CMD_COMPLETE);
        bluez.hci_filter_set_opcode(flt, opcode)
        sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, flt )

        # first read the current inquiry mode.
        bluez.hci_send_cmd(sock, bluez.OGF_HOST_CTL, bluez.OCF_READ_INQUIRY_MODE )

        pkt = sock.recv(255)

        status,mode = struct.unpack("xxxxxxBB", pkt)
        if status != 0: mode = -1

        # restore old filter
        sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, old_filter )
        return mode    

def write_inquiry_mode(sock, mode):
        """returns 0 on success, -1 on failure"""
        # save current filter
        old_filter = sock.getsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, 14)

        # Setup socket filter to receive only events related to the
        # write_inquiry_mode command
        flt = bluez.hci_filter_new()
        opcode = bluez.cmd_opcode_pack(bluez.OGF_HOST_CTL, bluez.OCF_WRITE_INQUIRY_MODE)
        bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
        bluez.hci_filter_set_event(flt, bluez.EVT_CMD_COMPLETE);
        bluez.hci_filter_set_opcode(flt, opcode)
        sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, flt )

        # send the command!
        bluez.hci_send_cmd(sock, bluez.OGF_HOST_CTL, bluez.OCF_WRITE_INQUIRY_MODE, struct.pack("B", mode) )

        pkt = sock.recv(255)

        status = struct.unpack("xxxxxxB", pkt)[0]

        # restore old filter
        sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, old_filter )
        if status != 0: return -1
        return 0

def device_inquiry_with_with_rssi(sock, btDevices):
        # save current filter
        old_filter = sock.getsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, 14)

        # perform a device inquiry on bluetooth device #0
        # The inquiry should last 8 * 1.28 = 10.24 seconds
        # before the inquiry is performed, bluez should flush its cache of
        # previously discovered devices
        flt = bluez.hci_filter_new()
        bluez.hci_filter_all_events(flt)
        bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
        sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, flt )

        duration = 4
        max_responses = 255
        cmd_pkt = struct.pack("BBBBB", 0x33, 0x8b, 0x9e, duration, max_responses)
        bluez.hci_send_cmd(sock, bluez.OGF_LINK_CTL, bluez.OCF_INQUIRY, cmd_pkt)

        #results = []

        done = False
        while not done:
            pkt = sock.recv(255)
            ptype, event, plen = struct.unpack("BBB", pkt[:3])
            if event == bluez.EVT_INQUIRY_RESULT_WITH_RSSI:
                pkt = pkt[3:]
                nrsp = struct.unpack("B", pkt[0])[0]
                for i in range(nrsp):
                    addr = bluez.ba2str( pkt[1+6*i:1+6*i+6] )
                    rssi = struct.unpack("b", pkt[1+13*nrsp+i])[0]
                    if btDevices.has_key(addr):
                        count = btDevices[addr][2] + 1
                        rssi = (rssi + btDevices[addr][1] * (count - 1)) / count
                    else:
                        count = 1
                    btDevices[addr] = [addr,rssi,count]
                    #results.append( ( addr, rssi ) )
                    #print "[%s] RSSI: [%d]" % (addr, rssi)
            elif event == bluez.EVT_INQUIRY_COMPLETE:
                done = True
            else:
                pass

        # restore old filter
        sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, old_filter )

        #return results


#======================================================================================================================

if __name__ == '__main__': 
    bt_dict = {}
    b = BluetoothScan(bt_dict)
    b.start()
    b.join()
    for addr in bt_dict:
        print addr, bt_dict[addr][1]
