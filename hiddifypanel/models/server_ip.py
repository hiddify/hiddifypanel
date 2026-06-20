from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, SmallInteger, String, Text, UniqueConstraint

from hiddifypanel.database import db


class ServerIp(db.Model):  # type: ignore
    """Public server IP addresses (manual or auto-discovered)."""

    __tablename__ = 'server_ip'
    __table_args__ = (
        UniqueConstraint('child_id', 'address', name='uq_server_ip_child_address'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    child_id = Column(Integer, ForeignKey('child.id'), default=0, nullable=False)
    address = Column(String(45), nullable=False)
    version = Column(SmallInteger, nullable=False, default=4)
    enabled = Column(Boolean, default=True, nullable=False)
    is_auto = Column(Boolean, default=False, nullable=False)
    label = Column(String(200), default='')
    health_status = Column(String(20), nullable=True)
    last_health_check = Column(DateTime, nullable=True)
    last_health_error = Column(Text, nullable=True)

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
