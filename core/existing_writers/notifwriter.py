import os
import collections
import threading
import asyncio

from typing import (
    Dict,
    Any
)

import ordinance.writer
from ordinance.writer import WriterBase, Message

"""
try:
    sys_bus = dbus.SessionBus()
    notify_interface = dbus.Interface(
        sys_bus.get_object(
            "org.freedesktop.Notifications",
            "/org/freedesktop/Notifications"),
        "org.freedesktop.Notifications")
except dbus.DBusException as e:
    print("NotifWriter: Failed to connect to dbus: ", e)
"""

class NotifWriter(WriterBase):
    """ Writer that shows a popup notification. """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.dbus_username = config.get('dbus_username')
        self.notify_send_path = config.get('notify_send_path', '/usr/bin/notify-send')
    
    def handle(self, msg: Message):
        if   msg.importance & Message.ERRR: title = "Ordinance: Error"
        elif msg.importance & Message.ALRT: title = "Ordinance: Alert"
        elif msg.importance & Message.CRIT: title = "Ordinance: Critical"
        else: return
        body = ' '.join(str(s) for s in msg.message)
        # we have to use `sudo -u {user}`; reason, see comment block below
        # this is a hack and surely there's a better workaround, but idk
        os.system(
            f"sudo -u {self.dbus_username} -E DISPLAY=':0' {self.notify_send_path} " + \
            f"-u 'critical' -a 'Ordinance Alerts' '{title}' '{body}'")

# NOTE -- this version uses asyncio and python-dbus, but doesn't work because
#         root can't connect to a given user's dbus session
"""
class NotifWriter(WriterBase):
    \""" Writer that shows a popup notification. \"""
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.queue = collections.deque()
        self.loop = None
        self.should_run = True
        self.loop_thread = threading.Thread(target=self.run, name="Notif-Writer_Loop_Thread")
        self.loop_thread.start()

    def handle(self, msg: Message):
        if   msg.importance & Message.ERRR: title = "Ordinance: Error"
        elif msg.importance & Message.ALRT: title = "Ordinance: Alert"
        elif msg.importance & Message.CRIT: title = "Ordinance: Critical"
        else: return
        body = ' '.join(str(s) for s in msg.message)
        self.queue.append((title,body))
    
    def run(self):
        if self.loop is None:
            self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        async def runner():
            while self.should_run:
                while True:
                    try: title,body = self.queue.popleft()
                    except IndexError: break
                    notify_interface.Notify(
                        "Ordinance",     # application name
                        0,               # optional ID of the notification to replace
                        "",              # notification icon
                        title,           # summary
                        body,            # body
                        [],              # actions
                        {'urgency': 2},  # hints (urgency=2 --> critical)
                        0                # display timeout, in ms
                    )
                await asyncio.sleep(2)
        self.loop.run_until_complete(runner())

    def close(self):
        # shut down asyncio loop thread
        self.should_run = False
        self.loop_thread.join()
        if self.loop is not None:
            self.loop.stop()
            self.loop.close()
            self.loop = None
"""
