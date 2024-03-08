# common utilities

import subprocess
import shlex
import os

from typing import (
    Tuple,
    List,
    Optional,
    Any
)

import ordinance.exceptions

def root_check():
    if os.geteuid() != 0: raise ordinance.exceptions.NotRootException()

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