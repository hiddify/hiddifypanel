from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from hiddifypanel.models.user import User


class UserVar(BaseModel):
    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)

    uuid: str = ""
    uuid_hex: str = ""
    name: str = ""
    username: str = ""
    id: int | None = None
    lang: str = ""
    usage_limit_GB: float = 0.0
    current_usage_GB: float = 0.0
    expire_days: int = 0
    is_active: bool = True
    enable: bool = True
    ed25519_public_key: str = ""
    ed25519_private_key: str = ""
    wg_pk: str = ""
    wg_pub: str = ""
    wg_psk: str = ""
    password: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)

    _user: User | None = PrivateAttr(default=None)

    @property
    def wg_ipv4(self) -> str:
        return str(self.extra.get("wg_ipv4") or "")

    @property
    def wg_ipv6(self) -> str:
        return str(self.extra.get("wg_ipv6") or "")

    @classmethod
    def from_user(cls, user: User | None) -> UserVar:
        if user is None:
            return cls()
        uuid = user.uuid or ""
        lang = user.lang.value if getattr(user.lang, "value", None) else (str(user.lang) if user.lang else "")
        var = cls(
            uuid=uuid,
            uuid_hex=uuid.replace("-", ""),
            name=user.name or "",
            username=user.username or user.name or "",
            id=user.id,
            lang=lang,
            usage_limit_GB=float(user.usage_limit_GB or 0),
            current_usage_GB=float(user.current_usage_GB or 0),
            expire_days=int(user.remaining_days),
            is_active=bool(user.is_active),
            enable=bool(user.enable),
            ed25519_public_key=user.ed25519_public_key or "",
            ed25519_private_key=user.ed25519_private_key or "",
            wg_pk=user.wg_pk or "",
            wg_pub=user.wg_pub or "",
            wg_psk=user.wg_psk or "",
            password=uuid,
            extra={},
        )
        var._user = user
        return var
