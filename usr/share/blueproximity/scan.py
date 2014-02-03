#!/usr/bin/env python

import threading
from audio_worker import *
#from gps_worker import *
from wifi_worker import *
from bt_worker import *
#from uuid_helper import *
from sensor import *
from log import Logging

"""Pass a new Sensor Object to store local scanning results (raw)"""
TAG = 'SCAN'

class Scan(threading.Thread):
    def __init__(self, udir, logging, sensor):
        threading.Thread.__init__(self)
        self.path = udir
        self.sensor = sensor
        self.log = logging

    def run(self):
        self.log.log(TAG,'Scan started')
        gpsDict = {}
        gpsTsDict = {}
        gpsCoordList = []
        wifiDict = {}
        btDict = {}
        threads = []
        #gThr = GpsScan(self.log, gpsDict,gpsTsDict,gpsCoordList)
        wThr = WifiScan(self.log, wifiDict)
        bThr = BluetoothScan(self.log, btDict)
        aThr = AudioScan(self.log, self.path+'/pool/'+str(self.sensor.getTime()))
        #threads.append(gThr)
        threads.append(wThr)
        threads.append(bThr)
        threads.append(aThr)
        self.log.log(TAG,'Scan thread pool initialized')
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.log.log(TAG,'Scan thread pool done')
        #exportToCsv('tmp.csv',wifiDict,btDict,gpsDict,gpsTsDict,gpsCoordList)
        commitToObjects(self.path, self.sensor,wifiDict,btDict,gpsDict,gpsTsDict,gpsCoordList)

#def exportToCsv(filepath,wifiDict,btDict,gpsDict,gpsTsDict,gpsCoordList):
#    uuid = getUuid()
#    with open(filepath, 'w+') as f:
#        f.write('0#'+uuid+'#'+'\n')
#        # WiFi raw data
#        for key in wifiDict:
#            f.write('1#'+key+'#'+str(wifiDict[key][1])+'\n')
#        # Bluetooth raw data
#        for key in btDict:
#            f.write('2#'+key+'#'+str(btDict[key][1])+'\n')
#        # GPS raw data (combined)
#        for key in gpsDict:
#            f.write('3#'+str(key)+'#'+str(gpsDict[key][1])+'\n')
#        # GPS raw data (timed)
#        for key in gpsTsDict:
#            f.write('4#'+str(key)+'#'+gpsTsDict[key][1]+'\n')
#        if len(gpsCoordList) > 0:
#           f.write('5#'+gpsCoordList[-1]+'\n')

def commitToObjects(path, s, wifiDict,btDict,gpsDict,gpsTsDict,gpsCoordList):
    """s: Sensor object"""
    gps = {}
    gpst = {}
    coord = {}
    wifi = {}
    bt = {}
    # WiFi raw data
    for key in wifiDict:
        wifi[key] = wifiDict[key][1]
    # Bluetooth raw data
    for key in btDict:
        bt[key] = btDict[key][1]
    # GPS raw data (combined)
    for key in gpsDict:
        gps[key] = gpsDict[key][1]
    # GPS raw data (timed)
    for key in gpsTsDict:
        gpst[key] = gpsTsDict[key][1]
    if len(gpsCoordList) > 0:
        coordlist = gpsCoordList[-1].split('#')
        coord[coordlist[0]] = coordlist[1]

    s.update(wifi, bt, gps, gpst, coord)
    wavPath = path+'/pool/'+str(s.getTime()) + '/0.wav'
    s.updateAudio(wavPath)
    s.setCsvStatus()
    s.setWavStatus()
    s.exportToCsv(path+'/pool/'+str(s.getTime()) + '/0.csv')


if __name__ == '__main__':
    """obselete test"""
    sample = Sample()
    sample.clearSensors()
    sample.updateTime()
    sc = Scan(sample.getLocalSensor())
    sc.start()
    sc.join()
