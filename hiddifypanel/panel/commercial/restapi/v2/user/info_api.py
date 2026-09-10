from flask import request
from flask.views import MethodView
from flask_babel import gettext as _

from hiddifypanel import auth, g, hutils
from hiddifypanel import current_app as app
from hiddifypanel.auth import login_required
from hiddifypanel.database import db
from hiddifypanel.models import Lang
from hiddifypanel.models.config import hconfig
from hiddifypanel.models.config_enum import ConfigEnum
from hiddifypanel.models.role import Role
from hiddifypanel.models.user import User
from hiddifypanel.panel.commercial.restapi.v2.pydantic_schema import ApiModel
from hiddifypanel.panel.user.user import get_common_data


class ProfileSchema(ApiModel):
    profile_title: str = ""
    profile_url: str = ""
    profile_usage_current: float = 0
    profile_usage_total: float = 0
    profile_remaining_days: int = 0
    profile_reset_days: int | None = None
    telegram_bot_url: str = ""
    telegram_id: int | None = None
    admin_message_html: str = ""
    admin_message_url: str = ""
    brand_title: str = ""
    brand_icon_url: str = ""
    doh: str = ""
    lang: Lang = Lang.en
    speedtest_enable: bool = False
    telegram_proxy_enable: bool = False


class UserInfoChangableSchema(ApiModel):
    language: Lang | None = None
    telegram_id: int | None = None


class InfoAPI(MethodView):
    decorators = [login_required({Role.user})]

    @app.output(ProfileSchema)
    def get(self):
        c = get_common_data(g.account.uuid, 'new')

        dto = ProfileSchema()
        # user is exist for sure
        dto.profile_title = c['user'].name
        dto.profile_url = f"{c['profile_url']}#{hutils.encode.url_encode(c['user'].name)}"
        dto.profile_usage_current = g.account.current_usage_GB
        dto.profile_usage_total = g.account.usage_limit_GB
        dto.profile_remaining_days = g.account.remaining_days
        dto.profile_reset_days = g.account.days_to_reset()
        dto.telegram_bot_url = f"https://t.me/{c['bot'].username}?start={g.account.uuid}" if c['bot'] else ""
        dto.telegram_id = c['user'].telegram_id

        dto.doh = f"https://{request.host}/{g.proxy_path}/dns/dns-query"
        dto.lang = (c['user'].lang) or Lang(hconfig(ConfigEnum.lang))
        dto.brand_icon_url = "" if hconfig(ConfigEnum.branding_title) else hutils.flask.static_url_for(filename="images/favicon.ico")
        # with force_locale("fa"):
        dto.admin_message_html = hconfig(ConfigEnum.branding_freetext) or _("Join our Hiddify Telegram channel to get the latest updates on Hiddify.")
        if not hconfig(ConfigEnum.branding_freetext) and auth.admin_session_is_exist():
            dto.admin_message_html += "<p style='font-style: italic;font-size:8px'>" + \
                _("[Admin only visible message:] You can change this message from settings") + "</p>"
        dto.admin_message_url = hconfig(ConfigEnum.branding_site) or "https://t.me/hiddify"
        dto.brand_title = hconfig(ConfigEnum.branding_title) or _("Hiddify")

        dto.speedtest_enable = hconfig(ConfigEnum.speed_test)
        dto.telegram_proxy_enable = c.get('telegram_enable', False)
        return dto

    @app.input(UserInfoChangableSchema, arg_name='data')
    def patch(self, data: UserInfoChangableSchema):
        if data.telegram_id:
            user = User.by_uuid(g.account.uuid)
            if user.telegram_id != data.telegram_id:
                user.telegram_id = data.telegram_id
                db.session.commit()

        if data.language:
            user = User.by_uuid(g.account.uuid)
            if user.lang != data.language:
                user.lang = data.language
                db.session.commit()
        return {'message': 'ok'}
