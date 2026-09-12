from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from hiddifypanel.database import db


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
            'address': self.address,
            'version': int(self.version or 4),
            'enabled': bool(self.enabled),
            'is_auto': bool(self.is_auto),
            'label': self.label or '',
            'health_status': self.health_status or '',
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None,
            'last_health_error': self.last_health_error or '',
        }
