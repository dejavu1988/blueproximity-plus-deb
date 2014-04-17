#!/usr/bin/env python

import pygtk
pygtk.require("2.0")
import pynotify
import sys
import os

def notify(msg):
    pynotify.init("Error")
    uri = "file://" + os.path.abspath(os.path.curdir) + "/applet-critical.png"
    n = pynotify.Notification("Exception: blueproximity-plus", msg, uri)
    n.set_urgency(pynotify.URGENCY_CRITICAL)
    n.set_timeout(3000)
    n.show()


if __name__ == '__main__':
    notify('test msg')