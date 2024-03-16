import enum
import time
import datetime
import random
import threading

from dataclasses import dataclass
from typing import Dict, List, Callable, Any, Optional, Union

import ordinance.exceptions

# base data classes (like c++ structs)

@dataclass(eq=False)
class BaseTrigger:
    id: str
    daemonic: bool
    def __eq__(self, other):
        if not isinstance(other, self.__class__) \
        or not isinstance(self, other.__class__):
            return NotImplemented
        for prop in self.__class__.__annotations__:
            if prop in ['id', 'daemonic']: continue
            if getattr(self, prop) != getattr(other, prop):
                return False
        return True

@dataclass(eq=False)
class CalendarTrigger(BaseTrigger):
    align_to: str
    seconds_into: float

@dataclass(eq=False)
class DelayTrigger(BaseTrigger):
    delay_sec: float

@dataclass(eq=False)
class EventTrigger(BaseTrigger):
    event: str

@dataclass(eq=False)
class PeriodicTrigger(BaseTrigger):
    period_sec: float

# base schedule class

class ScheduledFunction:
    def __init__(self, callback: Callable):
        self.__callback = callback
        self.__lock = threading.Lock()
        self.__triggers: Dict[str, BaseTrigger] = {}
        self.__triggers_calendar: Dict[str, CalendarTrigger] = {}
        self.__triggers_delay:    Dict[str, DelayTrigger]    = {}
        self.__triggers_event:    Dict[str, EventTrigger]    = {}
        self.__triggers_periodic: Dict[str, PeriodicTrigger] = {}
    
    @property
    def name(self) -> str: return self.__callback.__name__

    def __repr__(self) -> str:
        return f"<ScheduledFunction tied to f{repr(self.__callback)}>"
    
    def __call__(self, plugin_instance, daemonic: Optional[bool] = False) -> threading.Thread:
        def _exc_wrap(*args):
            try: self.__callback(*args)
            except Exception as e:
                ordinance.writer.error("Failed to call ScheduledFunction callback:")
                ordinance.writer.error(e)
        thread = threading.Thread(
            target=_exc_wrap,
            args=(plugin_instance,),
            name=self.name,
            daemon=daemonic)
        thread.start()
        return thread
    
    def id_is_unique(self, id: str) -> bool:
        with self.__lock:
            return not (id in self.__triggers)

    def get_trigger_by_id(self, id: str) -> BaseTrigger:
        with self.__lock:
            if id in self.__triggers:
                return self.__triggers[id]
        raise ordinance.exceptions.SchedulerError(f"Unknown trigger ID '{id}'")
    
    def _get_triggers(self):
        with self.__lock:
            return list(self.__triggers.values())

    def __add_trigger(self,
        trig_cls, data_clash_fail_message: str,
        id: str, daemonic: bool, *args
    ) -> str:
        with self.__lock:
            # generate new id, if not given
            if not id:
                id = f"trigger-{int(random.random() * 0xFFFFFFFF)}"
            # make sure id isn't clashing
            if id in self.__triggers:
                raise ordinance.exceptions.SchedulerError(
                    f"Scheduler with ID '{id}' is already defined for this plugin")
            # create new class
            new = trig_cls(id, daemonic, *args)
            # make sure data isn't clashing
            for id,trig in self.__triggers.items():
                if new == trig:
                    raise ordinance.exceptions.SchedulerError(data_class_fail_message)
            # good! append and return
            self.__triggers[id] = new
        return id

    def add_calendar_trigger(self, align_to: str, into: datetime.timedelta, id: Optional[str] = None, daemonic: Optional[bool] = False) -> str:
        into_sec = into.total_seconds()
        day_total = 60*60*24
        week_total = day_total * 7
        month_total = day_total * 28  # assumes worst-case of February
        # check for bad cal type
        def _cap(totlen):
            while into_sec < 0:      into_sec += totlen
            while into_sec > totlen: into_sec -= totlen
        if align_to == 'day':     _cap(day_total)
        elif align_to == 'week':  _cap(week_total)
        elif align_to == 'month': _cap(month_total)
        else: raise ordinance.exceptions.SchedulerError(
            f"Unknown calendar type '{align_to}' (must be 'day', 'week', or 'month')")
        # everything good. make and return
        return self.__add_trigger( CalendarTrigger,
            f"Calendar trigger of {into_sec} aligned to '{align_to}' already registered",
            id, daemonic, align_to, into_sec)
    
    def add_delay_trigger(self, delay: datetime.timedelta, id: Optional[str] = None, daemonic: Optional[bool] = False) -> str:
        delta = delay.total_seconds()
        return self.__add_trigger(DelayTrigger,
            f"Delay trigger of {delta} seconds already registered",
            id, daemonic, delay)
    
    def add_event_trigger(self, event: str, id: Optional[str] = None, daemonic: Optional[bool] = False) -> str:
        return self.__add_trigger(EventTrigger,
            f"Already subscribed to event {event}",
            id, daemonic, event)
    
    def add_periodic_trigger(self, delta: datetime.timedelta, id: Optional[str] = None, daemonic: Optional[bool] = False) -> str:
        delta = delta.total_seconds()
        return self.__add_trigger(PeriodicTrigger,
            f"Periodic trigger of {delta} seconds already registered",
            id, daemonic, delta)

def _cast_coro(coro: Union[Callable, ScheduledFunction]) -> ScheduledFunction:
    if isinstance(coro, ScheduledFunction):
        return coro
    elif isinstance(coro, Callable):
        return ScheduledFunction(coro)
    else:
        raise ordinance.exceptions.SchedulerError(f"Cannot schedule non-method {type(coro)} {coro}")

def _make_calendar_decorator(every_what: str, into: datetime.timedelta, id: Optional[str] = None, daemonic: Optional[bool] = False):
    def decorator(coro):
        coro = _cast_coro(coro)
        coro.add_calendar_trigger(every_what, into, id=id, daemonic=daemonic)
        return coro
    return decorator

def _make_delay_decorator(delay: datetime.timedelta, id: Optional[str] = None, daemonic: Optional[bool] = False):
    def decorator(coro):
        coro = _cast_coro(coro)
        coro.add_delay_trigger(delay, id=id, daemonic=daemonic)
        return coro
    return decorator

def _make_event_decorator(event: str, id: Optional[str] = None, daemonic: Optional[bool] = False):
    def decorator(coro):
        coro = _cast_coro(coro)
        coro.add_event_trigger(event, id=id, daemonic=daemonic)
        return coro
    return decorator

def _make_periodic_decorator(delta: datetime.timedelta, id: Optional[str] = None, daemonic: Optional[bool] = False):
    def decorator(coro):
        coro = _cast_coro(coro)
        coro.add_periodic_trigger(delta, id=id, daemonic=daemonic)
        return coro
    return decorator



# blank scheduler

def blank_schedule():
    """
    Transforms the marked function into a :class:`ScheduledFunction` with no
    schedules.
    
    This is useful if a schedule will be added programmatically, but no
    "default" or "base" schedule is wanted.
    """
    def decorator(coro):
        return _cast_coro(coro)
    return decorator



# calendar based schedulers

def run_daily_at(hour: int = 0, minute: int = 0, second: int = 0, id: Optional[str] = None, daemonic: Optional[bool] = False):
    """
    Schedules a function to run daily at :meth:`hh:mm:ss`, where `hour`,
    `minute`, and `second` are given as paramaters. **Uses 24-hour clock;**
    for example, 9:00PM should be specified as `hour=21`.
    """
    delta = datetime.timedelta(hours=hour, minutes=minute, seconds=second)
    return _make_calendar_decorator('day', delta, id=id, daemonic=daemonic)

def run_weekly_at(day: int = 0, hour: int = 0, minute: int = 0, second: int = 0, id: Optional[str] = None, daemonic: Optional[bool] = False):
    """
    Schedules a function to run weekly at :meth:`dd hh:mm:ss`, where `day`,
    `hour`, `minute`, and `second` are given as paramaters. **Uses 24-hour
    clock;** for example, 9:00PM should be specified as `hour=21`. **Weeks
    start with day 0 being Monday;** for example, Wednesday should be
    specified as `day=2`.
    """
    delta = datetime.timedelta(days=day, hours=hour, minutes=minute, seconds=second)
    return _make_calendar_decorator('week', delta, id=id, daemonic=daemonic)

def run_monthly_at(day: int = 0, hour: int = 0, minute: int = 0, second: int = 0, id: Optional[str] = None, daemonic: Optional[bool] = False):
    """
    Schedules a function to run weekly at :meth:`dd hh:mm:ss`, where `day`,
    `hour`, `minute`, and `second` are given as paramaters. **Uses 24-hour
    clock;** for example, 9:00PM should be specified as `hour=21`.
    """
    delta = datetime.timedelta(days=day, hours=hour, minutes=minute, seconds=second)
    return _make_calendar_decorator('month', delta, id=id, daemonic=daemonic)



# delay based schedulers

def delay(minutes: int = 0, seconds: int = 0, id: Optional[str] = None, daemonic: Optional[bool] = False):
    """
    Schedules a function to run once, after a specified delay of :meth:`mm:ss`,
    where `minutes` and `seconds` are given as parameters. The returned
    schedule will be invalid after this timer has expired (meaning it cannot be
    shifted or cancelled), but can still be called manually.
    """
    delta = datetime.timedelta(minutes=minutes, seconds=seconds)
    return _make_delay_decorator(delta, id=id, daemonic=daemonic)



# event based schedulers

def run_at_plugin_start(id: Optional[str] = None, daemonic: Optional[bool] = False):
    """ Schedules a function to run when this plugin starts. """
    return _make_event_decorator('ordinance:plugin.start', id=id, daemonic=daemonic)

def run_at_plugin_stop(id: Optional[str] = None, daemonic: Optional[bool] = False):
    """ Schedules a function ro run when this plugin shuts down. """
    return _make_event_decorator('ordinance:plugin.stop', id=id, daemonic=daemonic)

def run_on_event(event: str, id: Optional[str] = None, daemonic: Optional[bool] = False):
    """ Schedules a function to run on the given event string. """
    return _make_event_decorator(event, id=id, daemonic=daemonic)



# period based schedulers

def run_periodically(seconds: int = 0, minutes: int = 0, hours: int = 0, days: int = 0, id: Optional[str] = None, daemonic: Optional[bool] = False):
    """
    Schedules a function to run at a set interval, on the order of seconds to
    days. Any and all parameters can be used with one another if needed, e.x.
    :attr:`hours=1, minutes=30`. Alternatively, one unit can be used and "roll
    over" to the others, e.x. :attr:`minutes=90`. The scheduled function will
    NOT run immediately, stack with :meth:`@run_at_plugin_start` to achieve this.
    """
    time_between = datetime.timedelta(seconds=seconds, minutes=minutes, hours=hours, days=days)
    return _make_periodic_decorator(time_between, id=id, daemonic=daemonic)

