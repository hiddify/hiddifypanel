from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from hiddifypanel.database import db


def _child_unique_id(child_id: int | None) -> str:
    from hiddifypanel.models.child import Child

    if child_id is None:
        return ""
    child = Child.by_id(child_id)
    return child.unique_id if child else ""


class ServerIp(db.Model):  # type: ignore
    """Public server IP addresses (manual or auto-discovered)."""

    __tablename__ = 'server_ip'
    __table_args__ = (
        UniqueConstraint('child_id', 'address', name='uq_server_ip_child_address'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("child.id"), default=0)
    address: Mapped[str] = mapped_column(String(45))
    version: Mapped[int] = mapped_column(SmallInteger, default=4)
    enabled: Mapped[bool] = mapped_column(default=True)
    is_auto: Mapped[bool] = mapped_column(default=False)
    label: Mapped[str | None] = mapped_column(String(200), default="")
    health_status: Mapped[str | None] = mapped_column(String(20))
    last_health_check: Mapped[datetime | None] = mapped_column(DateTime)
    last_health_error: Mapped[str | None] = mapped_column(Text)

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'child_id': self.child_id,
            'child_unique_id': _child_unique_id(self.child_id),
            'address': self.address,
            'version': int(self.version or 4),
            'enabled': bool(self.enabled),
            'is_auto': bool(self.is_auto),
            'label': self.label or '',
            'health_status': self.health_status or '',
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None,
            'last_health_error': self.last_health_error or '',
        }

    @classmethod
    def add_or_update(cls, child_id: int = 0, commit: bool = True, **data) -> ServerIp:
        address = str(data.get("address") or "").strip()
        if not address:
            raise ValueError("address is required")
        row = cls.query.filter(cls.child_id == child_id, cls.address == address).first()
        if not row:
            row = cls(child_id=child_id, address=address)
            db.session.add(row)
        if "version" in data and data["version"] is not None:
            row.version = int(data["version"])
        if "enabled" in data:
            row.enabled = bool(data["enabled"])
        if "is_auto" in data:
            row.is_auto = bool(data["is_auto"])
        if "label" in data:
            row.label = data.get("label") or ""
        if "health_status" in data:
            row.health_status = data.get("health_status") or None
        if "last_health_error" in data:
            row.last_health_error = data.get("last_health_error") or None
        if data.get("last_health_check"):
            raw = data["last_health_check"]
            if isinstance(raw, datetime):
                row.last_health_check = raw
            elif isinstance(raw, str) and raw.strip():
                try:
                    row.last_health_check = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                except ValueError:
                    pass
        if commit:
            db.session.commit()
        return row

    @classmethod
    def bulk_register(cls, ips, commit: bool = True, force_child_unique_id: str | None = None) -> None:
        from hiddifypanel.panel import hiddify

        for item in ips:
            row = item.model_dump() if hasattr(item, "model_dump") else dict(item)
            child_id = hiddify.child_id_from_row(row, force_child_unique_id)
            payload = {k: v for k, v in row.items() if k not in {"id", "child_id", "child_unique_id"}}
            try:
                cls.add_or_update(child_id=child_id, commit=False, **payload)
            except ValueError:
                continue
        if commit:
            db.session.commit()
