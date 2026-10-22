import base64
import json
import subprocess
from pathlib import Path

from loguru import logger

from hiddifypanel.models.usage_data import UsageData

from .abstract_driver import DriverABS

# Protocols whose users are added live (shadowsocks: only 2022, whose per-user key the panel derives from the uuid).
_USER_PROTOCOLS = {"vless", "vmess", "trojan", "shadowsocks"}


def _account(uuid: str, protocol: str, method: str):
    """The xray account of a user, as the server templates write it (proxy_templates/xray/server/protocols)."""
    if protocol == "trojan":
        from xtlsapi.xray_api.proxy.trojan import config_pb2

        return config_pb2.Account(password=uuid)
    from xtlsapi.xray_api.proxy.shadowsocks_2022 import config_pb2

    # ss.j2: "password": u.uuid_hex | b64encode
    return config_pb2.Account(key=base64.b64encode(uuid.replace("-", "").encode()).decode())
_XRAY_CONFIG = Path("/opt/hiddify-manager/generated/xray.json")


class XrayApi(DriverABS):
    def is_enabled(self) -> bool:
        # The generated xray.json is what matters; core_type may be "both" / hiddify_core while xray still runs.
        return _XRAY_CONFIG.is_file()

    def get_xray_client(self):
        if not hasattr(self, "xray_client"):
            import xtlsapi

            self.xray_client = xtlsapi.XrayClient("127.0.0.1", 10085)
        return self.xray_client

    def get_enabled_users(self):
        return {u: 1 for u in self.get_enabled_users_terminal()}

    def _inbound_meta(self) -> dict[str, dict]:
        """tag → {protocol, flow} from the generated config (not tag-name sniffing)."""
        try:
            data = json.loads(_XRAY_CONFIG.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"xray config unreadable: {e}")
            return {}
        out: dict[str, dict] = {}
        for inb in data.get("inbounds") or []:
            tag = inb.get("tag")
            if not tag:
                continue
            protocol = (inb.get("protocol") or "").strip()
            if not protocol:
                continue
            settings = inb.get("settings") or {}
            # The flow can be set for the whole inbound (vision); a user added without it is rejected.
            flow = str(settings.get("flow") or "")
            for client in settings.get("clients") or []:
                if client.get("flow"):
                    flow = str(client["flow"])
                    break
            out[str(tag)] = {"protocol": protocol, "flow": flow, "method": str(settings.get("method") or "")}
        return out

    def get_inbound_tags(self):
        try:
            xray_client = self.get_xray_client()
            inbounds = {inb.name.split(">>>")[1] for inb in xray_client.stats_query("inbound")}
        except Exception as e:
            print(f"error in get inbound tags {e}")
            inbounds = {}
        return list(inbounds)

    def __add_uuid_to_tag(self, uuid, t, *, protocol: str, flow: str, method: str = ""):
        xray_client = self.get_xray_client()
        if protocol in ("trojan", "shadowsocks"):
            # xtlsapi cannot: it gives trojan a flow field it does not have, and has no shadowsocks 2022.
            self.__add_user(t, f"{uuid}", _account(uuid, protocol, method))
            return
        # Empty flow (not "\0"): xtlsapi / xray reject the null-byte sentinel for non-vision inbounds.
        kwargs = dict(protocol=protocol, alter_id=0, cipher="chacha20_poly1305")
        if flow:
            kwargs["flow"] = flow
        xray_client.add_client(t, f"{uuid}", f"{uuid}", **kwargs)

    def __add_user(self, tag: str, email: str, account) -> None:
        from xtlsapi.ext import utils
        from xtlsapi.xray_api.app.proxyman.command import command_pb2
        from xtlsapi.xray_api.common.protocol import user_pb2

        user = user_pb2.User(email=email, account=utils.to_typed_message(account))
        operation = utils.to_typed_message(command_pb2.AddUserOperation(user=user))
        self.get_xray_client().handler_stub.AlterInbound(command_pb2.AlterInboundRequest(tag=tag, operation=operation))

    def add_client(self, user):
        uuid = user.uuid
        meta = self._inbound_meta()
        # The inbounds of the generated config: the stats list misses inbounds without traffic yet.
        for t, info in meta.items():
            if info["protocol"] not in _USER_PROTOCOLS or (info["protocol"] == "shadowsocks" and not info["method"].startswith("2022-")):
                continue
            try:
                self.__add_uuid_to_tag(uuid, t, protocol=info["protocol"], flow=info.get("flow") or "", method=info["method"])
            except Exception as e:
                if "already exists" not in str(e):
                    logger.warning(f"xray: could not add user {uuid} to {t}: {e}")

    def remove_client(self, user):
        # New connections of the user are refused; xray keeps the open ones until they close (no API to cut them).
        # On purpose: restarting xray to cut them drops every user's connections.
        return self._remove_client(user.uuid)

    def _remove_client(self, uuid, tags=None, dolog=True):
        xray_client = self.get_xray_client()
        tags = tags or self.get_inbound_tags()

        for t in tags:
            try:
                xray_client.remove_client(t, f"{uuid}")
            except Exception as e:
                if dolog:
                    logger.info(f"error in remove  {uuid} {t} {e}")

    def get_all_usage(self) -> dict[str, UsageData]:
        res: dict[str, UsageData] = {}
        try:
            xray_client = self.get_xray_client()
            usages = xray_client.stats_query("user", reset=True)
        except Exception as e:
            logger.warning(f"xray stats unavailable: {e}")
            return res
        for use in usages:
            if "user>>>" not in use.name:
                continue
            parts = use.name.split(">>>")
            if len(parts) < 2:
                continue
            uuid = parts[1]
            direction = parts[-1].lower() if len(parts) >= 4 else ""
            upload = int(use.value or 0) if direction == "uplink" else 0
            download = int(use.value or 0) if direction != "uplink" else 0
            row = UsageData(uuid=uuid, upload=upload, download=download)
            res[uuid] = res[uuid].add(row) if uuid in res else row
        return res

    def get_usage_imp(self, uuid):
        xray_client = self.get_xray_client()
        d = xray_client.get_client_download_traffic(f"{uuid}", reset=True)
        u = xray_client.get_client_upload_traffic(f"{uuid}", reset=True)
        row = UsageData(uuid=str(uuid), upload=int(u or 0), download=int(d or 0))
        if row.usage:
            logger.debug(f"Xray usage {uuid} d={d} u={u} sum={row.usage}")
        return row

    def get_enabled_users_terminal(self):
        tags = self.get_inbound_tags()
        users: set[str] = set()
        for t in tags:
            cmd = ["/opt/hiddify-manager/services/xray/bin/xray", "api", "inbounduser", "--server=127.0.0.1:10085", f"-tag={t}"]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                data = json.loads(result.stdout)
                for u in data.get("users", []) or []:
                    email = u.get("email") or ""
                    if email:
                        users.add(email)
            except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
                print(f"inbounduser {t}: {e}")
        return list(users)
