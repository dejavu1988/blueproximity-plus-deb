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

def state_command(uname):
    uid = get_uid(uname)
    cmd = 'dbus-send --type=method_call --print-reply --dest=org.gnome.ScreenSaver /org/gnome/ScreenSaver \
    org.gnome.ScreenSaver.GetActive'

    exec_cmd = cmd.strip().split()

    process = subprocess.Popen(exec_cmd, preexec_fn=deamon(uid),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    outs, errs = process.communicate()
    #print outs.split()[-1]
    if 'true' in outs.split()[-1]:
        return True     #locked state
    else:
        return False    #unlocked state

if __name__ == '__main__':
    uname = sys.argv[1]
    deactive_cmd = 'dbus-send --type=method_call --dest=org.gnome.ScreenSaver /org/gnome/ScreenSaver \
    org.gnome.ScreenSaver.SetActive boolean:false'
    active_cmd = 'dbus-send --type=method_call --dest=org.gnome.ScreenSaver /org/gnome/ScreenSaver \
    org.gnome.ScreenSaver.Lock'
    #status_cmd = 'dbus-send --type=method_call --print-reply --dest=org.gnome.ScreenSaver /org/gnome/ScreenSaver \
    #org.gnome.ScreenSaver.GetActive'
    status_command(uname)
    lock_command(uname, active_cmd)
    import time
    for i in range(10):
        status_command(uname)
    time.sleep(2)
    lock_command(uname, deactive_cmd)
    status_command(uname)
