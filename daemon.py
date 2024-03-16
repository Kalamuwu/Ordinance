#!/usr/bin/python

# 
# Ordinance v4.1
# An active honeypotting, monitoring, and protection tool.
# 
# Written by: @Kalamuwu
# Github: https://github.com/Kalamuwu/
# 

# pre-conditions -- check for root, and change working dir
import os
if os.geteuid() != 0:
    raise PermissionError("[!] Ordinance must be run as root.")
os.chdir(os.path.dirname(os.path.abspath(__file__)))

pid = os.fork()
if pid != 0:
    # this is parent. write pidfile and exit
    print(f"PID of daemon is {pid}")
    with open('pidfile', 'w') as file:
        file.write(str(pid))
    exit(0)


from core import Core
core = Core(
    config_path='config.yaml',
    load_plugins=True
)

import time
try:
    while 1: time.sleep(1)
except:
    core.stop()
    os.remove('pidfile')
