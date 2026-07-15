import json
import os


def get_setting_from_db(key: str, child_id: int = 0) -> str | None:
    from hiddifypanel.models import ConfigEnum, hconfig

    return hconfig(ConfigEnum(key), child_id)


def print_setting(key: str, child_id: int = 0) -> int:
    value = get_setting_from_db(key, child_id)
    if not value:
        return 1
    print(value, end="")
    return 0
