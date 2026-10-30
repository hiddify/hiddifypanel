import random
import string
from hiddifypanel.models import hconfig, ConfigEnum


def get_random_string(min_: int = 10, max_: int = 30) -> str:
    # With combination of lower and upper case
    length = random.randint(min_, max_)
    characters = string.ascii_letters + string.digits
    result_str = ''.join(random.choice(characters) for i in range(length))
    return result_str


def get_random_password(length: int = 16) -> str:
    '''Retunrns a random password with fixed length'''
    characters = string.ascii_letters + string.digits  # + '-'
    while True:
        passwd = ''.join(random.choice(characters) for i in range(length))
        if (any(c.islower() for c in passwd) and any(c.isupper() for c in passwd) and sum(c.isdigit() for c in passwd) > 1):
            return passwd


def __is_port_in_range(port, start_port: int | str | None, count: int):
    if start_port is None:
        return False
    start_port = int(start_port)
    if port < start_port:
        return False

    if port > start_port + count:
        return False
    return True


def __is_in_used_port(port):
    for k in ConfigEnum:
        if "port" in k:
                for p in (hconfig(k) or "").split(","):
                    if p and __is_port_in_range(port, p, 100):
                        return True
    
    for p in [443, 80, 9000, 10085, 10086]:
        if __is_port_in_range(port, p, 100):
            return True
    return False


def get_random_unused_port():
    port = random.randint(11000, 60000)
    while __is_in_used_port(port):
        port = random.randint(11000, 60000)
    return port


def get_amneziawg_obfuscation() -> dict[str, int]:
    """Random AmneziaWG obfuscation values in the ranges awg accepts: Jmin < Jmax <= 1280, S1 / S2 in 15-150 with
    S1 + 56 != S2 (an init and a response message must not end up the same size), H1-H4 distinct and above 4 (1-4 are
    plain WireGuard's message types)."""
    jmin = random.randint(40, 80)
    s1 = random.randint(15, 150)
    s2 = random.randint(15, 150)
    while s1 + 56 == s2:
        s2 = random.randint(15, 150)
    headers: set[int] = set()
    while len(headers) < 4:
        headers.add(random.randint(5, 2_147_483_647))
    h1, h2, h3, h4 = headers
    return {
        "jc": random.randint(4, 8),
        "jmin": jmin,
        "jmax": random.randint(jmin + 1, 1000),
        "s1": s1,
        "s2": s2,
        "h1": h1,
        "h2": h2,
        "h3": h3,
        "h4": h4,
    }


def random_case(string):
    return ''.join(random.choice((str.upper, str.lower))(c) for c in string)
