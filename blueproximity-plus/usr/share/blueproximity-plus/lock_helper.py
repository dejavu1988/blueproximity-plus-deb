#!/usr/bin/env python

'''
 The test script for child process uid switching
'''

import os
import subprocess
import sys
from uuid_helper import get_uid

def deamon(uid):
    os.setuid(uid)

def lock_command(uname, cmd):
    uid = get_uid(uname)
    #cmd = ['gnome-screensaver-command', '-l']

    exec_cmd = cmd.strip().split()

    process = subprocess.Popen(exec_cmd, preexec_fn=deamon(uid),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
 
    outs, errs = process.communicate()
    #print "process return code:", process.returncode
    #print "stderr:", errs
    #print "stdout:", outs

def lock_command_sim(cmd):
    #cmd = ['gnome-screensaver-command', '-l']

    exec_cmd = cmd.strip().split()

    process = subprocess.Popen(exec_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    outs, errs = process.communicate()

if __name__ == '__main__':
    uname = sys.argv[1]
    deactive_cmd = 'dbus-send --type=method_call --dest=org.gnome.ScreenSaver /org/gnome/ScreenSaver \
    org.gnome.ScreenSaver.SetActive boolean:false'
    active_cmd = 'dbus-send --type=method_call --dest=org.gnome.ScreenSaver /org/gnome/ScreenSaver \
    org.gnome.ScreenSaver.Lock'
    lock_command(uname, active_cmd)
    import time
    time.sleep(10)
    lock_command(uname, deactive_cmd)
