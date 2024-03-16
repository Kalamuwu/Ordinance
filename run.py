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


from core import Core
core = Core(
    config_path='config.yaml',
    load_plugins=True
)

cmd = ""
try:
    while core.running:
        if core.command(cmd) == -1:
            # shutdown signal received on last command
            break
        cmd = input("> ").strip().lstrip().lower()
except KeyboardInterrupt:
    core.stop()
