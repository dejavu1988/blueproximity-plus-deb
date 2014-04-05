#!/usr/bin/env python

import sys
import math
import time
import os
import base64
from audio_proc import getXCorrandDistFromWav
from math import log, exp, sqrt
from decision import decision
from uuid_helper import *
from dbhelper import *

class Sensor():
    """Sensor info in dictionaries, and timestamp (in sec)"""
    def __init__(self,udir):
        self.path = udir
        self.wifi = {}
        self.bluetooth = {}
        self.audio = ''
        self.gps = {}
        self.gpst = {}
        self.coord = {}
        self.time = 0  # timestamp in sec (int)
        self.uuid = ''  # uuid of sensor source (string)
        self.csvstatus = False  # status: if csv data is filled
        self.wavstatus = False  # status: if wav data is filled

    def getTime(self):
        return self.time
    
    def setTime(self, ts):
        self.time = ts

    def getUuid(self):
        return self.uuid

    def setUuid(self, uuid):
        self.uuid = uuid

    def setCsvStatus(self):
        self.csvstatus = True

    def setWavStatus(self):
        self.wavstatus = True

    def getStatus(self):
        return self.csvstatus and self.wavstatus

    def setNew(self):
        os.mkdir(self.path+'/pool/'+str(self.time), 0755)
        return self.path+'/pool/'+str(self.time)

    def update(self, wifi, bluetooth, gps, gpst, coord):
        self.wifi = wifi
        self.bluetooth = bluetooth
        #self.audio = audio
        self.gps = gps
        self.gpst = gpst
        self.coord = coord

    def updateAll(self, wifi, bluetooth, gps, gpst, coord, audioPath):
        self.wifi = wifi
        self.bluetooth = bluetooth
        self.audio = audioPath
        self.gps = gps
        self.gpst = gpst
        self.coord = coord

    def setSensor(self, sensor):
        self.wifi = sensor.getWifiRaw()
        self.bluetooth = sensor.getBluetoothRaw()
        #self.audio = audio
        self.gps = sensor.getGpsRaw()
        self.gpst = sensor.getGpstRaw()
        self.coord = sensor.getGpsCoordRaw()
        self.time = sensor.getTime()

    def updateAudio(self, audioPath):
        self.audio = audioPath

    def getWifiRaw(self):
        return self.wifi

    def getBluetoothRaw(self):
        return self.bluetooth

    def getAudioRaw(self):
        return self.audio

    def getGpsRaw(self):
        return self.gps

    def getGpstRaw(self):
        return self.gpst

    def getGpsCoordRaw(self):
        return self.coord

    def getDataStatus(self):
        """
        Bits of data filling status: 1-wifi, 2-bluetooth
        """
        tmp = 0
        if len(self.wifi) > 0:
            tmp ^= 1
        if len(self.bluetooth) > 0:
            tmp ^= 2
        return tmp

    def clear(self):
        self.wifi = {}
        self.bluetooth = {}
        self.audio = ''
        self.gps = {}
        self.gpst = {}
        self.coord = {}
        self.csvstatus = False
        self.wavstatus = False

    def updateFromCSV(self, ts, data):
        """For remote"""
        """Store csv string with entry-delimiter ';' into dictionary
            the returned dictionary is keyed with 'wifi'/'bt', and
            valued with info tuples, e.g. (00:3A:9A:0F:A4:40,-71)"""
        if ts == self.time:
            wifiDict = {}
            btDict = {}
            gpsDict = {}
            gpstDict = {}
            gpsCoordDict = {}
            entryList = data.split(';')
            for entry in entryList:
                tmpList = entry.split('#')
                if tmpList[0] == '0':
                    if tmpList[1] != self.uuid:
                        self.setUuid(tmpList[1])
                elif tmpList[0] == '1':
                    wifiDict[tmpList[1]] = tmpList[2]
                elif tmpList[0] == '2':
                    btDict[tmpList[1]] = tmpList[2]
                elif tmpList[0] == '3':
                    gpsDict[tmpList[1]] = tmpList[2]
                elif tmpList[0] == '4':
                    gpstDict[tmpList[1]] = tmpList[2]
                elif tmpList[0] == '5':
                    gpsCoordDict[tmpList[1]] = tmpList[2]
            self.update(wifiDict,btDict,gpsDict,gpstDict,gpsCoordDict)
            self.setCsvStatus()

    def updateFromWAV(self, ts, data):
        """For remote"""
        """Data: Base64 hex-string, need transfer to wav, and save wav file path"""
        if ts == self.time:
            wavPath = self.path+'/pool/'+str(ts) + '/1.wav'
            self.updateAudio(wavPath)
            #os.mkdir(self.path+'/pool/'+str(ts), 0755)
            with open(wavPath, 'wb') as f:
                f.write(base64.decodestring(data))
            self.setWavStatus()

    def exportToCsv(self,filepath):
        """
        Export Sensor to Csv file
        """
        f= open(filepath, 'w')
        f.write('0#'+self.uuid+'#'+'\n')
        # WiFi raw data
        for key in self.wifi:
            f.write('1#'+key+'#'+str(self.wifi[key])+'\n')
        # Bluetooth raw data
        for key in self.bluetooth:
            f.write('2#'+key+'#'+str(self.bluetooth[key])+'\n')
        # GPS raw data (combined)
        for key in self.gps:
            f.write('3#'+str(key)+'#'+str(self.gps[key])+'\n')
        # GPS raw data (timed)
        for key in self.gpst:
            f.write('4#'+str(key)+'#'+str(self.gpst[key])+'\n')
        for key in self.coord:
            f.write('5#'+str(key)+'#'+str(self.coord[key])+'\n')
        f.close()

class Feature():
    def __init__(self):
        self.wifijacc = -1
        self.wifiabs = -1
        self.wifieucl = -1
        self.wifiexp = -1
        self.wifisumsqua = -1
        self.bluejacc = -1
        self.blueabs = -1
        self.audiocorr = -1
        self.audiofreq = -1
        self.gpsjacc = -1
        self.gpsabs = -1
        self.gpseucl = -1
        self.gpsexp = -1
        self.gpssubset = -1

    def clear(self):
        self.wifijacc = -1
        self.wifiabs = -1
        self.wifieucl = -1
        self.wifiexp = -1
        self.wifisumsqua = -1
        self.bluejacc = -1
        self.blueabs = -1
        self.audiocorr = -1
        self.audiofreq = -1
        self.gpsjacc = -1
        self.gpsabs = -1
        self.gpseucl = -1
        self.gpsexp = -1
        self.gpssubset = -1

    def setWifiJacc(self, val):
        self.wifijacc = val

    def setWifiAbs(self, val):
        self.wifiabs = val

    def setWifiEucl(self, val):
        self.wifieucl = val

    def setWifiExp(self, val):
        self.wifiexp = val

    def setWifiSumSquared(self, val):
        self.wifisumsqua = val

    def setBlueJacc(self, val):
        self.bluejacc = val

    def setBlueAbs(self, val):
        self.blueabs = val

    def setAudioCorr(self, val):
        self.audiocorr = val

    def setAudioFreq(self, val):
        self.audiofreq = val

    def setGpsJacc(self, val):
        self.gpsjacc = val

    def setGpsAbs(self, val):
        self.gpsabs = val

    def setGpsEucl(self, val):
        self.gpseucl = val

    def setGpsExp(self, val):
        self.gpsexp = val

    def setGpsSubset(self, val):
        self.gpssubset = val

    def getFeatures(self):
        return self.audiocorr, self.audiofreq, self.wifijacc, self.wifiabs, self.wifieucl, self.wifiexp, self.wifisumsqua, self.bluejacc, self.blueabs, self.gpsjaccwhole, self.gpsabs, self.gpseucl, self.gpsexp, self.gpssubset

    def toString(self):
        return str(self.audiocorr) + '#' + str(self.audiofreq) + '#' + str(self.wifijacc) + '#' + str(self.wifiabs) + '#' + str(self.wifieucl) + '#' + str(self.wifiexp) + '#' + str(self.wifisumsqua) + '#' + str(self.bluejacc) + '#' + str(self.blueabs) + '#' + str(self.gpsjaccwhole) + '#' + str(self.gpsabs) + '#' + str(self.gpseucl) + '#' + str(self.gpsexp) + '#' + str(self.gpssubset)

class Sample():
    """
    Sample: pair of sensor info
    """
    def __init__(self, udir, dbobj):
        self.path = udir
        self.dbhelper = dbobj
        self.time = 0
        self.local = Sensor(udir)
        self.remote = Sensor(udir)
        self.feature = Feature()
        self.decision = False    #default decision is False
        self.groundtruth = True     #default groundtruth is False
        #self.decisiontime = 0
        self.lifetime = 120 # lifetime of decision: 120s
        self.decisionOn = False
        self.scanstatus = 0 #scan status: 0-no scan; 1-scan triggered; 2-post scan

    def getLocalSensor(self):
        return self.local

    def getRemoteSensor(self):
        return self.remote

    def clearSensors(self):
        self.local.clear()
        self.remote.clear()
        self.feature.clear()

    def updateTime(self):
        self.time = int(time.time())
        self.local.setTime(self.time)
        self.remote.setTime(self.time)
        os.mkdir(self.path+'/pool/'+str(self.time), 0755)

    def getTime(self):
        return self.time

    def getStatus(self):
        return self.local.getStatus() and self.remote.getStatus()

    def setScanStatus(self, sta):
        self.scanstatus = sta

    def getScanStatus(self):
        return self.scanstatus

    def setDecision(self, decision):
        self.decision = decision

    def getDecision(self):
        return self.decision

    def dumpRecord(self):
        f = open('record.csv', 'w+')
        f.write(str(self.time) + '#' + str(self.decision) + '#' + self.feature.toString() + '\n')
        f.close()

    def isDecisionOn(self):
        """
        Is decision already done
        """
        return self.decisionOn

    def isExpired(self):
        """
        Is decision already expired
        """
        return self.time + self.lifetime < int(time.time())

    def calculateDecision(self):
        self.feature.setWifiJacc(self.getWifiJacc())
        self.feature.setWifiAbs(self.getWifiAbs())
        self.feature.setWifiEucl(self.getWifiEucl())
        self.feature.setWifiExp(self.getWifiExp())
        self.feature.setWifiSumSquared(self.getWifiSumSquared())
        self.feature.setBlueJacc(self.getBlueJacc())
        self.feature.setBlueAbs(self.getBlueAbs())
        self.feature.setGpsJacc(self.getGpsJacc())
        self.feature.setGpsAbs(self.getGpsAbs())
        self.feature.setGpsEucl(self.getGpsEucl())
        self.feature.setGpsExp(self.getGpsExp())
        self.feature.setGpsSubset(self.getGpsSubset())
        xcorr, dist = getXCorrandDistFromWav(self.local.getAudioRaw(), self.remote.getAudioRaw())
        self.feature.setAudioCorr(xcorr)
        self.feature.setAudioFreq(dist)
        self.decision = decision(self.feature.getFeatures())
        self.decisionOn = True
        if self.decision:
            self.dbhelper.putRecord(self.time, 1)
        else:
            self.dbhelper.putRecord(self.time, 0)
        return self.decision

    def jaccard(self, set1, set2):  
        """compute Jaccard distance of two sets: set1 and set2"""
        u = set.intersection(set1,set2)
        x = len(u)
        y = len(set1)+len(set2)-len(u)
        if y != 0 :
            ret = 1-(x*1.0/y*1.0)
        else:
            ret = 1
        return ret

    def getWifiJacc(self):
        set1 = set(self.local.getWifiRaw().keys())
        set2 = set(self.remote.getWifiRaw().keys())       
        if (len(set1)>0 and len(set2)>0): 
            dist = self.jaccard(set1, set2)
        else:
            dist = -1
        return round(dist,3)

    def getBluetoothJaccard(self):
        set1 = set(self.local.getBluetoothRaw().keys())
        set2 = set(self.remote.getBluetoothRaw().keys())
        if (len(set1)>0 and len(set2)>0): 
            dist = self.jaccard(set1, set2)
        else:
            dist = -1
        return round(dist,3)

    def getGpsJaccard(self):
        set1 = set(self.local.getGpsRaw().keys())
        set2 = set(self.remote.getGpsRaw().keys())
        if (len(set1)>0 and len(set2)>0): 
            dist = self.jaccard(set1, set2)
        else:
            dist = -1
        return round(dist,3)

    def build_vector(self, data1, data2, DEFAULT):
        vector1 = dict()
        vector2 = dict()
        key1 = set(data1.keys())
        key2 = set(data2.keys())
        keyset = key1.union(key2)
        for x in keyset:
            if x in data1:
                vector1[x] = float(data1[x])
            else:
                vector1[x] = DEFAULT
            if x in data2:
                vector2[x] = float(data2[x])
            else:
                vector2[x] = DEFAULT
        return (vector1, vector2)

    def distance_abs(self, data1, data2, DEFAULT): 
        if (len(data1)>0) and (len(data2)>0):
            v = self.build_vector(data1, data2, DEFAULT)
            v1 = v[0]
            v2 = v[1]
            sum_distance = 0
            for x in v1:
                sum_distance += abs(v1[x] - v2[x])
            distance = (sum_distance*1.0)/(len(v1)*1.0)
        else:
            distance = -1
        return distance

    def distance_eucl(self, data1, data2, DEFAULT):                
        if (len(data1)>0) and (len(data2)>0):
            v = self.build_vector(data1, data2, DEFAULT)
            v1 = v[0]
            v2 = v[1]
            sum_square = 0
            for x in v1:
                sum_square += abs(v1[x] - v2[x]) * abs(v1[x] - v2[x])
            distance = math.sqrt(sum_square)
        else:
            distance = -1
        return distance

    def distance_exp(self, data1, data2, DEFAULT):
        if (len(data1)>0) and (len(data2)>0):
            v = self.build_vector(data1, data2, DEFAULT)
            v1 = v[0]
            v2 = v[1]
            sum_exp = 0
            for x in v1:            
                try:
                    sum_exp += exp(abs(v1[x] - v2[x]))
                except Exception, e:
                    print "overflow with e of ", abs(v1[x] - v2[x])                  
            distance = (sum_exp*1.0)/(len(v1)*1.0)
        else:
            distance = -1
        return distance

    def getWifiAbs(self):
        dist = self.distance_abs(self.local.getWifiRaw(), self.remote.getWifiRaw(), -100)
        return round(dist,3)

    def getWifiEucl(self):
        dist = self.distance_eucl(self.local.getWifiRaw(), self.remote.getWifiRaw(), -100)
        return round(dist,3)

    def getWifiExp(self):
        dist = self.distance_exp(self.local.getWifiRaw(), self.remote.getWifiRaw(), -100)
        return round(dist,3)

    def getBluetoothAbs(self):
        dist = self.distance_abs(self.local.getBluetoothRaw(), self.remote.getBluetoothRaw(), -100)
        return round(dist,3)

    def distance_sum_squared(self, dict1, dict2):
        """"list1 and list2 contains values which keys are common in
        dict1 and dict2 return rank1 and rank2, where rank1 contains
        sorted orders of elements of list1, rank2 contains sorted
        orders of elements of list2. For example, (-70,-50,-80)
        returns (2,3,1)"""
        if (len(dict1)>0) and (len(dict2)>0):
            set1 = set(dict1.keys())
            set2 = set(dict2.keys())
            common = set1&set2 #intersection of two sets
            if len(common)>0:
                list1 = []
                list2 = []
                for i in common:
                    list1.append(float(dict1[i]))
                    list2.append(float(dict2[i]))
                tmp = sorted(enumerate(list1), key=lambda x: x[1])
                rank1 = [i[0]+1 for i in sorted(enumerate(tmp), key= lambda x: x[1] )]
                tmp = sorted(enumerate(list2), key=lambda x: x[1])
                rank2 = [i[0]+1 for i in sorted(enumerate(tmp), key= lambda x: x[1] )]
                distance = sum((rank1[i]-rank2[i])**2 for i in range(len(rank1))) #len(rank1)=len(rank2), sum of (ai-bi)**2
            else:
                distance = 10000
        else:
            distance = -1
        return distance

    def getWifiSumSquared(self):
        dist = self.distance_sum_squared(self.local.getWifiRaw(), self.remote.getWifiRaw().wifi)
        return round(dist,3)

    def getGpsAbs(self):
        dist = self.distance_abs(self.local.getGpsRaw(), self.remote.getGpsRaw(), 0)
        return round(dist,3)

    def getGpsEucl(self):
        dist = self.distance_eucl(self.local.getGpsRaw(), self.remote.getGpsRaw(), 0)
        return round(dist,3)

    def getGpsExp(self):
        dist = self.distance_exp(self.local.getGpsRaw(), self.remote.getGpsRaw(), 0)
        return round(dist,3)

    def subset(self, sdata1, sdata2):
        """count the number one entry contains set of satelittes which is subset of the corresponding entry in the other device """
        data1 = {}
        data2 = {}
        for key in sdata1.keys():
            prns = []
            prns = sdata1[key].split(',')
            data1[key] = set(prns)
        for key in sdata2.keys():
            prns = []
            prns = sdata2[key].split(',')
            data2[key] = set(prns)
        if (len(data1)>0) and (len(data2)>0):
            n_entry = 0
            subset_count = 0
            for key in data1:
                if key in data2:
                    n_entry += 1
                    set1 = data1[key]
                    set2 = data2[key]
                    if set1.issubset(set2) or set1.issuperset(set2):
                        subset_count += 1
            if n_entry != 0:
                p = subset_count/(n_entry*1.0)
            else:
                p = 0
        else:
            p = -1
        return p

    def getGpsSubset(self):
        dist = self.subset(self.local.getGpstRaw(), self.remote.getGpstRaw())
        return round(dist,3)



