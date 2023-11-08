import re
import os
import subprocess
import threading
import aiohttp

from typing import (
    Union,
    Set,
    Dict,
    Any
)

import ordinance.writer
import ordinance.exceptions
import ordinance.util

# ordinance.ext.network -- common networking utilities
# also handles banning and whitelisting ips

def clean_ip(ip: str):
    # if IP is cidr, strip net
    if "/" in ip:  ip = ip.split("/")[0]
    # TODO more?
    return ip


## stolen from Artillery src.core
def is_addr_within_network(ip, net):
    try:
        ipaddr = int(''.join([ '%02x' % int(x) for x in ip.split('.') ]), 16)
        netstr, bits = net.split('/')
        netaddr = int(''.join([ '%02x' % int(x) for x in netstr.split('.') ]), 16)
        mask = (0xffffffff << (32 - int(bits))) & 0xffffffff
        return (ipaddr & mask) == (netaddr & mask)
    except:
       return False


## stolen from Artillery src.core
pattern = re.compile(r"""
^
(?:
  # Dotted variants:
  (?:
    # Decimal 1-255 (no leading 0's)
    [3-9]\d?|2(?:5[0-5]|[0-4]?\d)?|1\d{0,2}
  |
    0x0*[0-9a-f]{1,2}  # Hexadecimal 0x0 - 0xFF (possible leading 0's)
  |
    0+[1-3]?[0-7]{0,2} # Octal 0 - 0377 (possible leading 0's)
  )
  (?:                  # Repeat 0-3 times, separated by a dot
    \.
    (?:
      [3-9]\d?|2(?:5[0-5]|[0-4]?\d)?|1\d{0,2}
    |
      0x0*[0-9a-f]{1,2}
    |
      0+[1-3]?[0-7]{0,2}
    )
  ){0,3}
|
  0x0*[0-9a-f]{1,8}    # Hexadecimal notation, 0x0 - 0xffffffff
|
  0+[0-3]?[0-7]{0,10}  # Octal notation, 0 - 037777777777
|
  # Decimal notation, 1-4294967295:
  429496729[0-5]|42949672[0-8]\d|4294967[01]\d\d|429496[0-6]\d{3}|
  42949[0-5]\d{4}|4294[0-8]\d{5}|429[0-3]\d{6}|42[0-8]\d{7}|
  4[01]\d{8}|[1-3]\d{0,9}|[4-9]\d{0,8}
)
$
""", re.VERBOSE | re.IGNORECASE)
def is_valid_ipv4(ip):
    return pattern.match(clean_ip(ip)) is not None


__should_comment_iptables_bans = False
def initialize(core_config: Dict[str, Any]) -> bool:
    _setup_iptables()
    should_comment_iptables_bans = core_config.get('issue_iptables_ban_comment', False)
    return True

__whitelist = set()
__blacklist = set()
__listlock = threading.Lock()

def ip_to_int(ip: str) -> int:
    """ Encodes a str IP to an int. """
    try:
        intff = lambda i: int(i)&0xFF
        p1,p2,p3,p4 = clean_ip(ip).split('.')
        p1,p2,p3,p4 = intff(p1),intff(p2),intff(p3),intff(p4)
        return (
            (p1 << 24) |  # 0xFF000000
            (p2 << 16) |  # 0x00FF0000
            (p3 << 8 ) |  # 0x0000FF00
            (p4      )    # 0x000000FF
        )
    except:
        raise ordinance.exceptions.IPInvalid(ip)

def int_to_ip(iip: int) -> str:
    """ Resolves an int-encoded IP to a str. """
    try:
        p1 = (iip >> 24) & 0xFF
        p2 = (iip >> 16) & 0xFF
        p3 = (iip >> 8 ) & 0xFF
        p4 = (iip      ) & 0xFF
        return f"{p1}.{p2}.{p3}.{p4}"
    except:
        raise ordinance.exceptions.IPInvalid(iip)


def is_whitelisted(ip: str):
    with __listlock:
        return ip_to_int(ip) in __whitelist

def is_blacklisted(ip: str):
    with __listlock:
        return ip_to_int(ip) in __blacklist

def blacklist(ip: Union[Set[str], str], _check=True, comment: str = ""):
    if isinstance(ip, set):
        for subip in ip: blacklist(subip, _check=False)
        return
    iip = ip_to_int(ip)
    with __listlock:
        if _check and (iip in __whitelist):
            raise ordinance.exceptions.IPWhitelisted(ip)
        __blacklist.add(iip)
    # update iptables
    # note that iptables does not handle thousands of ips very well. for this
    # reason we use ipset, and build sets of ips to cut the search space from
    # O(n) to O(log n)
    #cmd = f"iptables -I ORDINANCE 1 -s {ip} -j DROP"
    #subprocess.run(cmd.split())
    #if should_comment_iptables_bans and comment:
    #    cmd = f'iptables -I ORDINANCE 1 -s {ip} -j LOG --log-prefix "{comment}"'
    #    subprocess.run(cmd.split())

def whitelist(ip: Union[Set[str], str], _check=True):
    if isinstance(ip, set):
        for subip in ip: whitelist(subip, _check=False)
        return
    iip = ip_to_int(ip)
    with __listlock:
        if _check and (iip in __blacklist):
            raise ordinance.exceptions.IPBlacklisted(ip)
        __whitelist.add(iip)

def un_blacklist(ip: Union[Set[str], str], _check=True):
    if isinstance(ip, set):
        for subip in ip: un_blacklist(subip, _check=False)
        return
    iip = ip_to_int(ip)
    with __listlock:
        if _check and (iip not in __blacklist):
            raise ordinance.exceptions.IPNotBlacklisted(ip)
        __blacklist.remove(iip)
    # very basic right now
    # TODO iptables rule

def un_whitelist(ip: Union[Set[str], str], _check=True):
    if isinstance(ip, set):
        for subip in ip: un_whitelist(subip, _check=False)
        return
    iip = ip_to_int(ip)
    with __listlock:
        if _check and (iip not in __whitelist):
            raise ordinance.exceptions.IPNotWhitelisted(ip)
        __whitelist.remove(iip)


def _write_local_list(black_path: str = "local_blacklist.bin", white_path: str = "local_whitelist.bin") -> bool:
    global __blacklist, __whitelist
    # test black
    if not os.path.isfile(black_path):
        ordinance.writer.error("Local blacklist path", black_path, "is not a file!")
        return False
    # test white
    if not os.path.isfile(white_path):
        ordinance.writer.error("Local whitelist path", white_path, "is not a file!")
        return False
    with __listlock:
        # write black
        ordinance.writer.debug("Writing local blacklist file...")
        with open(black_path, 'wb') as file:
            for ip in __blacklist:
                file.write(ip.to_bytes(4))
        ordinance.writer.success(f"Saved {len(__blacklist)} blacklisted IPs to local blacklist file.")
        # write white
        ordinance.writer.debug("Writing local whitelist file...")
        with open(white_path, 'wb') as file:
            for ip in __whitelist:
                file.write(ip.to_bytes(4))
        ordinance.writer.success(f"Saved {len(__whitelist)} whitelisted IPs to local whitelist file.")
    # return
    return True


def _read_local_list(black_path: str = "local_blacklist.bin", white_path: str = "local_whitelist.bin") -> bool:
    global __blacklist, __whitelist
    # test black
    if not os.path.exists(black_path):
        return True
    if not os.path.isfile(black_path):
        ordinance.writer.error("Local blacklist path", black_path, "is not a file!")
        return False
    # test white
    if not os.path.exists(white_path):
        return True
    if not os.path.isfile(white_path):
        ordinance.writer.error("Local whitelist path", white_path, "is not a file!")
        return False
    with __listlock:
        # read black
        __blacklist = set()
        ordinance.writer.debug("Reading local blacklist file...")
        with open(black_path, 'rb') as file:
            data = file.read(4)
            while data:
                __blacklist.add(int.from_bytes(data))
                data = file.read(4)
        ordinance.writer.success(f"Read {len(__blacklist)} blacklisted IPs from local blacklist file.")
        # read white
        __whitelist = set()
        ordinance.writer.debug("Reading local whitelist file...")
        with open(white_path, 'rb') as file:
            data = file.read(4)
            while data:
                __blacklist.add(int.from_bytes(data))
                data = file.read(4)
        ordinance.writer.success(f"Read {len(__whitelist)} whitelisted IPs from local whitelist file.")
    # return
    return True


def _setup_iptables():
    # make iptables table ORDINANCE
    ordinance.writer.debug("Flushing iptables chain and creating a new one...")
    cmds = [
        # (command, can_error)
        # make ORDINANCE chain, attach to filter.INPUT
        ("iptables -D INPUT -j ORDINANCE", True),  # can error if table doesn't exist
        ("iptables -N ORDINANCE", True),  # can error if table already exists
        ("iptables -F ORDINANCE", False),
        ("iptables -I INPUT -j ORDINANCE", False),
        
        # make blacklist ipset
        ("iptables -D ORDINANCE -m set --match-set ORDINANCE_BLACKLIST src -j DROP", True),
          # above and below both can error if set doesn't exist
        ("ipset destroy ORDINANCE_BLACKLIST", True),
        ("ipset create ORDINANCE_BLACKLIST hash:ip", False)
    ]
    for (cmd, can_err) in cmds:
        (ret, res) = ordinance.util.run_shell_cmd(cmd)
        if ret and not can_err:
            ordinance.writer.error(f"iptables setup: '{cmd}' returned code {ret},\n... {res}")
            raise ordinance.exceptions.NetworkException(f"Call to '{cmd.split()[0]}' failed")
    ordinance.writer.debug("Table created.")


def flush_blacklist_to_iptables():
    """ Flushes the blacklist to iptables through ipset. """
    ordinance.writer.info("Flushing blacklist to ipset...")
    global __blacklist
    with __listlock:
        if len(__blacklist) > 65536:  # TODO make this work for >65536
            raise ordinance.exceptions.NetworkException("Too many blacklisted IPs (>65536)")
    # make new /tmp/ directory
    (ret, tmpfile) = ordinance.util.run_shell_cmd("mktemp")
    if ret:  raise ordinance.exceptions.NetworkException("Call to 'mktemp' failed")
    # open temp file and write IPs
    ordinance.writer.debug(f"Writing to tmpfile {tmpfile}")
    with open(tmpfile, 'w') as file:
        with __listlock:
            for ip in __blacklist:
                file.write(f'add "ORDINANCE_BLACKLIST" {int_to_ip(ip)}\n')
    # fill ipset
    with open(tmpfile, 'r') as file:
        (ret, res) = ordinance.util.run_shell_cmd('ipset restore', inpipe=file)
    if ret:
        ordinance.writer.error(f"Call to 'ipset restore' returned {ret}\n{res}")
        raise ordinance.exceptions.NetworkException("Call to 'ipset restore' failed")
    # attach to chain
    cmd = f"iptables -I ORDINANCE -m set --match-set ORDINANCE_BLACKLIST src -j DROP"
    (ret, res) = ordinance.util.run_shell_cmd(cmd)
    if ret:
        ordinance.writer.error(f"Call to 'iptables' returned {ret}\n{res}")
        raise ordinance.exceptions.NetworkException("Call to 'iptables' failed")
    # clean up
    os.remove(tmpfile)
    ordinance.writer.success(f"Flushed blacklist to ipset.")


def create_iptables_input_accept(port_type: str, port: int) -> None:
    """
    Creates an iptables ACCEPT rule on the ORDINANCE chain to accept port
    :attr:`port` of type :attr:`port_type`, which must be either `"tcp"` or
    `"udp"`. Returns `True` if this is successful, `False` if not.
    """
    if port_type != "tcp" and port_type != "udp":
        ordinance.writer.error(f"Could not make iptables rule ACCEPT on port {port}; {port_type} not one of ('tcp','udp')!")
        return False
    ordinance.util.run_shell_cmd(f"iptables -D ORDINANCE -p {port_type} --dport {port} -j ACCEPT -w 5")
    (ret,res) = ordinance.util.run_shell_cmd(f"iptables -A ORDINANCE -p {port_type} --dport {port} -j ACCEPT -w 5")
    out = f"iptables ACCEPT rule on {port_type} port {port}"
    if ret:  ordinance.writer.error(f"Could not create " + out)
    else:    ordinance.writer.debug("Created " + out)
    return ret == 0
