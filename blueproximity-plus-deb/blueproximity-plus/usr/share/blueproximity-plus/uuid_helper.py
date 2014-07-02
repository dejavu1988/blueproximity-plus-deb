#!/usr/bin/python

import subprocess
import pwd


def get_uuid():
    """ Get the UUID alphanumeric string from Linux machine"""
    uuid = subprocess.Popen(['cat', '/sys/class/dmi/id/product_uuid'], stdout=subprocess.PIPE).communicate()[0]
    return uuid.split()[0]


def get_uid(uname):
    """ Get the UID from pwd"""
    pw_record = pwd.getpwnam(uname)
    uid = pw_record.pw_uid
    return uid

if __name__ == '__main__':
    print "UUID: " + str(get_uuid())
