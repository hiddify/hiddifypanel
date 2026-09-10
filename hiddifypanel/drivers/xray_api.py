import xtlsapi
from loguru import logger

from hiddifypanel.models import ConfigEnum, hconfig
from hiddifypanel.models.usage_data import UsageData

from .abstract_driver import DriverABS


class XrayApi(DriverABS):
    def is_enabled(self) -> bool:
        return hconfig(ConfigEnum.core_type) == "xray"

    def get_xray_client(self):
        if not hasattr(self, "xray_client"):
            self.xray_client = xtlsapi.XrayClient("127.0.0.1", 10085)
        return self.xray_client

    def get_enabled_users(self):
        return {u: 1 for u in self.get_enabled_users_terminal()}
        # xray_client = self.get_xray_client()
        # usages = xray_client.stats_query('user', reset=True)
        # res = defaultdict(int)
        # tags = set(self.get_inbound_tags())
        # for use in usages:
        #     if "user>>>" not in use.name:
        #         continue
        #     uuid = use.name.split(">>>")[1].split("@")[0]
        #     res[uuid]=1

        #     #TODO use xtls api
        #     for t in tags.copy():
        #         try:
        #             self.__add_uuid_to_tag(uuid, t)
        #             self._remove_client(uuid, [t], False)
        #             # print(f"Success add  {uuid} {t}")
        #             res[uuid] = 0
        #             break
        #         except ValueError:
        #             # tag invalid
        #             tags.remove(t)
        #             pass
        #         except xtlsapi.xtlsapi.exceptions.EmailAlreadyExists as e:
        #             res[uuid] = 1
        #             break
        #         except Exception as e:
        #             print(f"error {e}")
        #             # res[uuid] = 1
        #             break

        # return res

        # xray_client = self.get_xray_client()
        # users = User.query.all() # t = "xtls"
        # protocol = "vless"
        # enabled = {}
        # for u in users:
        #     uuid = u.uuid
        #     try:
        #         xray_client.add_client(t, f'{uuid}', f'{uuid}', protocol=protocol, flow='xtls-rprx-vision', alter_id=0, cipher='chacha20_poly1305')
        #         xray_client.remove_client(t, f'{uuid}')
        #         enabled[uuid] = 0
        #     except xtlsapi.xtlsapi.exceptions.EmailAlreadyExists as e:
        #         enabled[uuid] = 1
        #     except Exception as e:
        #         print(f"error {e}")
        #         enabled[uuid] = e
        # return enabled

    # @cache.cache(ttl=300)
    def get_inbound_tags(self):
        try:
            xray_client = self.get_xray_client()
            inbounds = {inb.name.split(">>>")[1] for inb in xray_client.stats_query("inbound")}
            # print(f"Success in get inbound tags {inbounds}")
        except Exception as e:
            print(f"error in get inbound tags {e}")
            inbounds = {}
        return list(inbounds)

    def __add_uuid_to_tag(self, uuid, t):
        xray_client = self.get_xray_client()
        proto_map = {
            "vless": "vless",
            "realityin": "vless",
            "xtls": "vless",
            "quic": "vless",
            "trojan": "trojan",
            "vmess": "vmess",
            "ss": "shadowsocks",
            "v2ray": "shadowsocks",
            "kcp": "vless",
            "dispatcher": "trojan",
            "reality": "vless",
        }

        def proto(t):
            res = "", ""
            for p, protocol in proto_map.items():
                if p in t:
                    res = p, protocol
                    break
            return res

        p, protocol = proto(t)
        if not p:
            raise ValueError("incorrect tag")
        flow = "xtls-rprx-vision" if "realityin_tcp" in t else "\0"
        # if (protocol == "vless" and p != "xtls" and p != "realityin") or "realityingrpc" in t:
        #     xray_client.add_client(t, f'{uuid}', f'{uuid}', protocol=protocol, flow='\0',)
        # else:
        xray_client.add_client(t, f"{uuid}", f"{uuid}", protocol=protocol, flow=flow, alter_id=0, cipher="chacha20_poly1305")

    def add_client(self, user):
        uuid = user.uuid
        xray_client = self.get_xray_client()
        tags = self.get_inbound_tags()

        for t in tags:
            try:
                self.__add_uuid_to_tag(uuid, t)
                # print(f"Success add  {uuid} {t}")
            except ValueError:
                # tag invalid
                pass
            except Exception:
                # print(f"error in add  {uuid} {t} {e}")
                pass

    def remove_client(self, user):
        return self._remove_client(user.uuid)

    def _remove_client(self, uuid, tags=None, dolog=True):
        xray_client = self.get_xray_client()
        tags = tags or self.get_inbound_tags()

        for t in tags:
            try:
                xray_client.remove_client(t, f"{uuid}")
                # if dolog:
                #     logger.info(f"Success remove  {uuid} {t}")
            except Exception as e:
                if dolog:
                    logger.info(f"error in remove  {uuid} {t} {e}")
                pass

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
        import json
        import subprocess

        tags = self.get_inbound_tags()
        for t in tags:
            # Command to execute
            cmd = ["xray", "api", "inbounduser", "--server=127.0.0.1:10085", f"-tag={t}"]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)

                # Parse JSON output
                data = json.loads(result.stdout)
                users = [u.get("email", "") for u in data.get("users", [])]
                if len(data) > 0:
                    return users

            except subprocess.CalledProcessError as e:
                print("Command failed:", e)
                print("Error output:", e.stderr)
            except json.JSONDecodeError as e:
                print("Failed to parse JSON:", e)
        return []
