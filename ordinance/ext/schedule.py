# 
# ordinance/plugin.py
# plugins base class and interfaces
# 

import os
import sys
import asyncio
import threading
import importlib.util
import importlib.machinery
import traceback
import inspect
import yaml.parser
import datetime
import time
import enum

import ordinance.ext.plugin
import ordinance.exceptions
import ordinance.util

from typing import (
    Any,
    Dict,
    List,
    Union,
    Optional,
    Tuple,
    Callable,
    Coroutine
)

def get_consthash(obj: object) -> Union[None, int]:
    return getattr(obj, '__consthash__', None)
def _assign_consthash(obj: object) -> None:
    if hasattr(obj, '__consthash__'): return
    obj.__consthash__ = hash(obj)
    obj.get_consthash = get_consthash



# Module classes

class OrdinanceEvent(enum.IntEnum):
    STARTUP = 1
    SHUTDOWN = 2
    # TODO more?
    __str__ = enum.Enum.__str__

class OrdinanceFunc:
    def __init__(self, func: Callable):
        _assign_consthash(func)
        self._func = func
        self._attached_plugin = None
        self._name: str = None
    
    def _set_attached_plugin(self, plugin):
        if self._attached_plugin is not None:
            raise ordinance.exceptions.SchedulerError("Already initialized!")
        self._attached_plugin = plugin
        self._name = f"{plugin.__class__.__name__}-{self._func.__name__}"
    
    @property
    def fhash(self):
        """
        Hash of the attached function. Used within the `ordinance.ext.schedule`
        module as an identifier of sorts to this :class:`OrdinanceFunc`.
        """
        return self._func.__consthash__
    
    @property
    def name(self):
        """ The name of this :class:`OrdinanceFunc`. """
        return self._name
    
    def run(self) -> None:
        """ Runs the attached function. """
        self._func(self._attached_plugin)
    
    def close(self) -> None:
        """ Closes this :class:`OrdinanceFunc`. """
        raise NotImplementedError("Cannot use base OrdinanceFunc class!")

class EventFunc(OrdinanceFunc):
    def __init__(self, func: Callable):
        super().__init__(func)
        self.__events: int = 0
        self.__threads: Dict[str, threading.Thread] = {}
        self.__len_lock = threading.Lock()
    
    @property
    def events(self):
        """
        The events that will trigger this :class:`EventFunc` to run. See
        :class:`OrdinanceEvent` for event names.
        """
        return self.__events
    
    def add_events(self, events_mask: int) -> int:
        """
        Adds a new event that this :class:`EventFunc` should listen to. See
        :class:`OrdinanceEvent` for event names.
        """
        self.__events |= events_mask
        return self.__events
    
    def should_run(self, event: int) -> bool:
        """ Returns if this :class:`EventFunc` should run on the given event. """
        return (self.__events & event) != 0
    
    def close(self) -> None:
        """ Closes this :class:`EventFunc`. Waits for all threads to join. """
        while True:
            with self.__len_lock:
                if len(self.__threads) == 0: break
                name,th = self.__threads.popitem()
            th.join()
    
    def _run_wrapper(self, name: str):
        self.run()
        with self.__len_lock:
            # name might not exist anymore if self.close() was called
            if name in self.__threads:
                self.__threads.pop(name)

    def fire(self) -> None:
        """ Fires this :class:`EventFunc` in its own thread. """
        with self.__len_lock:
            name = f"{self._name}-{len(self.__threads)}"
            th = threading.Thread(target=self._run_wrapper, name=name, args=(name,))
            self.__threads[name] = th
        th.start()

class ScheduledFunc(OrdinanceFunc):
    def __init__(self, func: Callable, time_between: datetime.timedelta, first_run: datetime.datetime):
        super().__init__(func)
        self.__between = time_between
        self.__next_run = first_run
        self.__timer: threading.Timer = None
        self.__thread: threading.Thread = None
    
    def set_time_between(self, time_between: datetime.timedelta, run_now: bool = False) -> None:
        """
        Changes the time between runs to be `time_between`. Useful for setting
        `time_between` programmatically, e.x. based on a config variable.
        """
        ordinance.writer.debug(f"Updated {self._attached_plugin.__class__.__name__} ScheduledFunc {self._func.__name__}",
                               f"from {self.__between.total_seconds()} seconds to {time_between.total_seconds()} seconds.")
        self.__between = time_between
    
    def close(self) -> None:
        """ Closes this :class:`ScheduledFunc`. Cancels timer and joins thread. """
        self.__timer.cancel()
        if self.__thread is not None and self.__thread.is_alive():
            self.__thread.join()

    def _run_wrapper(self):
        if self.__thread is not None and self.__thread.is_alive():
            raise ordinance.exceptions.SchedulerError("Scheduled function tried to start running before last run finished!")
        self.start_ticking()  # set up and tick next Timer
        self.__thread = threading.Thread(target=self.run, name=self.__name)
        self.__thread.start()

    def start_ticking(self):
        self.__timer = threading.Timer(self.__between.total_seconds(), self._run_wrapper)
        self.__timer.start()



# Module globals

__schedules: List[ScheduledFunc]  = []
__events:    Dict[int, EventFunc] = {}
__should_run = False



# Module methods

def get_coro(func: Callable) -> OrdinanceFunc:
    """
    Gets the :class:`ScheduledFunc` or :class:`EventFunc` associated with the
    given function.
    """
    if not hasattr(func, '__consthash__'):
        raise ordinance.exceptions.NotAnOrdinanceFunc(func)
    fhash = func.__consthash__
    if fhash in __events:   return __events[fhash]
    for sched in __schedules:
        if sched.fhash == fhash: return sched
    raise KeyError(f"Unknown function hash {fhash} (this should not occur)")

def cancel_func(func: Callable):
    """
    Cancels the :class:`ScheduledFunc` or :class:`EventFunc` associated with
    the given function.
    """
    if not hasattr(func, '__consthash__'):
        raise ordinance.exceptions.NotAnOrdinanceFunc(func)
    fhash = func.__consthash__
    if fhash in __events:   del __events[fhash]
    for i in range(len(__schedules)-1, -1, -1):
        if __schedules[i].fhash == fhash:
            del __schedules[i]
            return
    raise KeyError(f"Unknown function hash {fhash} (this should not occur)")

def fire_event(event: Union[int, OrdinanceEvent]):
    global __events
    if isinstance(event, OrdinanceEvent):
        ev_int = event.value
        ev_str = event
    else:
        ev_int = event
        ev_str = OrdinanceEvent(ev_int).name
    ordinance.writer.debug(f"Firing event {ev_str} (int {ev_int})")
    for fhash,ev in __events.items():
        if ev.should_run(event): ev.fire()

# def fire_event(event: int):
#     global __events
#     ordinance.writer.debug(f"Firing event(s) (int {event})")
#     async def inner__try_evcoro(evcoro: EventFunc):
#         if evcoro.should_run(event):
#             await asyncio.sleep(0)  # let other `EventFunc`s start ticking
#             try:  await evcoro._run_wrapper()
#             except Exception as e:
#                 tb = traceback.format_exc()
#                 ordinance.writer.error("Could not run event-triggered function with id",
#                                       f"{evcoro.fhash}, with error: {e.__class__.__name__}\n{tb}")
#     async def inner__run_all():
#         return await asyncio.gather(*[inner__try_evcoro(evcoro) for evcoro in __events.values()])



# Module Decorators

def _make_event_decorator(event: int):
    def decorator(coro):
        # not on top of another EventFunc decorator? check type and make attr
        if not hasattr(coro, '_EventFunc'):
            if not hasattr(coro, '_ScheduledFuncs'):  # type hasnt been checked
                # not a method!
                if not isinstance(coro, Callable):
                    ordinance.writer.error(f"Cannot schedule non-method {coro}")
                    return coro
            # type check ok. make and save new attr
            coro._EventFunc = EventFunc(coro)
            __events[coro._EventFunc.fhash] = coro._EventFunc
        # append this event and return
        coro._EventFunc.add_events(event)
        return coro
    return decorator

def run_at_startup():
    """
    Schedules a function ro run when Ordinance finishes initializing.
    """
    return _make_event_decorator(OrdinanceEvent.STARTUP)

def run_at_shutdown():
    """
    Schedules a function ro run when Ordinance shuts down.
    """
    return _make_event_decorator(OrdinanceEvent.SHUTDOWN)

def run_periodically(seconds: int = 0, minutes: int = 0, hours: int = 0, days: int = 0):
    """
    Schedules a function to run at a set interval, on the order of seconds to
    days. Any and all parameters can be used with one another if needed, e.x.
    :attr:`hours=1, minutes=30`. Alternatively, one unit can be used and "roll
    over" to the others, e.x. :attr:`minutes=90`. The scheduled function will
    NOT run immediately, stack with :meth:`@run_at_startup` to achieve this.
    """
    def decorator(coro):
        # not on top of another ScheduledFunc decorator? check type and make attr
        if not hasattr(coro, '_ScheduledFuncs'):
            if not hasattr(coro, '_EventFunc'):  # type hasnt been checked
                # not a method!
                if not isinstance(coro, Callable):
                    ordinance.writer.error(f"Cannot schedule non-method {coro}")
                    return coro
            # type check ok. make and save new attr
            coro._ScheduledFuncs = []
        # create scheduled coroutine parameters
        time_between = datetime.timedelta(seconds=seconds, minutes=minutes, hours=hours, days=days)
        first = datetime.datetime.now() + time_between
        # instantiate, save, and return
        __schedules.append(
            ScheduledFunc(coro, time_between=time_between, first_run=first)
        )
        coro._ScheduledFuncs.append(__schedules[-1])
        return coro
    return decorator

def run_daily_at(self, hour: int = 0, minute: int = 0, second: int = 0):
    """
    Schedules a function to run daily at :meth:`hh:mm:ss`, where `hour`,
    `minute`, and `second` are given as paramaters. **Uses 24-hour clock;**
    for example, 9:00PM should be specified as `hour=21`.
    """
    def decorator(coro):
        # not on top of another ScheduledFunc decorator? check type and make attr
        if not hasattr(coro, '_ScheduledFuncs'):
            if not hasattr(coro, '_EventFunc'):  # type hasnt been checked
                # not a method!
                if not isinstance(coro, Callable):
                    ordinance.writer.error(f"Cannot schedule non-method {coro}")
                    return coro
            # type check ok. make and save new attr
            coro._ScheduledFuncs = []
        # create scheduled coroutine parameters
        time_between = datetime.timedelta(days=1)
        # calculate how long until the first scheduled run
        localtz = ordinance.util.local_tz()
        time_now = datetime.datetime.now(tz=localtz)
        time_first = datetime.datetime(
            time_now.year, time_now.month, time_now.day,
            hour, minute, second, 0,
            localtz
        )
        if time_first >= time_now:  # run would have been earlier today
            time_first += datetime.timedelta(days=1)
        # instantiate, save, and return
        __schedules.append(
            ScheduledFunc(coro, time_between=time_between, first_run=time_first)
        )
        coro._ScheduledFuncs.append(__schedules[-1])
        return coro
    return decorator



# Internal methods

def _register(plugin):
    """
    **Called internally. Plugins should not call this.**
    
    Registers the decorator functions inside a :class:`OrdinancePlugin`.
    """
    for name,method in plugin.__class__.__dict__.items():
        if hasattr(method, '_ScheduledFuncs'):
            for schedc in method._ScheduledFuncs:
                schedc._set_attached_plugin(plugin)
        if hasattr(method, '_EventFunc'):
            method._EventFunc._set_attached_plugin(plugin)

# async def _run_coro():
#     """
#     Called internally to run the :mod:`schedule` module. Note that plugins
#     **should not** call this directly, but instead this function will be called
#     internally in its own thread to start ticking the :mod:`schedule` module.
#     """
#     global __should_run
#     __should_run = True
#     while __should_run:
#         now = datetime.datetime.now()
#         for schedcoro in __schedules:
#             if schedcoro.should_run(now):
#                 try:
#                     await schedcoro._run_wrapper()
#                 except Exception as e:
#                     tb = traceback.format_exc()
#                     ordinance.writer.error(f"Could not run scheduled function with id {schedcoro.fhash},",
#                                            f"with error: {e.__class__.__name__}\n{tb}")
#             await asyncio.sleep(0)
#         await asyncio.sleep(0.5)



# functions for core

def _start():
    global __schedules
    for sched in __schedules:
        sched.start_ticking()

def _close():
    global __schedules, __events
    for sched in __schedules:
        sched.close()
    for ev in __events.values():
        ev.close()
