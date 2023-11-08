#!/usr/bin/python

# 
# Ordnance v2 - An active honeypotting, monitoring, and protection tool.
# v1 loosely based on Artillery by BinaryDefense
# 
# Written by: @Kalamuwu
# Github: https://github.com/Kalamuwu/
# 
# Artillery - a Binary Defense Project (https://www.binarydefense.com) @Binary_Defense
# Written by: Dave Kennedy (ReL1K) @HackingDave
# Website: https://www.binarydefense.com
# Github: https://github.com/binarydefense/artillery
# 

import time

from ordinance.core import Core

# TODO command line argument parsing

core = Core(
    config_path='config.yaml',
    load_plugins=True,
    # interactive_mode=False  # TODO eventually ;)
)
core.run()

should_run = True
try:
    while should_run:
        time.sleep(1)
except KeyboardInterrupt:
    should_run = False
    core.close()
    print("done")
    exit(0)
