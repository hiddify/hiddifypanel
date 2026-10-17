import json
import os
import time

import redis

from hiddifypanel.models import ConfigEnum, User, hconfig
from hiddifypanel.models.usage_data import UsageData
from hiddifypanel.panel.run_commander import Command, commander

from .abstract_driver import DriverABS

USERS_USAGE = "wg:users-usage"
# One usage update asks twice (who is enabled, then the usage): both take the same `wg show` instead of running it twice.
WG_USAGE_CACHE_SECONDS = 60


class WireguardApi(DriverABS):
    def get_redis_client(self):
        if not hasattr(self, "redis_client"):
            self.redis_client = redis.from_url(os.environ.get("REDIS_URI_MAIN", ""))

        return self.redis_client

    def is_enabled(self) -> bool:
        return hconfig(ConfigEnum.wireguard_enable)

    def __init__(self) -> None:
        super().__init__()
        self.pub_uuid_map = {}
        self._wg_usages_cache: tuple[float, dict] | None = None

    def __load_pubkey_uuid_map(self):
        from hiddifypanel.database import db

        users = db.session.query(User).all()
        self.pub_uuid_map = {u.wg_pub: u.uuid for u in users}

    def __convert_pub_key_to_uuid(self, pubkeys):
        res = {}
        can_reload_map = True
        for key in pubkeys:
            if uuid := self.pub_uuid_map.get(key):
                res[key] = uuid
            elif can_reload_map:
                self.__load_pubkey_uuid_map()
                can_reload_map = False
                if uuid := self.pub_uuid_map.get(key):
                    res[key] = uuid
        return res

    def __get_wg_usages(self) -> dict:
        cached = self._wg_usages_cache
        if cached and time.monotonic() - cached[0] < WG_USAGE_CACHE_SECONDS:
            return cached[1]
        data = self.__read_wg_usages()
        self._wg_usages_cache = (time.monotonic(), data)
        return data

    def __read_wg_usages(self) -> dict:
        raw_output = commander(Command.update_wg_usage, run_in_background=False)
        data = {}
        for line in raw_output.split("\n"):
            if not line:
                continue
            sections = line.split()
            if len(sections) < 3:
                continue
            # `wg show <if> transfer`: <pubkey> <received> <sent>, from the server's side
            data[sections[0]] = {
                "up": int(sections[1]),  # received by the server = the client's upload
                "down": int(sections[2]),  # sent by the server = the client's download
            }

        return data

    def __get_local_usage(self) -> dict:
        usage_data = self.get_redis_client().get(USERS_USAGE)
        if usage_data:
            return json.loads(usage_data)

        return {}

    def __sync_local_usages(self) -> dict:
        had_state = bool(self.get_redis_client().exists(USERS_USAGE))  # not the first read since redis was empty
        local_usage = self.__get_local_usage()
        wg_usage = self.__get_wg_usages()

        res = {}
        # remove local usage that is removed from wg usage
        for local_wg_pub in local_usage.copy().keys():
            if local_wg_pub not in wg_usage:
                del local_usage[local_wg_pub]

        uuid_map = self.__convert_pub_key_to_uuid(wg_usage.keys())
        for wg_pub, wg_usage in wg_usage.items():
            uuid = uuid_map.get(wg_pub)

            if not local_usage.get(wg_pub):
                if had_state and uuid:  # a peer added since the last read (a re-enabled user): its counters started at 0
                    res[uuid] = {"up": wg_usage["up"], "down": wg_usage["down"]}
                local_usage[wg_pub] = {"uuid": uuid, "usage": wg_usage}
                continue
            res[uuid] = self.calculate_reset(local_usage[wg_pub]["usage"], wg_usage)
            local_usage[wg_pub] = {"uuid": uuid, "usage": wg_usage}

        self.get_redis_client().set(USERS_USAGE, json.dumps(local_usage))

        return res

    def calculate_reset(self, last_usage: dict, current_usage: dict) -> dict:
        """Bytes since the last read; a smaller counter means the interface was recreated and counted again from 0 (as
        the telemt driver does)."""
        res = {}
        for key in ("up", "down"):
            delta = current_usage[key] - last_usage[key]
            res[key] = delta if delta >= 0 else current_usage[key]
        return res

    def get_enabled_users(self):
        if not hconfig(ConfigEnum.wireguard_enable):
            return {}
        usages = self.__get_wg_usages()
        new_wg_pubs = set(usages.keys())
        old_usages = self.__get_local_usage()
        old_wg_pubs = set(old_usages.keys())
        enabled = {u["uuid"]: 1 for u in old_usages.values()}
        not_included = new_wg_pubs - old_wg_pubs
        if not_included:
            users = User.query.filter(User.wg_pub.in_(not_included)).all()
            for u in users:
                enabled[u.uuid] = 1

        return enabled

    def add_client(self, user):
        pass

    def remove_client(self, user):
        pass

    def get_all_usage(self, reset=True) -> dict[str, UsageData]:
        if not hconfig(ConfigEnum.wireguard_enable):
            return {}
        all_usages = self.__sync_local_usages()
        res: dict[str, UsageData] = {}
        for uuid, use in all_usages.items():
            res[str(uuid)] = UsageData(
                uuid=str(uuid),
                upload=int(use.get("up") or 0),
                download=int(use.get("down") or 0),
            )
        return res
