from __future__ import annotations

from typing import Any

from hiddifypanel.models.usage_data import UsageData


class DriverABS:
    def get_all_usage(self) -> dict[str, UsageData]:
        return {}

    def get_enabled_users(self) -> dict[str, Any]:
        return {}

    def add_client(self, user: Any) -> None:
        pass

    def remove_client(self, user: Any) -> None:
        pass

    def is_enabled(self) -> bool:
        return False
