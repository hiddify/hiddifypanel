from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from hiddifypanel.database import db

if TYPE_CHECKING:
    from hiddifypanel.models.external_model.network import ServerIpModel


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

    def to_model(self) -> ServerIpModel:
        from hiddifypanel.models.external_model.network import ServerIpModel

        return ServerIpModel(
            id=self.id,
            child_id=self.child_id,
            child_unique_id=_child_unique_id(self.child_id),
            address=self.address,
            version=int(self.version or 4),
            enabled=bool(self.enabled),
            is_auto=bool(self.is_auto),
            label=self.label or '',
            health_status=self.health_status or '',
            last_health_check=self.last_health_check,
            last_health_error=self.last_health_error or '',
        )

    def to_dict(self) -> dict[str, Any]:
        return self.to_model().to_dict()

    @classmethod
    def add_or_update(cls, child_id: int = 0, commit: bool = True, **data) -> ServerIp:
        from hiddifypanel.models.external_model.network import ServerIpModel

        return cls.upsert(ServerIpModel.coerce(data), child_id=child_id, commit=commit)

    @classmethod
    def upsert(cls, data: ServerIpModel, *, child_id: int = 0, commit: bool = True) -> ServerIp:
        row = cls.query.filter(cls.child_id == child_id, cls.address == data.address).first()
        if not row:
            row = cls(child_id=child_id, address=data.address)
            db.session.add(row)
        if data.version is not None:
            row.version = data.version
        if data.has("enabled"):
            row.enabled = bool(data.enabled)
        if data.has("is_auto"):
            row.is_auto = bool(data.is_auto)
        if data.has("label"):
            row.label = data.label or ""
        if data.has("health_status"):
            row.health_status = data.health_status or None
        if data.has("last_health_error"):
            row.last_health_error = data.last_health_error or None
        if data.last_health_check is not None:
            row.last_health_check = data.last_health_check
        if commit:
            db.session.commit()
        return row

    @classmethod
    def bulk_register(cls, ips, commit: bool = True, force_child_unique_id: str | None = None) -> None:
        from hiddifypanel.models.external_model.network import ServerIpModel
        from hiddifypanel.panel import hiddify

        for item in ips:
            try:
                data = ServerIpModel.coerce(item)
            except ValueError:
                continue
            child_id = hiddify.child_id_from_row({"child_unique_id": data.child_unique_id}, force_child_unique_id)
            cls.upsert(data, child_id=child_id, commit=False)
        if commit:
            db.session.commit()
