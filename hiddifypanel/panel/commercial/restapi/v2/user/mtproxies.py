from apiflask import abort
from flask.views import MethodView

from hiddifypanel import current_app as app
from hiddifypanel import g
from hiddifypanel.auth import login_required
from hiddifypanel.models.config import hconfig
from hiddifypanel.models.config_enum import ConfigEnum
from hiddifypanel.models.child import Child
from hiddifypanel.models.domain import Domain, DomainType, FakeMode
from hiddifypanel.models.role import Role
from hiddifypanel.panel.commercial.restapi.v2.pydantic_schema import ApiModel
from hiddifypanel.panel.user.user import get_common_data
from hiddifypanel.proxy_v3.context_vars.domain import get_ips


class MtproxySchema(ApiModel):
    link: str = ""
    title: str = ""


class MTProxiesAPI(MethodView):
    decorators = [login_required({Role.user})]

    @app.output(list[MtproxySchema])
    def get(self):
        c = get_common_data(g.account.uuid, "new")

        if not c["telegram_enable"]:
            abort(status_code=404, message="Telegram mtproxy is not enable")

        dtos = []
        domains = c["domains"]
        servers = [d for d in domains if d.mode in [DomainType.direct, DomainType.relay] and d.fake_mode == FakeMode.valid]
        fronts = [d for d in domains if d.fake_mode == FakeMode.telegram]
        # Choosing domains for the sub link: if it picks some Telegram domains only those are shown, else all of them.
        picked = c["db_domain"].show_domains if c.get("db_domain") is not None else []
        picked_fronts = [d for d in fronts if d in picked]
        fronts = picked_fronts or fronts or Domain.query.filter(Domain.fake_mode == FakeMode.telegram, Domain.child_id == Child.current().id).all()

        # TODO: Remove duplicated domains mapped to a same ipv4 and v6
        if not fronts:  # no Telegram domain row yet: the old behaviour, the setting's fake domain on every server domain
            for d in servers:
                dtos.append(_dto(d.alias or d.domain, d.domain, d.child_id, hconfig(ConfigEnum.telegram_fakedomain, d.child_id)))
            return dtos

        for front in fronts:
            node_servers = [d for d in servers if d.child_id == front.child_id]
            for d in node_servers:
                dtos.append(_dto(d.alias or d.domain, d.domain, front.child_id, front.domain))
            ips = get_ips(front)
            for ip in sorted(ips.ipsv4):
                dtos.append(_dto(f"{front.alias or front.domain} IPv4", ip, front.child_id, front.domain))
            for ip in sorted(ips.ipsv6):
                dtos.append(_dto(f"{front.alias or front.domain} IPv6", ip, front.child_id, front.domain))
        return dtos


def _dto(title: str, server: str, child_id: int, fake_domain: str) -> MtproxySchema:
    raw_sec = hconfig(ConfigEnum.shared_secret, child_id)
    if hconfig(ConfigEnum.telegram_lib) == "telemt":
        raw_sec = g.account.uuid
    secret_hex = str(raw_sec).replace("-", "")
    fake_domain_hex = str(fake_domain or "").encode("utf-8").hex()
    dto = MtproxySchema()
    dto.title = title
    dto.link = f"tg://proxy?server={server}&port=443&secret=ee{secret_hex}{fake_domain_hex}"
    return dto
