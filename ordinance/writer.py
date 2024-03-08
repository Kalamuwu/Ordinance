import datetime
import threading

from typing import (
    Dict,
    List,
    Set,
    Any,
    Union,
    Optional,
    Coroutine
)

import ordinance.exceptions



class Message:

    # criticality levels
    ALRT = 0x40
    CRIT = 0x20
    ERRR = 0x10
    WARN = 0x08
    SUCC = 0x04
    INFO = 0x02
    DBUG = 0x01

    # aliases
    ALERT = ALRT
    CRITICAL = CRIT
    ERROR = ERRR
    WARNING = WARN
    SUCCESS = SUCC
    DEBUG = DBUG

    def __init__(self, msg: List[Any], importance: int):
        self.message = msg
        self.importance = importance
        self.time = datetime.datetime.now()



class WriterBase():
    """ Base writer class. """
    def __init__(self, config: Dict[str, Any]):
        self._handle_lock = threading.Lock()


    ## Overwritten functions
    
    def handle(self, message: Message):
        raise NotImplementedError()

    def close(self):
        """
        Some writers can override this to make sure they are closed properly.
        By default there is nothing to close.
        """
    
    
    ## Passed-down functions
    
    def debug(self, *msg):
        with self._handle_lock:
            self.handle(Message(msg, Message.DBUG))
    
    def info(self, *msg):
        with self._handle_lock:
            self.handle(Message(msg, Message.INFO))
    
    def success(self, *msg):
        with self._handle_lock:
            self.handle(Message(msg, Message.SUCC))
    
    def warn(self, *msg):
        with self._handle_lock:
            self.handle(Message(msg, Message.WARN))
    
    def error(self, *msg):
        with self._handle_lock:
            self.handle(Message(msg, Message.ERRR))
    
    def critical(self, *msg):
        with self._handle_lock:
            self.handle(Message(msg, Message.CRIT))
    
    def alert(self, *msg):
        with self._handle_lock:
            self.handle(Message(msg, Message.ALRT))



__enabled: List[WriterBase] = []
__classes: Dict[str, WriterBase] = {}

def add_writer_type(name: str, writer_class: WriterBase) -> None:
    if name in __classes:
        raise ordinance.exceptions.WriterException(f"A writer of this name ('{name}') already exists")
    __classes[name] = writer_class

def enable(name: str, config: Dict[str, Any]) -> None:
    if name not in __classes:
        raise ordinance.exceptions.WriterNotFound(name)
    typ = __classes[name]
    for writer in __enabled:
        if isinstance(writer, typ):
            raise ordinance.exceptions.WriterAlreadyEnabled(name)
    obj = typ(config)
    __enabled.append(obj)

def disable(name: str) -> None:
    if name not in __classes:
        raise ordinance.exceptions.WriterNotFound(name)
    typ = __classes[name]
    for writer in __enabled:
        if isinstance(writer, typ):
            writer.close(); return
    raise ordinance.exceptions.WriterAlreadyDisabled(name)

def get_enabled() -> Set[str]:
    out = set()
    for obj in __enabled:
        for name,typ in __classes.items():
            if isinstance(obj, typ): out.add(name)
    return out

def get_known() -> Set[str]:
    return set(__classes.keys())

def debug(*msg):
    for writer in __enabled: writer.debug(*msg)
def info(*msg):
    for writer in __enabled: writer.info(*msg)
def success(*msg):
    for writer in __enabled: writer.success(*msg)
def warn(*msg):
    for writer in __enabled: writer.warn(*msg)
def error(*msg):
    for writer in __enabled: writer.error(*msg)
def critical(*msg):
    for writer in __enabled: writer.critical(*msg)
def alert(*msg):
    for writer in __enabled: writer.alert(*msg)
