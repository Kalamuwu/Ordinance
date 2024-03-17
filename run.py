#!/usr/bin/python

# 
# Ordinance
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

# start core
from core import Core, VERSION
core = Core(
    config_path='config.yaml',
    load_plugins=True
)

# set process name
new_process_name = f"Ordinance v{VERSION}".encode('utf-8')
from ctypes import cdll, byref, create_string_buffer
libc = cdll.LoadLibrary('libc.so.6')
buff = create_string_buffer(len(new_process_name)+1)
buff.value = new_process_name
libc.prctl(15, byref(buff), 0, 0, 0)

# command loop
cmd = ""
try:
    while core.running:
        if core.command(cmd) == -1:
            # shutdown signal received on last command
            break
        cmd = input("> ").strip().lstrip().lower()
except KeyboardInterrupt:
    core.stop()
