import asyncio
import threading

from typing import (
    List,
    Coroutine,
    Callable,
    Optional
)

import ordinance.writer

def run_loop_forever(loop: asyncio.AbstractEventLoop):
    """ Runs an :class:`asyncio.AbstractEventLoop` in its own thread. """
    asyncio.set_event_loop(loop)
    loop.run_forever()


class BackgroundEventLoop():
    def __init__(self, name: str, closefunc: Coroutine, tasksfunc: Coroutine):
        self.name = name
        # initialize loop
        self.loop = asyncio.new_event_loop()
        tasksfunc(self.loop)
        # initialize internal loop thread
        self.thread = threading.Thread(
            name=name,
            target=run_loop_forever,
            args=(self.loop,))
        # save close function -- closefunc() returns this coroutine
        self.closecoro = closefunc
    
    def start(self):
        self.thread.start()
        ordinance.writer.info(f"Started thread {self.name}")
    
    def stop(self, timeout: Optional[float] = None):
        # run close func
        res = asyncio.run_coroutine_threadsafe(self.closecoro(), self.loop)
        while not res.done(): pass
        # finish final tasks
        tasks = asyncio.all_tasks(self.loop)
        async def __inner(): await asyncio.gather(*tasks, return_exceptions=True)
        res = asyncio.run_coroutine_threadsafe(__inner(), self.loop)
        while not res.done(): pass
        # close and leave thread
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout)
        print(f"Stopped thread {self.name}")
        # note: the above cannot use :module:`ordinance.writer` because the
        # write thread for that module is a :class:`BackgroundEventLoop`
