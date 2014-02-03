#!/usr/bin/env python

'''
 The test script for child process uid switching
'''

import os
import subprocess
import sys
from uuid_helper import getUid

def deamon(uid):
    os.setuid(uid)

def lockcommand(uname):
    uid = getUid(uname)
    cmd = ['gnome-screensaver-command', '-l']

    process = subprocess.Popen(cmd, preexec_fn=deamon(uid), stdout = subprocess.PIPE, stderr = subprocess.PIPE)
 
    outs, errs = process.communicate()
    #print "process return code:", process.returncode
    #print "stderr:", errs
    #print "stdout:", outs

if __name__ == '__main__':
    uname = sys.argv[1]
    lockcommand(uname)
