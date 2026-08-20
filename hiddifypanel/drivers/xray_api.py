import xtlsapi
from hiddifypanel.models import *
from .abstract_driver import DriverABS
from collections import defaultdict
from hiddifypanel.cache import cache
from loguru import logger


class XrayApi(DriverABS):
    def is_enabled(self) -> bool:
        return hconfig(ConfigEnum.core_type) == "xray"

    def get_xray_client(self):
        if not hasattr(self, 'xray_client'):
            self.xray_client = xtlsapi.XrayClient('127.0.0.1', 10085)
        return self.xray_client

    def get_enabled_users(self):
        return {u:1 for u in self.get_enabled_users_terminal()}
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
        #         xray_client.add_client(t, f'{uuid}', f'{uuid}@hiddify.com', protocol=protocol, flow='xtls-rprx-vision', alter_id=0, cipher='chacha20_poly1305')
        #         xray_client.remove_client(t, f'{uuid}@hiddify.com')
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
            inbounds = {inb.name.split(">>>")[1] for inb in xray_client.stats_query('inbound')}
            # print(f"Success in get inbound tags {inbounds}")
        except Exception as e:
            print(f"error in get inbound tags {e}")
            inbounds = {}
        return list(inbounds)

    def __add_uuid_to_tag(self, uuid, t):
        xray_client = self.get_xray_client()
        proto_map = {
            'vless': 'vless',
            'realityin': 'vless',
            'xtls': 'vless',
            'quic': 'vless',
            'trojan': 'trojan',
            'vmess': 'vmess',
            'ss': 'shadowsocks',
            'v2ray': 'shadowsocks',
            'kcp': 'vless',
            'dispatcher': 'trojan',
            'reality': 'vless'
        }

        def proto(t):
            res = '', ''
            for p, protocol in proto_map.items():
                if p in t:
                    res = p, protocol
                    break
            return res
        p, protocol = proto(t)
        if not p:
            raise ValueError("incorrect tag")
        flow='xtls-rprx-vision' if 'realityin_tcp' in t else '\0'
        # if (protocol == "vless" and p != "xtls" and p != "realityin") or "realityingrpc" in t:
        #     xray_client.add_client(t, f'{uuid}', f'{uuid}@hiddify.com', protocol=protocol, flow='\0',)
        # else:
        xray_client.add_client(t, f'{uuid}', f'{uuid}@hiddify.com', protocol=protocol, flow=flow, alter_id=0, cipher='chacha20_poly1305')

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
            except Exception as e:
                # print(f"error in add  {uuid} {t} {e}")
                pass

    def remove_client(self, user):
        return self._remove_client(user.uuid)

    def _remove_client(self, uuid, tags=None, dolog=True):
        xray_client = self.get_xray_client()
        tags = tags or self.get_inbound_tags()

        for t in tags:
            try:
                xray_client.remove_client(t, f'{uuid}@hiddify.com')
                # if dolog:
                #     logger.info(f"Success remove  {uuid} {t}")
            except Exception as e:
                if dolog:
                    logger.info(f"error in remove  {uuid} {t} {e}")
                pass

    def get_all_usage(self)->dict:
        res = defaultdict(int)
        try:
            xray_client = self.get_xray_client()
            usages = xray_client.stats_query('user', reset=True)
        except Exception as e:
            logger.warning(f"xray stats unavailable: {e}")
            return res
        for use in usages:
            if "user>>>" not in use.name:
                continue
            uuid = use.name.split(">>>")[1].split("@")[0]
            res[uuid] += use.value
        return res

    def get_usage_imp(self, uuid):
        xray_client = self.get_xray_client()
        d = xray_client.get_client_download_traffic(f'{uuid}@hiddify.com', reset=True)
        u = xray_client.get_client_upload_traffic(f'{uuid}@hiddify.com', reset=True)

        res = None
        if d is None:
            res = u
        elif u is None:
            res = d
        else:
            res = d + u
        if res:
            logger.debug(f"Xray usage {uuid} d={d} u={u} sum={res}")
        return res




    def get_enabled_users_terminal(self):
        import subprocess
        import json
        tags=self.get_inbound_tags()
        for t in tags:
        # Command to execute
            cmd = [
                'xray',
                'api',
                'inbounduser',
                '--server=127.0.0.1:10085',
                f'-tag={t}'
            ]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)

                # Parse JSON output
                data = json.loads(result.stdout)
                users= [splt[0] for splt in [u.get('email','').split("@") for u in data.get('users',[])] if len(splt)==2 and splt[1]=="hiddify.com"]
                if len(data)>0:
                    return users

            except subprocess.CalledProcessError as e:
                print("Command failed:", e)
                print("Error output:", e.stderr)
            except json.JSONDecodeError as e:
                print("Failed to parse JSON:", e)
        return []