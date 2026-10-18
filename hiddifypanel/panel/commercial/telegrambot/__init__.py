"""Hiddify's Telegram bot: one tidy message per chat that buttons edit in place.

Admins (linked with ``/start admin_<uuid>`` from the panel) manage users, see a pocket dashboard, take backups
and open the panel as a Mini App. Users (linked with ``/start <uuid>``) see their account, links and QR code.
"""

from hiddifypanel.panel.commercial.restapi.v1 import bot, register_bot, register_bot_cached

from . import handlers  # noqa: E402,F401  (registers the handlers)
from . import Usage  # noqa: E402,F401  (kept for broadcast / tgmsg / usage)
