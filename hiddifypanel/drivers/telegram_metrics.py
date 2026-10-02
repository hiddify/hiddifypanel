import re
from decimal import Decimal

_PROMETHEUS_NUMBER = r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
_TELEMT_PATTERN = re.compile(
    r'telemt_user_octets_(from_client|to_client)\{user="([^"]+)"\}\s+'
    + _PROMETHEUS_NUMBER
)
_TELEGO_PATTERN = re.compile(
    r'telego_traffic_(in|out)_bytes_total\{[^}]*user="([^"]+)"[^}]*\}\s+'
    + _PROMETHEUS_NUMBER
)


def parse_usage_metrics(raw_output: str, telegram_lib: str) -> dict[str, dict[str, int]]:
    if telegram_lib == "telemt":
        pattern = _TELEMT_PATTERN
        upload_direction = "from_client"
    elif telegram_lib == "telego":
        pattern = _TELEGO_PATTERN
        upload_direction = "in"
    else:
        return {}

    data = {}
    for line in raw_output.splitlines():
        match = pattern.search(line)
        if not match:
            continue

        direction, user, raw_value = match.groups()
        usage = data.setdefault(user, {"down": 0, "up": 0})
        key = "up" if direction == upload_direction else "down"
        usage[key] = int(Decimal(raw_value))

    return data
