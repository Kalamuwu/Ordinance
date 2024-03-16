from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders
import smtplib

from typing import (
    Dict,
    Any
)

from ordinance.writer import WriterBase, Message

class EmailWriter(WriterBase):
    """ Writer that functions via an email server. """
    def __init__(self, config: Dict[str, Any]):
        ############################################
        raise NotImplementedError("no email fo you")
        ############################################
        super().__init__(config)
        self.server = {
            'ip': config.get('smtp.ip'),
            'port': config.get('smtp.port', 25)
        }
        self.credentials = {
            'username': config.get('credentials.username'),
            'password': config.get('credentials.password'),
        }
        self.meta = {
            'from': config.get('meta.from', "Ordinance_Incident@localhost"),
            'to': config.get('meta.to'),
            'title': config.get('meta.title', "Ordinance Alerts")
        }
        self.keepalive = config.get_config('writers.email.keepalive', False)
        self.__smtp_con = None
        if self.keepalive: self.__login()
    
    def __login(self):
        """ Attempts to login to SMTP server and establish connection. """
        try:
            mail_server = smtplib.SMTP(
                host=self.server['ip'],
                port=self.server['port']
            )
            mail_server.ehlo()
            mail_server.starttls()  # tls support?
            mail_server.ehlo()  # some servers require ehlo again
            mail_server.login(
                user=self.credentials['username'],
                password=self.credentials['password']
            )
        except Exception as e:
            self.__smtp_con = None
            raise
        else:
            self.__smtp_con = mail_server
    
    def close(self):
        if self.__smtp_con is not None:
            # are both necessary?
            self.__smtp_con.quit()
            self.__smtp_con.close()
            self.__smtp_con = None

    def handle(self):
        pass


# Below is from the old src file, for sending emails. Probably still useful.
"""
def send_mail(subject, text):
    mail(read_config("ALERT_USER_EMAIL"), subject, text)

# mail function preping to send
def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def mail(to, subject, text):
    enabled = read_config("EMAIL_ALERTS")
    if enabled == "ON":
        try:
            user = read_config("SMTP_USERNAME")
            pwd = read_config("SMTP_PASSWORD")
            smtp_address = read_config("SMTP_ADDRESS")
            # port we use, default is 25
            smtp_port = int(read_config("SMTP_PORT"))
            smtp_from = read_config("SMTP_FROM")
            msg = MIMEMultipart()
            msg['From'] = smtp_from
            msg['To'] = to
            msg['Date'] = formatdate(localtime=True)
            msg['Message-Id'] = "<" + id_generator(20) + "." + smtp_from + ">"
            msg['Subject'] = subject
            msg.attach(MIMEText(text))
            # prep the smtp server
            mailServer = smtplib.SMTP("%s" % (smtp_address), smtp_port)
            #if user == '':
            #    write_console("[!] Email username is blank. please provide address in config file")
            
            # send ehlo
            mailServer.ehlo()
            if not user == "": 
                # tls support?
                mailServer.starttls()
                # some servers require ehlo again
                mailServer.ehlo()
                mailServer.login(user, pwd)
            # send the mail
            write_log("Sending email to %s: %s" % (to, subject))
            mailServer.sendmail(smtp_from, to, msg.as_string())
            mailServer.close()

        except Exception as err:
            write_log("Error, Artillery was unable to log into the mail server %s:%d" % (
                smtp_address, smtp_port),2)
            emsg = traceback.format_exc()
            write_log("Error: " + str(err),2)
            write_log(" %s" % emsg,2)
            write_console("[!] Artillery was unable to send email via %s:%d" % (smtp_address, smtp_port))
            write_console("[!] Error: %s" % emsg)
            pass
    else:
        write_console("[*] Email alerts are not enabled. please look @ %s to enable." % (globals.g_configfile))
"""
