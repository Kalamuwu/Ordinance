import notify2

from typing import (
    Dict,
    Any
)

from ordinance.writer import WriterBase, Message

class NotifWriter(WriterBase):
    """ Writer that shows a popup notification. """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
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
