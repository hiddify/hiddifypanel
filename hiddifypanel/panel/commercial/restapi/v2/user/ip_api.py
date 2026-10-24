from flask.views import MethodView

from hiddifypanel import current_app as app
from hiddifypanel.auth import login_required
from hiddifypanel.hutils.network.auto_ip_selector import get_real_user_ip
from hiddifypanel.hutils.network.ip_lookup import lookup
from hiddifypanel.models.role import Role
from hiddifypanel.panel.commercial.restapi.v2.pydantic_schema import ApiModel


class IpLookupSchema(ApiModel):
    """Where the caller's connection reaches this panel from. Not a lookup of an arbitrary address."""

    ip: str = ""
    city: str = ""
    region: str = ""
    region_code: str = ""
    country_name: str = ""
    country_code: str = ""
    continent_code: str = ""
    latitude: float | None = None
    longitude: float | None = None
    timezone: str = ""
    utc_offset: str = ""
    currency: str = ""
    currency_name: str = ""
    languages: str = ""
    asn: str = ""
    org: str = ""


class IpAPI(MethodView):
    decorators = [login_required({Role.user})]

    @app.output(IpLookupSchema)
    def get(self):
        return IpLookupSchema(**lookup(get_real_user_ip()))
