from typing import (
    Dict,
    Any
)

import ordinance.exceptions
from ordinance.writer import WriterBase, Message

class colors:
    GREY   = "\033[30m"
    GRAY   = "\033[30m"
    RED    = "\033[31m"
    GREEN  = "\033[32m"
    YELLOW = "\033[33m"
    BLUE   = "\033[34m"
    PURPLE = "\033[35m"
    CYAN   = "\033[36m"
    WHITE  = "\033[37m"

class StdoutWriter(WriterBase):
    """ Writer that writes to stdout. """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.headers = {
            Message.DBUG:          "\033[35m[DBUG]\033[0m ",
            Message.INFO:          "\033[34m[INFO]\033[0m ",
            Message.SUCC:          "\033[32m[SUCC]\033[0m ",
            Message.WARN:          "\033[33m[WARN]\033[0m ",
            Message.ERRR:          "\033[31m[ERRR]\033[0m ",
            Message.CRIT:  "\033[37m\033[41m[CRIT]\033[0m ",
            Message.ALRT:  "\033[37m\033[41m[ALRT]\033[0m ",
        }

    def handle(self, msg: Message):
        header = self.headers[msg.importance]
        out = ' '.join(str(m) for m in msg.message)
        out = out.replace('\n', f'\n{header} ')
        print(header, out, flush=True)
