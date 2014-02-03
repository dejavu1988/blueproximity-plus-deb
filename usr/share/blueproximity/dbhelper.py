#!/usr/bin/env python

import sqlite3
TAG = 'DB'
#self.dbpath = 'record.db'

class DBHelper():
    def __init__(self, udir):
        self.dbpath = udir+'/record.db'

    def createDB(self):
        """ Create table local, bind and record """
        with sqlite3.connect(self.dbpath) as con:
            con.execute('''CREATE TABLE IF NOT EXISTS local (
                id TEXT NOT NULL PRIMARY KEY,
                bdaddr TEXT NOT NULL DEFAULT ''
                )''')
            con.execute('''CREATE TABLE IF NOT EXISTS bind (
                id TEXT NOT NULL PRIMARY KEY,
                bdaddr TEXT NOT NULL DEFAULT ''
                )''')
            con.execute('''CREATE TABLE IF NOT EXISTS record (
                time INTEGER NOT NULL PRIMARY KEY,
                decision INTEGER NOT NULL DEFAULT 0,
                response INTEGER NOT NULL DEFAULT 0
                )''')

    def clearBind(self):
        """ Clear bind info"""
        with sqlite3.connect(self.dbpath) as con:
            con.execute('DELETE FROM bind')

    def putBind(self,bindtuple):
        """ Insert entry into bind table 
            @param bindtuple: (bindID,bindBDADDR) ~ (TEXT, TEXT)"""
        with sqlite3.connect(self.dbpath) as con:
            con.execute('INSERT INTO bind VALUES (?, ?)', bindtuple)

    def putLocal(self,localtuple):
        """ Insert entry into local table 
            @param localtuple: (ID,BDADDR) ~ (TEXT, TEXT)"""
        with sqlite3.connect(self.dbpath) as con:
            con.execute('INSERT INTO local VALUES (?, ?)', localtuple)

    def putRecord(self,recordtuple):
        """ Insert entry into record table 
            @param recordtuple: (time, decision) ~ (INTEGER, INTEGER)"""
        with sqlite3.connect(self.dbpath) as con:
            res = con.execute('INSERT INTO record(time,decision) VALUES (?, ?)', recordtuple)

    def updateRecord(self,recordtuple):
        """ Update entry in record table 
            @param recordtuple: (response, time) ~ (INTEGER, INTEGER)"""
        with sqlite3.connect(self.dbpath) as con:
            res = con.execute('UPDATE record SET response=? WHERE time=?', recordtuple)

    def getLocal(self):
        """ Get local tuple (ID, BDADDR)
            @return isRegistered, id, bdaddr"""
        res = None
        with sqlite3.connect(self.dbpath) as con:
            res = con.execute('SELECT * FROM local')
        row = res.fetchone()
        if row != None:
            return True, row[0], row[1]
        else:
            return False, '', ''

    def getBind(self):
        """ Get bind tuple (ID, BDADDR)
            @return isBind, bindID, bindAddr"""
        res = None
        with sqlite3.connect(self.dbpath) as con:
            res = con.execute('SELECT * FROM bind')
        row = res.fetchone()
        if row != None:
            return True, row[0], row[1]
        else:
            return False, '', ''


if __name__ == '__main__':
    #createDB()
    #putBind(('asda','sdfsd'))
    #clearBind()
    #print getBind()
    import time
    t = int(time.time())
    putRecord((t, 1))
    updateRecord((2 , t))
