import re
import os
import io
import subprocess
import threading

from typing import (
    Union,
    Literal,
    Set,
    Dict,
    Any,
    Optional,
    Iterable
)

import ordinance.writer
import ordinance.exceptions
import ordinance.util
import ordinance.database

# ordinance.network -- common networking utilities
# also handles banning and whitelisting ips



# IPv4 utils

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
_pattern = re.compile(r"""
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
    return _pattern.match(clean_ip(ip)) is not None

def ip_to_int(ip: str) -> int:
    """ Encodes a str IP to an int. """
    def intff(i):  # used to just return (int(i) & 0xFF), hence the name
        try: i = int(i); assert 255 >= i >= 0; return i
        except: raise ValueError()
    try:
        p1,p2,p3,p4 = clean_ip(ip).split('.')
        p1,p2,p3,p4 = intff(p1),intff(p2),intff(p3),intff(p4)
        return (
            (p1 << 24) |  # 0xXX......
            (p2 << 16) |  # 0x..XX....
            (p3 << 8 ) |  # 0x....XX..
            (p4      )    # 0x......XX
        )
    except:
        raise ordinance.exceptions.IPInvalid(ip)

def int_to_ip(iip: int) -> str:
    """ Resolves an int-encoded IP to a str. """
    try:
        p1 = (iip >> 24) & 0xFF  # 0xXX......
        p2 = (iip >> 16) & 0xFF  # 0x..XX....
        p3 = (iip >> 8 ) & 0xFF  # 0x....XX..
        p4 = (iip      ) & 0xFF  # 0x......XX
        return f"{p1}.{p2}.{p3}.{p4}"
    except:
        raise ordinance.exceptions.IPInvalid(iip)

class IPv4Dataset(ordinance.database.BaseDataset):
    """
    Stores a set of unique IPv4 addresses.
    Inherits from :class:`ordinance.database.BaseDatalist`.
    
    Data in the file is laid out as follows:

    ```
    eight bytes
    containing
    the num of    one such
      entries      entry
    .----|----. .----|----.
    AA ..... AA BB BB BB BB [more entries]-->
    ```
    Each entry consists of:
    
    `BB BB BB BB`  Four bytes for this value
    """
    def _serialize(self, file: io.BufferedWriter, data: Set[int]) -> None:
        num_entries = len(data)
        file.write(num_entries.to_bytes(8))
        for v in data: file.write( v.to_bytes(4) )
    
    def _deserialize(self, file: io.BufferedReader) -> Set[int]:
        out = set()
        def read_n(n: int):
            data = file.read(n)
            if len(data) != n: raise ValueError()
            return data
        num_entries = int.from_bytes(file.read(8))
        for i in range(num_entries):
            val = int.from_bytes(read_n(4))
            out.add(val)
        return out
    
    def _value_type(self, value: Any) -> Any:
        try:
            if isinstance(value, int):
                if 0 <= value <= 0xFFFFFFFF: return value
                raise ValueError()
            elif isinstance(value, str):
                return ip_to_int(value)
        except: raise ValueError()

blacklist = IPv4Dataset('storage/core.network.blacklist.database', name="global_whitelist")
whitelist = IPv4Dataset('storage/core.network.whitelist.database', name="global_blacklist")



# iptables bindings

def flush_blacklist_to_iptables() -> None:
    """ Flushes the blacklist to iptables through ipset. """
    global blacklist
    ordinance.writer.info("Flushing blacklist to ipset...")
    if len(blacklist) > 65536:  # TODO make this work for >65536
        raise ordinance.exceptions.NetworkException("Too many blacklisted IPs (>65536)")
    # make new /tmp/ directory
    (ret, tmpfile) = ordinance.util.run_shell_cmd("mktemp")
    if ret:  raise ordinance.exceptions.NetworkException("Call to 'mktemp' failed")
    # open temp file and write IPs
    ordinance.writer.debug(f"Writing to tmpfile {tmpfile}")
    with open(tmpfile, 'w') as file:
        for ip in blacklist.iter():
            file.write(f'add "ORDINANCE_BLACKLIST" {ip}\n')
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

def create_iptables_rule(
    rule_type: Literal['ACCEPT', 'DROP', 'REJECT'] = None,
    port_type: Literal['udp', 'tcp']               = None,
    port: int                                      = None
) -> bool:
    """
    Creates an iptables ACCEPT, DROP, or REJECT rule on the ORDINANCE chain for
    port :attr:`port` of type :attr:`port_type`, which must be either `'tcp'`
    or `'udp'`. Returns `True` if this is successful, `False` if not.
    """
    # check args
    if rule_type is None:                             raise ValueError("rule_type not specified")
    if port_type is None:                             raise ValueError("port_type not specified")
    if port      is None:                             raise ValueError("port not specified")
    if not rule_type in ['ACCEPT', 'DROP', 'REJECT']: raise ValueError(f"rule_type not valid, must be one of 'ACCEPT', 'DROP', 'REJECT' (got '{rule_type}')")
    if not port_type in ['udp', 'tcp']:               raise ValueError(f"port_type not valid, must be one of 'udp', 'tcp' (got '{port_type}')")
    if not isinstance(port, int) or port <= 0:        raise ValueError(f"port not valid, must be integer value >0  (got '{port})")
    # run command
    (ret,res) = ordinance.util.run_shell_cmd(f"iptables -A ORDINANCE -j {rule_type} -p {port_type} --dport {port} -w 5")
    if ret:  ordinance.writer.error(f"Could not create iptables {rule_type} rule on {port_type} port {port}")
    else:    ordinance.writer.debug(         f"Created iptables {rule_type} rule on {port_type} port {port}")
    return ret == 0

def delete_iptables_rule(
    rule_type: Literal['ACCEPT', 'DROP', 'REJECT'] = None,
    port_type: Literal['udp', 'tcp']               = None,
    port: int                                      = None
) -> bool:
    """
    Deletes an iptables ACCEPT, DROP, or REJECT rule on the ORDINANCE chain for
    port :attr:`port` of type :attr:`port_type`, which must be either `'tcp'`
    or `'udp'`. Returns `True` if this is successful, `False` if not.
    """
    # check args
    if rule_type is None:                             raise ValueError("rule_type not specified")
    if port_type is None:                             raise ValueError("port_type not specified")
    if port      is None:                             raise ValueError("port not specified")
    if not rule_type in ['ACCEPT', 'DROP', 'REJECT']: raise ValueError(f"rule_type not valid, must be one of 'ACCEPT', 'DROP', 'REJECT' (got '{rule_type}')")
    if not port_type in ['udp', 'tcp']:               raise ValueError(f"port_type not valid, must be one of 'udp', 'tcp' (got '{port_type}')")
    if not isinstance(port, int) or port <= 0:        raise ValueError(f"port not valid, must be integer value >0  (got '{port})")
    # run command
    (ret,res) = ordinance.util.run_shell_cmd(f"iptables -D ORDINANCE -j {rule_type} -p {port_type} --dport {port} -w 5")
    if ret:  ordinance.writer.error(f"Could not delete iptables {rule_type} rule on {port_type} port {port}")
    else:    ordinance.writer.debug(         f"Deleted iptables {rule_type} rule on {port_type} port {port}")
    return ret == 0
