"""apply_users.sh (the configs that change with the users, then a reload), asked by the panel when users change.

The first change runs right away; changes during a run or within ``INTERVAL`` seconds of its start go
in one more run. The panel's workers share the queue in redis, so 10 users added at once give 2 runs, not 10.
"""

from __future__ import annotations

import os
import threading
import time

from loguru import logger

from hiddifypanel.panel.run_commander import Command, commander

#: It runs at most once per this many seconds: users added together (10 at once, a bulk add) are applied in one run.
INTERVAL = 15
#: Shared by the panel's workers (redis): the changes not applied yet, when the last run started, and which worker runs them.
_PENDING = "apply-users:pending"  # hash: requested, domain, full (a change that is not users only)
_LAST_START = "apply-users:last-start"
_RUNNER = "apply-users:runner"
#: The runner's claim, renewed while it works: a worker that stops (a panel restart) leaves it within a minute.
_RUNNER_TTL = 60


def _redis():
    from hiddifypanel.cache import redis_client  # not at import: hutils is loaded before the app's environment

    return redis_client


def _take_pending() -> dict[str, bool] | None:
    pipe = _redis().pipeline()
    pipe.hgetall(_PENDING)
    pipe.delete(_PENDING)
    raw = pipe.execute()[0]
    if not raw:
        return None
    flags = {k.decode() if isinstance(k, bytes) else k: (v in (b"1", "1")) for k, v in raw.items()}
    return {"domain": flags.get("domain", False), "users_only": not flags.get("full", False)}


def _run(domain: bool, users_only: bool) -> None:
    try:
        commander(Command.apply_users, run_in_background=False, domain=int(domain), users_only=int(users_only))
    except Exception as e:
        logger.exception(f"apply users failed: {e}")


def _worker():
    """The one runner of all workers: runs the pending changes, at most once per INTERVAL seconds."""
    r = _redis()
    stop = threading.Event()

    def keep_claim():
        while not stop.wait(_RUNNER_TTL / 3):
            r.expire(_RUNNER, _RUNNER_TTL)

    threading.Thread(target=keep_claim, daemon=True).start()
    try:
        _loop(r)
    finally:
        stop.set()


def _loop(r) -> None:
    while True:
        last = float(r.get(_LAST_START) or 0)
        wait = last + INTERVAL - time.time()
        if wait > 0:
            time.sleep(wait)  # changes coming in meanwhile go in this same run
        pending = _take_pending()
        if pending is None:
            r.delete(_RUNNER)
            # a change asked just before the claim was released found it taken: take it back and run it
            if not r.exists(_PENDING) or not r.set(_RUNNER, os.getpid(), nx=True, ex=_RUNNER_TTL):
                return
            continue
        r.set(_LAST_START, time.time())
        _run(**pending)


def quick_apply_users(domain: bool = False, users_only: bool = False):
    """Run apply_users.sh soon: right away when it did not run in the last INTERVAL seconds, otherwise once
    that time is over, with every change asked meanwhile (by any of the panel's workers) in one run.
    domain: domains changed, so services that cannot hot-reload them (telemt) restart.
    users_only: only users changed and user_driver already gave them to the cores' APIs: xray is not reloaded."""
    try:
        r = _redis()
        pipe = r.pipeline()
        pipe.hset(_PENDING, "requested", 1)
        if domain:
            pipe.hset(_PENDING, "domain", 1)
        if not users_only:
            pipe.hset(_PENDING, "full", 1)
        pipe.execute()
        if not r.set(_RUNNER, os.getpid(), nx=True, ex=_RUNNER_TTL):
            logger.info("apply users: queued for the running apply")
            return {"status": "queued"}
        target, args = _worker, ()
    except Exception as e:  # no redis: this change on its own (the commander still waits for a running one)
        logger.warning(f"apply users: redis unavailable ({e}), running it directly")
        target, args = _run, (domain, users_only)
    threading.Thread(target=target, args=args, daemon=True).start()
    return {"status": "success"}
