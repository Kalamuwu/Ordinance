from systemd import journal
import asyncio

from typing import (
    Dict,
    Any
)

import ordinance.exceptions
from .__writer_base import WriterBase, Message

class SyslogWriter(WriterBase):
    """ Writer that writes to syslog. """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, 0)
        self.importances = {
            Message.DBUG:  journal.LOG_INFO,
            Message.INFO:  journal.LOG_INFO,
            Message.SUCC:  journal.LOG_NOTICE,
            Message.WARN:  journal.LOG_WARNING,
            Message.ERRR:  journal.LOG_ERR,
            Message.CRIT:  journal.LOG_CRIT,
            Message.ALRT:  journal.LOG_ALERT,
        }

    def handle(self, msg: Message):
        out = ' '.join(str(m) for m in msg.message)
        journal.send(out, PRIORITY=self.importances[msg.importance])
