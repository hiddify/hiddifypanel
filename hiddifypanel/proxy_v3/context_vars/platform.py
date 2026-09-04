from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, PrivateAttr, Field

from .version import PlatformPart, TemplateVersion
from hiddifypanel import hutils


class PlatformVar(BaseModel):
    """Client platform derived from User-Agent."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    os_version: str = ""
    root_access: bool = False
    app_group_version: str = ""
    useragent: str = ""
    tls_engine: str = "go"
    is_hiddify: bool = False

    os: PlatformPart = Field(default_factory=lambda: PlatformPart("linux"))
    app: PlatformPart = Field(default_factory=lambda: PlatformPart("unknown"))
    app_group: PlatformPart = Field(default_factory=lambda: PlatformPart("singbox"))
    singbox: PlatformPart = Field(default_factory=lambda: PlatformPart("singbox"))
    hiddify: PlatformPart = Field(default_factory=lambda: PlatformPart("hiddify"))
    xray: PlatformPart = Field(default_factory=lambda: PlatformPart("xray"))
    app_version: TemplateVersion = Field(default_factory=TemplateVersion)

    @classmethod
    def from_user_agent(cls, ua: str) -> PlatformVar:
        raw = (ua or "").strip()
        info = dict(hutils.flask.parse_user_agent(raw) or {})
        os_family = cls._detect_os(raw, info)
        app = cls._detect_app(raw, info)
        app_group = cls._detect_app_group(raw, info, app)
        app_version = cls._detect_app_version(raw, info, app, app_group)
        group_version = cls._detect_group_version(info, app_group)

        os_version = ".".join(str(x) for x in (info.get("os_version") or []) if x) or ""
        singbox_version = ".".join(str(x) for x in (info.get("singbox_version") or []) if x) or ""
        hiddify_version = ".".join(str(x) for x in (info.get("hiddify_version") or []) if x) or ""
        xray_version = ".".join(str(x) for x in (info.get("xray_version") or []) if x) or ""
        if app == "v2rayn" and xray_version == "" and app_version:
            if TemplateVersion(app_version) >= "7.20.0":
                xray_version = "26.3.27"
            else:
                xray_version = "25.12.31"

        var = cls(
            os_version=os_version,
            root_access=bool(info.get("root_access", False)),
            app_group_version=group_version,
            useragent=raw,
            tls_engine=cls._tls_engine(os_family),
            is_hiddify=bool(info.get("is_hiddify")),
        )
        var.os = PlatformPart(os_family, os_version)
        var.app = PlatformPart(app, app_version)
        var.app_version = TemplateVersion(app_version)
        var.app_group = PlatformPart(app_group, group_version or singbox_version)
        var.singbox = PlatformPart("singbox", singbox_version)
        var.hiddify = PlatformPart("hiddify", hiddify_version)
        var.xray = PlatformPart("xray", xray_version)
        return var

    @staticmethod
    def _detect_os(ua: str, info: dict[str, Any]) -> str:
        lowered = ua.lower()
        for token, name in (
            ("(android)", "android"),
            ("(ios)", "ios"),
            ("(iphone)", "ios"),
            ("(ipad)", "ios"),
            ("(windows)", "windows"),
            ("(linux)", "linux"),
            ("(macos)", "macos"),
            ("(mac os", "macos"),
        ):
            if token in lowered:
                return name
        return _normalize_os(info.get("os"))

    @staticmethod
    def _tls_engine(os_name: str) -> str:
        if os_name in ("ios", "macos"):
            return "apple"
        if os_name == "windows":
            return "windows"
        return "go"

    @staticmethod
    def _detect_app(ua: str, info: dict[str, Any]) -> str:
        if info.get("app"):
            return str(info["app"]).lower()
        if info.get("is_hiddify"):
            return "hiddify"
        if info.get("is_singbox"):
            return "singbox"
        if info.get("is_v2rayng"):
            return "v2rayng"
        if info.get("is_clash_meta"):
            return "clash-meta"
        if info.get("is_clash"):
            return "clash"
        lowered = ua.lower()
        if "hiddify" in lowered:
            return "hiddify"
        if "sing-box" in lowered or "singbox" in lowered:
            return "singbox"
        if "xray" in lowered:
            return "xray"
        if "v2rayng" in lowered:
            return "v2rayng"
        if "v2rayn" in lowered:
            return "v2rayn"
        return "unknown"

    @staticmethod
    def _detect_app_group(ua: str, info: dict[str, Any], app: str) -> str:
        if info.get("is_singbox") or info.get("is_hiddify"):
            return "singbox"
        if info.get("is_clash") or info.get("is_clash_meta"):
            return "clash"
        if info.get("is_v2ray") or info.get("is_v2rayng"):
            return "xray"
        for pattern, group in _APP_GROUP_MAP:
            if re.search(pattern, ua):
                return group
        if app in ("hiddify", "singbox"):
            return "singbox"
        if "clash" in app:
            return "clash"
        if "v2ray" in app or app == "xray":
            return "xray"
        return "singbox"

    @staticmethod
    def _detect_app_version(ua: str, info: dict[str, Any], app: str, group: str) -> str:
        for key in ("hiddify_version", "singbox_version", "v2rayng_version"):
            ver = info.get(key)
            if ver:
                return ".".join(str(x) for x in ver)
        match = re.search(r"/(\d+\.\d+(?:\.\d+)?)", ua)
        if match:
            return match.group(1)
        return ""

    @staticmethod
    def _detect_group_version(info: dict[str, Any], group: str) -> str:

        if group == "singbox" and info.get("singbox_version"):
            return ".".join(str(x) for x in info["singbox_version"])
        if group == "xray" and info.get("v2rayng_version"):
            return ".".join(str(x) for x in info["v2rayng_version"])
        return ""


_OS_NORMALIZE = {
    "android": "android",
    "ios": "ios",
    "windows": "windows",
    "linux": "linux",
    "mac os x": "macos",
    "macos": "macos",
}

_APP_GROUP_MAP: list[tuple[str, str]] = [
    (r"(?i)(hiddify|sing-box|singbox|sfa|sfi|dart)", "singbox"),
    (r"(?i)(clash|stash|nekobox|nekoray|pharos|meta)", "clash"),
    (r"(?i)(v2ray|v2rayng|sagernet|foxray|fair|shadowrocket|v2box|loon|liberty)", "xray"),
    (r"(?i)(sub|subscription|sublink)", "sublink"),
]


def _normalize_os(family: str | None) -> str:
    if not family:
        return "linux"
    key = family.strip().lower()
    return _OS_NORMALIZE.get(key, key)
