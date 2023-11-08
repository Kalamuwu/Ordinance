import datetime
import asyncio
import threading

from typing import (
    Dict,
    List,
    Any,
    Union,
    Optional,
    Coroutine
)

import ordinance.exceptions

from .__output.__writer_base import WriterBase
from .__output.__emailwriter import EmailWriter
from .__output.__filewriter import FileWriter
from .__output.__notifwriter import NotifWriter
from .__output.__stdoutwriter import StdoutWriter
from .__output.__syslogwriter import SyslogWriter


_types: Dict[str, type] = {
    'email': EmailWriter,
    'logfile': FileWriter,
    'notif': NotifWriter,
    'stdout': StdoutWriter,
    'syslog': SyslogWriter
}

_inited = False
_enabled: Dict[str, WriterBase] = {}

# TODO make :meth:`_parse_config(Dict[str, Any]) -> Dict[str, Any]`

def initialize(config: Dict[str, Any]):
    global _inited, _enabled
    if _inited:
        raise ordinance.exceptions.WriterException("Already initialized!")
    _enabled = {}
    enabled_conf = config.get('enabled', {})
    for name,clss in _types.items():
        if enabled_conf.get(name, False):
            try:
                writer_conf = config.get(name, {})
                obj = clss(writer_conf)
            except Exception as e:
                print(f"Could not enable writer {name}, with error: ", e)
            else:
                _enabled[name] = obj
    _inited = True


def is_enabled(writer_type_name: str) -> bool:
    """ Checks if the given writer type is enabled. """
    if writer_type_name not in _types:
        raise ordinance.exceptions.WriterNotFound(writer_type_name)
    return isinstance(_enabled[writer_type_name], WriterBase)


def debug(*msg):
    for writer in _enabled.values():
        writer.debug(*msg)

def info(*msg):
    for writer in _enabled.values():
        writer.info(*msg)

def success(*msg):
    for writer in _enabled.values():
        writer.success(*msg)

def warn(*msg):
    for writer in _enabled.values():
        writer.warn(*msg)

def error(*msg):
    for writer in _enabled.values():
        writer.error(*msg)

def critical(*msg):
    for writer in _enabled.values():
        writer.critical(*msg)

def alert(*msg):
    for writer in _enabled.values():
        writer.alert(*msg)


def _close() -> None:
    """ Closes all active writers. """
    for writer in _enabled.values():
        writer.close()
