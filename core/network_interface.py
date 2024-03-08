import shutil
import shlex
import subprocess

import ordinance.network

def read_dbs():
    try: ordinance.network.blacklist.read()
    except Exception as e:
        ordinance.writer.error(f"Failed to read blacklist, with error:")
        ordinance.writer.error(e)
        ordinance.network.blacklist.clear()
    else: ordinance.writer.success(f"Read {len(ordinance.network.blacklist)} IPv4 addresses into blacklist")

    try: ordinance.network.whitelist.read()
    except Exception as e:
        ordinance.writer.error(f"Failed to read whitelist, with error:")
        ordinance.writer.error(e)
        ordinance.network.whitelist.clear()
    else: ordinance.writer.success(f"Read {len(ordinance.network.whitelist)} IPv4 addresses into whitelist")

def setup_iptables() -> bool:
    ordinance.writer.debug(f"Flushing iptables chain and creating a new one...")

    can_fail_commands = [
        "iptables -D INPUT -j ORDINANCE",
        "iptables -D ORDINANCE -m set --match-set ORDINANCE_BLACKLIST src -j DROP",
        "ipset destroy ORDINANCE_BLACKLIST"
        "iptables --delete-chain ORDINANCE",
    ]
    for cmd in can_fail_commands:
        code,stdout = subprocess.getstatusoutput(cmd)
        #if code: pass
    
    must_succeed_commands = [
        "iptables -N ORDINANCE",
        "iptables -F ORDINANCE",
        "iptables -I INPUT -j ORDINANCE",
        "ipset create ORDINANCE_BLACKLIST hash:ip"
    ]
    for cmd in must_succeed_commands:
        code,stdout = subprocess.getstatusoutput(cmd)
        if code:
            ordinance.writer.error(f"Could not setup IPtables, code {code}, with error:")
            ordinance.writer.error(stdout)
            return False
    
    ordinance.writer.info(f"Successfully setup IPtables")
    return True
        