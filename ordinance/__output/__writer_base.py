import asyncio
import datetime
import threading
from collections import deque

from typing import (
    Dict,
    List,
    Any
)

class Message:
    # lbl      bin     dec   hex
    ALRT = 0b1000000  # 64  0x40
    CRIT = 0b0100000  # 32  0x20
    ERRR = 0b0010000  # 16  0x10
    WARN = 0b0001000  #  8  0x08
    SUCC = 0b0000100  #  4  0x04
    INFO = 0b0000010  #  2  0x02
    DBUG = 0b0000001  #  1  0x01
    def __init__(self, msg: List[Any], importance: int):
        self.message = msg
        self.importance = importance
        self.time = datetime.datetime.now()


class WriterBase():
    """ Base writer class. """
    def __init__(self, config: Dict[str, Any], delay_between_handles: int):
        self.__message_queue: deque[Message] = deque()
        self._handle_lock = threading.Lock()
        self.is_running = True
        self.delay = delay_between_handles


    ## Overwritten functions
    
    def handle(self, message: Message):
        raise NotImplementedError()

    def close(self):
        """
        Some writers can override this to make sure they are closed properly.
        By default there is nothing to close.
        """
    
    
    ## Passed-down functions
    
    # def _handle_thread(self):
    #     msg = None  # allocate before try-except
    #     while self.is_running:
    #         try:
    #             msg = self.__message_queue.popleft()
    #             await self.handle(msg)
    #         except IndexError: pass  # queue EAFP; see https://stackoverflow.com/a/58679588
    #         except Exception as e:
    #             print(f"Couldn't call {self.__class__.__name__}.handle() with error:", e)
    #         await asyncio.sleep(self.delay)
    
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
