#! /usr/bin/python

import os
from gps import *
import time
import threading
from log import Logging

TAG = 'GPS'

gpsd = None #seting the global variable

class GpsScan(threading.Thread):
    def __init__(self, logging, gps_dict, gps_timed_dict, gps_coord_list):
        threading.Thread.__init__(self)
        global gpsd #bring it in scope
        gpsd = gps(mode=WATCH_ENABLE) #starting the stream of info
        self.gpsSats = gps_dict
        self.gpsTsSats = gps_timed_dict
        self.gpsCoords = gps_coord_list
        self.current_value = None
        self.running = False #setting the thread running to true
        self.time_init = 0
        self.log = logging
        
    def isScanning(self):
        return self.running
                
    def run(self):
        global gpsd
        self.running = True
        self.log.log(TAG,'GPS scan started')
        self.time_init = int(time.time()*1000)
        while (self.time_init + 10000 >= int(time.time()*1000)):
            gpsd.next() #this will continue to loop and grab EACH set of gpsd info to clear the buffer
            ts = (int(time.time()*1000) - self.time_init)/1000
            prn_entry = []
            #snr_entry = []
            for sat in gpsd.satellites:
                sat_attrs = str(sat).split()
                prn = int(sat_attrs[1])
                snr = int(sat_attrs[7])
                prn_entry.append(prn)
                #snr_entry.append(snr)
                if self.gpsSats.has_key(prn):
                    count = self.gpsSats[prn][2] + 1
                    snr = (snr + self.gpsSats[prn][1] * (count - 1)) / count
                else:
                    count = 1
                self.gpsSats[prn] = [prn,snr,count]
            st = str(prn_entry).replace(' ','')
            st = st[1:len(st)-1]
            self.gpsTsSats[ts] = [ts,st]
            coord = str(gpsd.fix.longitude)+','+str(gpsd.fix.latitude)+','+str(gpsd.fix.altitude)+'#'+str(max(gpsd.fix.epx,gpsd.fix.epy))
            self.gpsCoords.append(coord)
            time.sleep(0.95) #set to whatever
        
        self.running = False
        self.log.log(TAG,'GPS scan terminated')
              
if __name__ == '__main__':
    gps_dict = {}
    gps_timed_dict = {}
    gps_coord_list = []
    g = GpsScan(gps_dict, gps_timed_dict, gps_coord_list)
    g.start()
    g.join()
    for key in gps_dict:
        print key, gps_dict[key][1]
    print
    for key in gps_timed_dict:
        print key, gps_timed_dict[key][1]
    print
    print gps_coord_list[-1]
