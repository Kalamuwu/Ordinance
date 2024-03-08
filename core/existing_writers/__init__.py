import ordinance.writer

from .emailwriter import EmailWriter
from .filewriter import FileWriter
from .notifwriter import NotifWriter
from .stdoutwriter import StdoutWriter
from .syslogwriter import SyslogWriter

def add_known_writers():
    ordinance.writer.add_writer_type('email',   EmailWriter)
    ordinance.writer.add_writer_type('logfile', FileWriter)
    ordinance.writer.add_writer_type('notif',   NotifWriter)
    ordinance.writer.add_writer_type('stdout',  StdoutWriter)
    ordinance.writer.add_writer_type('syslog',  SyslogWriter)
