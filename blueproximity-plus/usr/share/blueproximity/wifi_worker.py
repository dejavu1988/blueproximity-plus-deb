#!/usr/bin/env python

import subprocess
import threading
import time
import os
import sys
from os import path
import commands
from log import Logging

TAG = 'WIFI'


#======================================================================================================================

#--- Class that calls iwlist periodically
#--- and parses its output:

class WifiScan(threading.Thread):

    def __init__(self, logging, wifi_dict):
        threading.Thread.__init__(self)
        self.wifiNetworks = wifi_dict
        self.interval = 2
        #self.networkInterface = 'wlan0' #deprecated: no dedicated name of wireless interface
        self.scanning = False
        self.time_init = 0
        self.log = logging

    def run(self):
        self.scanning = True
        self.log.log(TAG,'WiFi scan started')
        self.time_init = int(time.time()*1000)
        while (self.time_init + 10000 >= int(time.time()*1000)):
            self.scanForWifiNetworks()
            self.log.log(TAG,'WiFi inquiry once')
            time.sleep(self.interval)
        
        self.scanning = False
        self.log.log(TAG,'WiFi scan terminated')
        #print self.wifiNetworks


    def getWifiNetworksList(self):
        result = []
        for k,v in self.wifiNetworks.iteritems():
            result.append(v)
        return result

    def scanForWifiNetworks(self):
        #print 'scan triggered'
        output = ""
        command = ["iwlist", "scanning"]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.wait()
        #print 'waiting'
        (stdoutdata, stderrdata) = process.communicate();
        output =  stdoutdata
        #print 'Output '+ output
        self.parseIwlistOutput(output)

    def cutFrom(self, s, pattern):
        index = s.find(pattern)
        if(index>-1):
            return s[index+len(pattern):]
        else:
            return ""

    def cutTo(self, s, pattern):
        index = s.find(pattern)
        if(index>-1):
            return s[:index]
        else:
            return s

    def parseIwlistOutput(self, output):
        output = self.cutFrom(output, "Address:")
        while (output!=""):
            entry = self.cutTo(output, "Address:")
            address = ""
            signal = -100
            address = entry[1:18]   
            
            startIndex = entry.find("Signal")
            if(startIndex > -1):
                endIndex = entry.find("dBm", startIndex) -1
                signal = int(entry[startIndex+13:endIndex])

            key = address
            if self.wifiNetworks.has_key(key):
                count = self.wifiNetworks[key][2] +1
                signal = (signal + self.wifiNetworks[key][1] * (count - 1)) / count
            else:
                count = 1
            value = [address, signal, count]
            self.wifiNetworks[key] = value
        
            output = self.cutFrom(output, "Address:")


#======================================================================================================================

if __name__ == '__main__': 
    wifi_dict = {}
    w = WifiScan(wifi_dict)
    w.start()
    w.join()
    for addr in wifi_dict:
        print addr, wifi_dict[addr][1]

