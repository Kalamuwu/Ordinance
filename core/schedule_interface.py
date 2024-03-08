import threading
import datetime
import time

from typing import List, Dict

import ordinance.writer

# helper methods

def local_tz() -> datetime.timezone:
    """
    Returns the local timezone as a :class:`datetime.timezone`. **Does**
    account for daylight savings time.
    """
    if time.daylight:  return datetime.timezone(datetime.timedelta(seconds=-time.altzone),  time.tzname[1])
    else:              return datetime.timezone(datetime.timedelta(seconds=-time.timezone), time.tzname[0])

def get_type_string(trigger: ordinance.schedule.BaseTrigger):
    if   isinstance(trigger, ordinance.schedule.CalendarTrigger): return 'calendar'
    elif isinstance(trigger, ordinance.schedule.DelayTrigger):    return 'delay'
    elif isinstance(trigger, ordinance.schedule.EventTrigger):    return 'event',
    elif isinstance(trigger, ordinance.schedule.PeriodicTrigger): return 'periodic'
    return 'none'



# trigger should_run functions

def calendar_trigger_should_run(calendar_trigger: ordinance.schedule.CalendarTrigger, now: datetime.datetime, granularity: float = 0.0) -> bool:
    if calendar_trigger.align_to == 'month':
        period_start = datetime.datetime(now.year, now.month, 0)
    elif calendar_trigger.align_to == 'week':
        period_start = datetime.datetime(now.year, now.month, now.day - now.weekday())
    elif calendar_trigger.align_to == 'day':
        period_start = datetime.datetime(now.year, now.month, now.day)
    run = period_start + datetime.timedelta(seconds=calendar_trigger.seconds_into)
    delta = run - now
    return abs(delta.total_seconds()) <= granularity

def delay_trigger_should_run(delay_trigger: ordinance.schedule.DelayTrigger, total_elapsed: datetime.timedelta, granularity: float = 0.0) -> bool:
    d = datetime.timedelta(seconds=delay_trigger.delay_sec)
    return abs( (total_elapsed - d).total_seconds() ) <= granularity

def periodic_trigger_should_run(periodic_trigger: ordinance.schedule.PeriodicTrigger, total_elapsed: datetime.timedelta, granularity: float = 0.0) -> bool:
    sec_left = total_elapsed.total_seconds() % periodic_trigger.period_sec
    return abs(sec_left) <= granularity

