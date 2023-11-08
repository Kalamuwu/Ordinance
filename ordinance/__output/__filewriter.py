import asyncio
import os

from typing import (
    Dict,
    List,
    Tuple,
    Any
)

import ordinance.exceptions
from .__writer_base import WriterBase, Message

class FileWriter(WriterBase):
    """ Writer that outputs to one or more logfiles. """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, 0)
        tmppaths = config.get_config('files')
        if not isinstance(tmppaths, list):
            raise ordinance.exceptions.InvalidConfigValue("writers.logfile.files must be a list")
        # verify paths are real files
        self.paths: List[Tuple[str, int]]
        for obj in tmppaths:
            if not isinstance(obj, dict) or 'path' not in obj or 'mask' not in obj:
                raise ordinance.exceptions.InvalidConfigValue("writers.logfile.files must be a list of { 'path': str, 'mask': int } objects")
            if not os.path.isfile(obj['path']):
                raise ordinance.exceptions.InvalidConfigValue(f"Unknown logfile path {obj['path']}")
            self.paths.append( (obj['path'], obj['mask']) )
        # misc
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
        for (path,mask) in self.paths:
            if mask & msg.importance:
                with open(path, 'w') as file:
                    print(header, out, flush=True, file=file)
