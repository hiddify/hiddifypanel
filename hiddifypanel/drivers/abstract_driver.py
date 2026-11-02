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

    def add_clients(self, users: list[Any]) -> None:
        """Many users at once (bulk create). Drivers with a per-call setup cost do it once here."""
        for user in users:
            self.add_client(user)

    def remove_client(self, user: Any) -> None:
        pass

    def remove_clients(self, users: list[Any]) -> None:
        """Many users at once (bulk disable / delete)."""
        for user in users:
            self.remove_client(user)

    def is_enabled(self) -> bool:
        return False
