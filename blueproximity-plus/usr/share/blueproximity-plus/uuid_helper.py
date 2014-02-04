#!/usr/bin/python
'''UUID can be extracted for setup runonce and stored in pref'''
import subprocess
import pwd
import os
import dbhelper

def getUuid():
    """ Get the UUID alphanumeric string from Linux machine"""
    uuid = subprocess.Popen(['cat','/sys/class/dmi/id/product_uuid'],stdout=subprocess.PIPE).communicate()[0]
    return uuid.split()[0]

def getUid(uname):
    """ Get the UID from pwd"""
    pw_record = pwd.getpwnam(uname)
    uid = pw_record.pw_uid
    return uid
