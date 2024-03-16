import ordinance.writer

def add_known_writers():
    try:
        from .emailwriter import EmailWriter
        ordinance.writer.add_writer_type('email', EmailWriter)
    except Exception as e:
        print("Failed to import EmailWriter: ", e)

    try:
        from .filewriter import FileWriter
        ordinance.writer.add_writer_type('logfile', FileWriter)
    except Exception as e:
        print("Failed to import FileWriter: ", e)

    try:
        from .notifwriter import NotifWriter
        ordinance.writer.add_writer_type('notif', NotifWriter)
    except Exception as e:
        print("Failed to import NotifWriter: ", e)

    try:
        from .stdoutwriter import StdoutWriter
        ordinance.writer.add_writer_type('stdout', StdoutWriter)
    except Exception as e:
        print("Failed to import StdoutWriter: ", e)

    try:
        from .syslogwriter import SyslogWriter
        ordinance.writer.add_writer_type('syslog', SyslogWriter)
    except Exception as e:
        print("Failed to import SyslogWriter: ", e)

