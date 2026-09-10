import json
import os

import xtlsapi
from loguru import logger

from hiddifypanel.cache import cache
from hiddifypanel.models import *
from hiddifypanel.models.usage_data import UsageData

from .abstract_driver import DriverABS


class SingboxApi(DriverABS):
    def is_enabled(self) -> bool:
        return True

    def get_singbox_client(self):
        return xtlsapi.SingboxClient("127.0.0.1", 10086)

    def get_enabled_users(self):
        config_dir = os.environ["HIDDIFY_CONFIG_PATH"]
        with open(f"{config_dir}/generated/hiddify-core.json") as f:
            json_data = json.load(f)
            return {u.split("@")[0]: 1 for u in json_data["experimental"]["v2ray_api"]["stats"]["users"]}

    @cache.cache(ttl=300)
    def get_inbound_tags(self):
        try:
            xray_client = self.get_singbox_client()
            inbounds = [inb.name.split(">>>")[1] for inb in xray_client.stats_query("inbound")]
            # print(f"Success in get inbound tags {inbounds}")
        except Exception as e:
            print(f"error in get inbound tags {e}")
            inbounds = []
        return list(set(inbounds))

    def add_client(self, user):
        pass

    def remove_client(self, user):
        pass

    def get_all_usage(self) -> dict[str, UsageData]:
        res: dict[str, UsageData] = {}
        try:
            xray_client = self.get_singbox_client()
            usages = xray_client.stats_query("user", reset=True)
        except Exception as e:
            logger.warning(f"hiddify-core stats unavailable: {e}")
            return res
        for use in usages:
            if "user>>>" not in use.name:
                continue
            parts = use.name.split(">>>")
            if len(parts) < 2:
                continue
            uuid = parts[1].split("@")[0]
            direction = parts[-1].lower() if len(parts) >= 4 else ""
            upload = int(use.value or 0) if direction == "uplink" else 0
            download = int(use.value or 0) if direction != "uplink" else 0
            row = UsageData(uuid=uuid, upload=upload, download=download)
            res[uuid] = res[uuid].add(row) if uuid in res else row
        return res

    def get_usage_imp(self, uuid):
        xray_client = self.get_singbox_client()
        d = xray_client.get_client_download_traffic(f"{uuid}", reset=True)
        u = xray_client.get_client_upload_traffic(f"{uuid}", reset=True)
        row = UsageData(uuid=str(uuid), upload=int(u or 0), download=int(d or 0))
        if row.usage:
            logger.debug(f"singbox {uuid} d={d} u={u} sum={row.usage}")
        return row
