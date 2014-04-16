#!/usr/bin/env python

import fcntl
import os
import stat
import tempfile

def check_singleton():
    # Establish lock file settings
    lf_name = 'blueproximity-plus.lock'
    lf_path = os.path.join('/var/run', lf_name)
    lf_flags = os.O_WRONLY | os.O_CREAT
    lf_mode = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH  # This is 0o222, i.e. 146

    # Create lock file
    umask_original = os.umask(0)
    try:
        lf_fd = os.open(lf_path, lf_flags, lf_mode)
    finally:
        os.umask(umask_original)

    # Try locking the file
    try:
        fcntl.lockf(lf_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        msg = ('Error: {0} is already running. Only one instance '
               'is allowed at a time.'
               ).format('Blueproximity-plus')
        exit(msg)