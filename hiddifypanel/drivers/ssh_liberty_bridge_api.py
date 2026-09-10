import os

import redis
from loguru import logger

from hiddifypanel.models import ConfigEnum, hconfig
from hiddifypanel.models.usage_data import UsageData

from .abstract_driver import DriverABS

USERS_SET = "ssh-server:users"
USERS_USAGE = "ssh-server:users-usage"


class SSHLibertyBridgeApi(DriverABS):
    def is_enabled(self) -> bool:
        return hconfig(ConfigEnum.ssh_server_enable)

    def get_ssh_redis_client(self):
        if not hasattr(self, "redis_client"):
            self.redis_client = redis.from_url(os.environ.get("REDIS_URI_MAIN", ""), decode_responses=True)

        return self.redis_client

    def get_enabled_users(self):
        redis_client = self.get_ssh_redis_client()
        members = redis_client.smembers(USERS_SET)
        return {m.split("::")[0]: 1 for m in members}

    def add_client(self, user):
        print(f"Adding SSH {user}")
        redis_client = self.get_ssh_redis_client()
        redis_client.sadd(USERS_SET, f"{user.uuid}::{user.ed25519_public_key}")
        redis_client.save()

    def remove_client(self, user):
        redis_client = self.get_ssh_redis_client()
        if user.ed25519_public_key is None:
            members = redis_client.smembers(USERS_SET)
            for member in members:
                if member.startswith(user.uuid):
                    redis_client.srem(USERS_SET, member)

        redis_client.srem(USERS_SET, f"{user.uuid}::{user.ed25519_public_key}")
        redis_client.hdel(USERS_USAGE, f"{user.uuid}")
        redis_client.save()

    def get_all_usage(self) -> dict[str, UsageData]:
        redis_client = self.get_ssh_redis_client()
        allusage = redis_client.hgetall(USERS_USAGE) or {}
        redis_client.delete(USERS_USAGE)
        res: dict[str, UsageData] = {}
        for uuid, value in allusage.items():
            # SSH bridge only reports total bytes — treat as download.
            try:
                total = max(0, int(value or 0))
            except (TypeError, ValueError):
                total = 0
            if total:
                res[str(uuid)] = UsageData(uuid=str(uuid), upload=0, download=total)
        return res

    def get_usage_imp(self, client_uuid: str, reset: bool = True) -> UsageData:
        redis_client = self.get_ssh_redis_client()
        value = redis_client.hget(USERS_USAGE, client_uuid)

        try:
            total = max(0, int(value or 0))
        except (TypeError, ValueError):
            total = 0

        if reset and total:
            redis_client.hincrby(USERS_USAGE, client_uuid, -total)
            redis_client.save()
        row = UsageData(uuid=str(client_uuid), upload=0, download=total)
        if row.usage:
            logger.debug(f"ssh usage {client_uuid} {row.usage}")
        return row
