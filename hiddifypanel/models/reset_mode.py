"""How often an account's used traffic goes back to zero: users and admins share the periods and the schedule."""

from __future__ import annotations

import datetime
from enum import auto

from strenum import StrEnum


class UserMode(StrEnum):
    """
    The "UserMode" class is an enumeration that defines five possible modes: "no_reset", "monthly", "weekly",
    "daily", and "disable". These modes represent different settings that can be applied to a user account,
    such as the frequency at which data is reset or whether the account is currently disabled. The class is
    implemented using the "StrEnum" base class and the "auto()" function to generate unique values for each mode.
    """

    no_reset = auto()
    monthly = auto()
    weekly = auto()
    daily = auto()
    # disable = auto()


package_mode_dic = {UserMode.daily: 1, UserMode.weekly: 7, UserMode.monthly: 30}


def should_reset(mode: UserMode | None, start_date: datetime.date | None, last_reset_time: datetime.date | None) -> bool:
    """A period of ``mode`` counted from ``start_date`` ends today, and the usage was not reset today yet."""
    if not last_reset_time:
        return True
    elif not start_date or (datetime.date.today() - last_reset_time).days == 0:
        return False
    return ((datetime.date.today() - start_date).days % package_mode_dic.get(mode, 10000)) == 0


def days_to_reset(mode: UserMode | None, start_date: datetime.date | None) -> int:
    """Days until the next reset (the whole period when it has not started)."""
    period = package_mode_dic.get(mode, 10000)
    if start_date:
        days = period - (datetime.date.today() - start_date).days % period
    else:
        days = period
    return max(-100000, min(days, 100000))
