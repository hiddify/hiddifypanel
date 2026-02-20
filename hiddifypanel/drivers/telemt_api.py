import json
import os
import re

import requests

from .abstract_driver import DriverABS
from hiddifypanel.models import User, hconfig, ConfigEnum
from hiddifypanel.panel.run_commander import Command, commander
import redis


USERS_USAGE = "tele:users-usage"


class TelemtApi(DriverABS):
    def get_redis_client(self):
        if not hasattr(self, 'redis_client'):
            self.redis_client = redis.from_url(os.environ.get("REDIS_URI_SSH",""))

        return self.redis_client

    def is_enabled(self) -> bool:
        return hconfig(ConfigEnum.telegram_enable) and hconfig(ConfigEnum.telegram_lib)=="telemt"

    def __init__(self) -> None:
        super().__init__()
        self.tg_uuid_map:dict[str,str]={}

    def __load_tg_uuid_map(self):
        from hiddifypanel.database import db
        users = db.session.query(User).all()
        self.tg_uuid_map={u.uuid.replace("-",""): u.uuid for u in users}

    def __convert_tg_to_uuid(self,pubkeys):
        res={}
        can_reload_map=True
        for key in pubkeys:
            if uuid:=self.tg_uuid_map.get(key):
                res[key]=uuid
            elif can_reload_map:
                self.__load_tg_uuid_map()
                can_reload_map=False
                if uuid:=self.tg_uuid_map.get(key):
                    res[key]=uuid
        return res
    def get_metric(self):
        resp = requests.get("http://localhost:10087/metrics", timeout=5)
        resp.raise_for_status()
        return resp.text

    def __get_tg_usages(self) -> dict:
        raw_output = self.get_metric()
        data = {}

        # Example lines:
        # telemt_user_octets_from_client{user="uuid"} 1983
        # telemt_user_octets_to_client{user="uuid"} 2171

        pattern = re.compile(
            r'telemt_user_octets_(from_client|to_client)\{user="([^"]+)"\}\s+(\d+)'
        )

        for line in raw_output.splitlines():
            match = pattern.search(line)
            if not match:
                continue

            direction, user, value = match.groups()
            value = int(value)

            if user not in data:
                data[user] = {"down": 0, "up": 0}

            if direction == "from_client":
                data[user]["up"] = value
            else:  # to_client
                data[user]["down"] = value

        return data

    def __get_local_usage(self) -> dict:
        usage_data = self.get_redis_client() .get(USERS_USAGE)
        if usage_data:
            return json.loads(usage_data)

        return {}

    def __sync_local_usages(self) -> dict:
        local_usage = self.__get_local_usage()
        tg_usage = self.__get_tg_usages()
        
        res = {}
        # remove local usage that is removed from wg usage
        for local_uuid in local_usage.copy().keys():
            if local_uuid not in tg_usage:
                del local_usage[local_uuid]

        
        uuid_map = self.__convert_tg_to_uuid(tg_usage.keys())
        for tg_uuid, tg_usage in tg_usage.items():
            uuid = uuid_map.get(tg_uuid)
            
            if not local_usage.get(tg_uuid):
                local_usage[tg_uuid] = {"uuid": uuid, "usage": tg_usage}
                continue
            res[uuid] = self.calculate_reset(local_usage[tg_uuid]['usage'], tg_usage)
            local_usage[tg_uuid] = {"uuid": uuid, "usage": tg_usage}

        self.get_redis_client().set(USERS_USAGE, json.dumps(local_usage))

        return res

    def calculate_reset(self, last_usage: dict, current_usage: dict) -> dict:
        res = {
            'up': current_usage['up'] - last_usage['up'],
            'down': current_usage['down'] - last_usage['down'],
        }

        if res['up'] < 0:
            res['up'] = 0
        if res['down'] < 0:
            res['down'] = 0
        return res

    def get_enabled_users(self):
        if not self.is_enabled():
            return {}
        usages = self.__get_tg_usages()
        new_wg_pubs = set(usages.keys())
        old_usages = self.__get_local_usage()
        old_wg_pubs = set(old_usages.keys())
        enabled = {u['uuid']: 1 for u in old_usages.values()}
        not_included = new_wg_pubs - old_wg_pubs
        if not_included:
            users = User.query.filter(User.wg_pub.in_(not_included).all())
            for u in users:
                enabled[u.uuid] = 1

        return enabled

    def add_client(self, user):
        pass

    def remove_client(self, user):
        pass

    def get_all_usage(self, reset=True):
        if not self.is_enabled():
            return {}
        all_usages = self.__sync_local_usages()
        res = {}
        for uuid,use in all_usages.items():
            # if use := all_usages.get(u.wg_pub):
                res[uuid] = use['up'] + use['down']
            # else:
            #     res[u] = 0
        return res
