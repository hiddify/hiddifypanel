"""What the bot knows about users: their state, links, the list filters, and changes made the same way the
Admin V2 users page makes them (drivers, apply, nodes)."""

from __future__ import annotations

import datetime
import uuid as uuid_lib
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import or_

from hiddifypanel import hutils
from hiddifypanel.database import db
from hiddifypanel.drivers import user_driver
from hiddifypanel.models import AdminUser, ConfigEnum, Domain, User, hconfig
from hiddifypanel.panel import hiddify

MAX_PACKAGE_DAYS = 10000
MAX_USAGE_GB = 1_000_000
ONLINE_WINDOW = datetime.timedelta(minutes=5)
SOON_DAYS = 7
LOW_DATA_RATIO = 0.8


class Status(StrEnum):
    active = "active"
    disabled = "disabled"
    expired = "expired"
    no_data = "no_data"


STATUS_ICON: dict[Status, str] = {Status.active: "🟢", Status.disabled: "⚪️", Status.expired: "🔴", Status.no_data: "🟠"}


def status(user: User) -> Status:
    """Same order as the users page: disabled > expired > out of data > active."""
    if not user.enable:
        return Status.disabled
    if user.remaining_days < 0:
        return Status.expired
    if (user.usage_limit or 0) < (user.current_usage or 0):
        return Status.no_data
    return Status.active


def usage_ratio(user: User) -> float:
    limit = user.usage_limit or 0
    return (user.current_usage or 0) / limit if limit else 1.0


def is_online(user: User) -> bool:
    return bool(user.last_online) and datetime.datetime.now() - user.last_online <= ONLINE_WINDOW


def is_expiring(user: User) -> bool:
    if status(user) is not Status.active:
        return False
    return (user.start_date is not None and user.remaining_days <= SOON_DAYS) or usage_ratio(user) >= LOW_DATA_RATIO


class Filter(StrEnum):
    all = "a"
    active = "c"
    expiring = "s"
    ended = "e"
    online = "o"


def matches(user: User, f: Filter) -> bool:
    match f:
        case Filter.all:
            return True
        case Filter.active:
            return status(user) is Status.active
        case Filter.expiring:
            return is_expiring(user)
        case Filter.ended:
            return status(user) in (Status.expired, Status.no_data)
        case Filter.online:
            return is_online(user)


@dataclass(frozen=True, slots=True)
class Page:
    users: list[User]
    total: int
    #: The page shown (asked pages past the end show the last one) and how many there are, at least 1.
    page: int
    pages: int


def _pages(total: int, page: int, size: int) -> tuple[int, int]:
    pages = max((total + size - 1) // size, 1)
    return min(max(page, 0), pages - 1), pages


def _sql_page(query, page: int, size: int) -> Page:
    """One page of ``query`` from the database (the newest first), without loading the rest."""
    total = query.order_by(None).count()
    page, pages = _pages(total, page, size)
    return Page(query.order_by(User.id.desc()).offset(page * size).limit(size).all(), total, page, pages)


def users_page(admin: AdminUser, f: Filter, page: int, size: int) -> Page:
    """The users under ``admin`` that ``f`` keeps, one page of them. "All" and "online" are counted and cut in the
    database; the others depend on the package (days left, data used), the same rule as ``status``, so only the
    switched-on accounts (the only ones they can keep) are read and checked here."""
    query = admin.recursive_users_query()
    if f is Filter.all:
        return _sql_page(query, page, size)
    if f is Filter.online:
        return _sql_page(query.filter(User.last_online >= datetime.datetime.now() - ONLINE_WINDOW), page, size)
    kept = [u for u in query.filter(User.enable.is_(True)).order_by(User.id.desc()).all() if matches(u, f)]
    page, pages = _pages(len(kept), page, size)
    return Page(kept[page * size : (page + 1) * size], len(kept), page, pages)


class Sort(StrEnum):
    """How a users list is ordered (the list's ↕️ button goes round them)."""

    new = "n"
    usage = "u"
    days = "d"
    seen = "l"
    name = "m"


def _sort_key(sort: Sort):
    match sort:
        case Sort.usage:  # the fullest first
            return lambda u: -usage_ratio(u)
        case Sort.days:  # the fewest days left first; not started and ended at the end
            return lambda u: (status(u) is not Status.active, u.remaining_days if u.start_date else 10**6)
        case Sort.seen:  # the last to connect first
            return lambda u: -u.last_online.timestamp() if u.last_online and u.last_online.year > 1970 else float("inf")
        case Sort.name:
            return lambda u: (u.name or "").casefold()
    return lambda u: -u.id


def list_page(admin: AdminUser, f: Filter, sort: Sort, page: int, size: int) -> Page:
    """``users_page`` in the order asked for. The newest first is cut in the database; any other order needs every
    user the filter keeps, read once and sorted here."""
    if sort is Sort.new:
        return users_page(admin, f, page, size)
    query = admin.recursive_users_query()
    if f is Filter.online:
        query = query.filter(User.last_online >= datetime.datetime.now() - ONLINE_WINDOW)
    elif f is not Filter.all:
        query = query.filter(User.enable.is_(True))
    kept = sorted((u for u in query.all() if matches(u, f)), key=_sort_key(sort))
    page, pages = _pages(len(kept), page, size)
    return Page(kept[page * size : (page + 1) * size], len(kept), page, pages)


def counts(admin: AdminUser) -> dict[Filter, int]:
    """How many users each filter keeps (the list's tabs): all and online from the database, the rest over the
    switched-on accounts only."""
    query = admin.recursive_users_query()
    enabled = query.filter(User.enable.is_(True)).all()
    return {
        Filter.all: query.order_by(None).count(),
        Filter.active: sum(status(u) is Status.active for u in enabled),
        Filter.expiring: sum(is_expiring(u) for u in enabled),
        Filter.ended: sum(status(u) in (Status.expired, Status.no_data) for u in enabled),
        Filter.online: query.filter(User.last_online >= datetime.datetime.now() - ONLINE_WINDOW).order_by(None).count(),
    }


def _search_query(admin: AdminUser, text: str):
    q = text.strip()
    if not q:
        return None
    match = or_(User.name.icontains(q, autoescape=True), User.uuid.icontains(q, autoescape=True), User.comment.icontains(q, autoescape=True))
    if q.isdigit():
        match = or_(match, User.telegram_id == int(q))
    return admin.recursive_users_query().filter(match)


def search_page(admin: AdminUser, text: str, page: int, size: int) -> Page:
    """Users under ``admin`` whose name, uuid or comment holds ``text`` (any case), or whose Telegram id it is."""
    query = _search_query(admin, text)
    return _sql_page(query, page, size) if query is not None else Page([], 0, 0, 1)


@dataclass(frozen=True, slots=True)
class Summary:
    total: int
    active: int
    online: int
    expiring: int


def summary(admin: AdminUser) -> Summary:
    """The admin home's counts: the total and the online ones from the database, the rest over the switched-on
    accounts only."""
    query = admin.recursive_users_query()
    total = query.order_by(None).count()
    online = query.filter(User.last_online >= datetime.datetime.now() - ONLINE_WINDOW).order_by(None).count()
    enabled = query.filter(User.enable.is_(True)).all()
    return Summary(total, sum(status(u) is Status.active for u in enabled), online, sum(is_expiring(u) for u in enabled))


def get_visible(admin: AdminUser, user_id: int) -> User | None:
    user = User.query.filter(User.id == user_id, User.deleted.is_(False)).first()
    return user if user and user.added_by in admin.recursive_sub_admins_ids() else None


# --------------------------------------------------------------------------- links


@dataclass(frozen=True, slots=True)
class Links:
    home: str  # the user page, bare: Mini App buttons open it (Telegram puts its own data after "#")
    page: str  # the user page as the panel gives it: ends with "#<name>", so apps name the profile
    sub: str
    hiddify: str


def user_host() -> str:
    """The domain users' links use: the first real domain name (sub-link domains first, as the panel orders
    them); an IP only when the panel has no name at all."""
    from .ui import is_domain_name

    candidates = [d.domain for d in Domain.get_domains()] + [Domain.get_panel_link() or ""]
    candidates = [c for c in candidates if c]
    return next((c for c in candidates if is_domain_name(c)), candidates[0] if candidates else "")


def links(user: User) -> Links:
    host = user_host()
    home = hiddify.get_account_panel_link(user, host)
    # The same links the panel gives (users list, user page): "#<name>" names the profile in the apps, and the
    # subscription is sub/ (auto/ answered browsers with the user page, not the subscription)
    name = hutils.encode.url_encode(user.name or "Hiddify")
    return Links(home=home, page=f"{home}#{name}", sub=f"{home}sub/?asn=unknown#{name}", hiddify=f"hiddify://import/{home}#{name}")


def panel_app_url() -> str | None:
    """The Mini App entry: logs the admin in from Telegram's signed data, then opens Admin V2."""
    from hiddifypanel.panel.commercial.restapi.v1.tgbot import panel_domain_name

    domain = panel_domain_name() or user_host()
    if not domain:
        return None
    return f"https://{domain}/{hconfig(ConfigEnum.proxy_path_admin)}/api/v1/tgbot/app/"


# --------------------------------------------------------------------------- changes


def apply(users: list[User]) -> None:
    """After a commit: push the users to the cores, regenerate configs, tell the nodes."""
    for user in users:
        if user.is_active:
            user_driver.add_client(user)
        else:
            user_driver.remove_client(user)
    hutils.apply_users.quick_apply_users(users_only=True)
    hutils.node.parent.notify_childs_users_changed()


def renew(user: User) -> None:
    """A fresh package: days count again from the next connection and usage is zero."""
    user.start_date = None
    user.reset_usage()
    user.enable = True


def add_days(user: User, days: int) -> None:
    user.package_days = min((user.package_days or 0) + days, MAX_PACKAGE_DAYS)


def add_gb(user: User, gb: int) -> None:
    user.usage_limit_GB = min(user.usage_limit_GB + gb, MAX_USAGE_GB)


def remove(user: User) -> None:
    user.remove(commit=False)
    db.session.commit()
    hutils.apply_users.quick_apply_users(users_only=True)
    hutils.node.parent.notify_childs_users_changed()


def create(admin: AdminUser, *, gb: int, days: int, count: int, name: str) -> list[User]:
    users = []
    for i in range(1, count + 1):
        user = User(
            uuid=str(uuid_lib.uuid4()),
            name=name if count == 1 else f"{name}-{i:0{max(2, len(str(count)))}d}",
            package_days=days,
            added_by=admin.id,
            enable=True,
        )
        user.usage_limit_GB = gb
        db.session.add(user)
        users.append(user)
    db.session.commit()
    apply(users)
    return users


def is_read_only() -> bool:
    return hutils.node.is_child()
