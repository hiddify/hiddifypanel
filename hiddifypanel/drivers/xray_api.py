import json
import subprocess
from pathlib import Path

from loguru import logger

from hiddifypanel.models.usage_data import UsageData

from .abstract_driver import DriverABS

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
            flow = ""
            for client in (inb.get("settings") or {}).get("clients") or []:
                if client.get("flow"):
                    flow = str(client["flow"])
                    break
            out[str(tag)] = {"protocol": protocol, "flow": flow}
        return out

    def get_inbound_tags(self):
        try:
            xray_client = self.get_xray_client()
            inbounds = {inb.name.split(">>>")[1] for inb in xray_client.stats_query("inbound")}
        except Exception as e:
            print(f"error in get inbound tags {e}")
            inbounds = {}
        return list(inbounds)

    def __add_uuid_to_tag(self, uuid, t, *, protocol: str, flow: str):
        xray_client = self.get_xray_client()
        # Empty flow (not "\0"): xtlsapi / xray reject the null-byte sentinel for non-vision inbounds.
        kwargs = dict(protocol=protocol, alter_id=0, cipher="chacha20_poly1305")
        if flow:
            kwargs["flow"] = flow
        xray_client.add_client(t, f"{uuid}", f"{uuid}", **kwargs)

    def add_client(self, user):
        uuid = user.uuid
        meta = self._inbound_meta()
        for t in self.get_inbound_tags():
            info = meta.get(t)
            if not info:
                continue
            try:
                self.__add_uuid_to_tag(uuid, t, protocol=info["protocol"], flow=info.get("flow") or "")
            except Exception:
                pass

    def remove_client(self, user):
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
