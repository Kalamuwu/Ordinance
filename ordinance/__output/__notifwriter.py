import asyncio
import notify2

from typing import (
    Dict,
    Any
)

from .__writer_base import WriterBase, Message

class NotifWriter(WriterBase):
    """ Writer that shows a popup notification. """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, 5)
        notify2.init("Ordinance Alerts")

    def handle(self, msg: Message):
        out = ' '.join(str(m) for m in msg.message)
        if msg.importance & Message.ERRR:
            n = notify2.Notification("Ordinance: Error", out)
            n.show()
        elif msg.importance & Message.ALRT:
            n = notify2.Notification("Ordinance: Alert", out)
            n.show()
        elif msg.importance & Message.CRIT:
            n = notify2.Notification("Ordinance: Critical", out)
            n.show()
