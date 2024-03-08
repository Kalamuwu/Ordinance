import os

from typing import (
    Dict,
    List,
    Tuple,
    Any
)

import ordinance.exceptions
from ordinance.writer import WriterBase, Message

default_strftime = "%Y-%d-%b %H:%M:%S"

class FileWriter(WriterBase):
    """ Writer that outputs to one or more logfiles. """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # verify paths is a list
        tmppaths = config.get('files')
        if not isinstance(tmppaths, list):
            raise ordinance.exceptions.InvalidConfigValue("writers.logfile.files must be a list")
        # verify paths are valid entries
        for obj in tmppaths:
            if not isinstance(obj, dict) or 'path' not in obj or 'mask' not in obj:
                raise ordinance.exceptions.InvalidConfigValue("writers.logfile.files must be a list of { 'path': str, 'mask': int, 'strftime': str } objects")
            if 'strftime' not in obj:
                obj['strftime'] = default_strftime
        # ensure files exist
        self.paths: List[Tuple[str, int, str]] = []
        for obj in tmppaths:
            path = os.path.abspath(obj['path'])
            print(path)
            if not os.path.isfile(path):
                with open(obj['path'], 'w') as file:
                    file.write('')
            self.paths.append( (obj['path'], obj['mask'], obj['strftime']) )
        # misc
        self.headers = {
            Message.DBUG:  "debug    ",
            Message.INFO:  "info     ",
            Message.SUCC:  "SUCCESS  ",
            Message.WARN:  "WARN     ",
            Message.ERRR:  "ERROR    ",
            Message.CRIT:  "CRITICAL ",
            Message.ALRT:  "ALERT    ",
        }

    def handle(self, msg: Message):
        header = self.headers[msg.importance]
        out = ' '.join(str(m) for m in msg.message)
        for (path,mask,strftime) in self.paths:
            if mask & msg.importance:
                with open(path, 'a') as file:
                    date = msg.time.strftime(strftime)
                    out_to_file = out.replace('\n', f'\n{date} {header}')
                    print(header, out_to_file, flush=True, file=file)
