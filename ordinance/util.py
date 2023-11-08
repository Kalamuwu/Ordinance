# common utilities

import subprocess
import shlex
import os
import datetime
import time

from typing import (
    Tuple,
    List,
    Optional,
    Any
)

import ordinance.exceptions

def deep_merge(dict1: dict, dict2: dict) -> dict:
    """
    Merges two dicts. If keys are conflicting, dict2 is preferred.
    
    Credit to milanboers on GitHub for this function:
    https://gist.github.com/milanboers/a8bb8b81b1c3fb3eb86ee2d9ea4bd5b2
    """
    def _val(v1, v2):
        if isinstance(v1, dict) and isinstance(v2, dict):
            return deep_merge(v1, v2)
        return v2 or v1
    return {k: _val(dict1.get(k), dict2.get(k)) for k in dict1.keys() | dict2.keys()}

def local_tz() -> datetime.timezone:
    """
    Returns the local timezone as a :class:`datetime.timezone`. **Does**
    account for daylight savings time.
    """
    if time.daylight:  return datetime.timezone(datetime.timedelta(seconds=-time.altzone),  time.tzname[1])
    else:              return datetime.timezone(datetime.timedelta(seconds=-time.timezone), time.tzname[0])

def root_check():
    if os.geteuid() != 0: raise ordinance.exceptions.NotRootException()

def get_header(comment: Optional[str] = ""):
    header = r"""#################################################################################################
#                                                                                               #
#   ________  ________  ________  ___  ________   ________  ________   ________  _______        #
#  |\   __  \|\   __  \|\   ___ \|\  \|\   ___  \|\   __  \|\   ___  \|\   ____\|\  ___ \       #
#  \ \  \|\  \ \  \|\  \ \  \_|\ \ \  \ \  \\ \  \ \  \|\  \ \  \\ \  \ \  \___|\ \   __/|      #
#   \ \  \\\  \ \   _  _\ \  \ \\ \ \  \ \  \\ \  \ \   __  \ \  \\ \  \ \  \    \ \  \_|/__    #
#    \ \  \\\  \ \  \\  \\ \  \_\\ \ \  \ \  \\ \  \ \  \ \  \ \  \\ \  \ \  \____\ \  \_|\ \   #
#     \ \_______\ \__\\ _\\ \_______\ \__\ \__\\ \__\ \__\ \__\ \__\\ \__\ \_______\ \_______\  #
#      \|_______|\|__|\|__|\|_______|\|__|\|__| \|__|\|__|\|__|\|__| \|__|\|_______|\|_______|  #
#                                                                                               #
#################################################################################################

"""
    if not comment: return header
    header += "\n# \n"
    for subcmt in comment.split('\n'):
        # break up every 80 chars, keep words intact
        lines = []
        for i,word in enumerate(subcmt.strip().split(' ')):
            if len(lines) == 0 or (len(lines[-1]) + len(word) > 77):
                lines.append(word)
            else:
                lines[-1] += " " + word
        header += '# ' + '\n# '.join(lines) + '\n'
    return header + '\n# '

def run_shell_cmd(command: str, inpipe: Optional[subprocess.PIPE] = None) -> Tuple[int, str]:
    """
    Runs a command on the system. Returns :attr:`(returncode, stream)` where
    `stream` = stdout if the command returns 0, otherwise `stream` = stderr.
    """
    res = subprocess.run(shlex.split(command), capture_output=True, stdin=inpipe)
    out = (res.stderr) if res.returncode else (res.stdout)
    return (res.returncode, out.decode().strip())

def run_shell_cmd_piped(command: str, inpipe: Optional[subprocess.PIPE] = None) -> Tuple[int, subprocess.PIPE, subprocess.PIPE]:
    """
    Runs a command on the system. Returns :attr:`(returncode, stdout, stderr)`.
    """
    res = subprocess.run(shlex.split(command), stdin=inpipe,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return (res.returncode, res.stdout, res.stderr)