"""The admin's inbox: the people who wrote to the Telegram bot (or asked for the free test), their messages, the
answers, and the admin's free test package and link (see ``hiddifypanel.free_test``).

An admin sees its own conversations only: they are between that admin and its customers.
"""

from __future__ import annotations

from typing import Any

from apiflask import abort
from flask import request
from flask.views import MethodView

from hiddifypanel import free_test, g, hutils
from hiddifypanel.auth import login_required
from hiddifypanel.database import db
from hiddifypanel.free_test import FreeTestError
from hiddifypanel.models import ConfigEnum, Role, User, hconfig
from hiddifypanel.models.message import Conversation, FreeStatus, Message

ROLES = {Role.super_admin, Role.admin, Role.agent}
MAX_CONVERSATIONS = 500
MAX_MESSAGES = 300


def _bot_username() -> str:
    from hiddifypanel.panel.commercial.restapi.v1.tgbot import bot

    return str(bot.username or "") if hconfig(ConfigEnum.telegram_bot_token) and bot else ""


def _conversation_out(conv: Conversation, accounts: dict[str, User]) -> dict[str, Any]:
    account = accounts.get(conv.user_uuid or "")
    return {
        "id": conv.id,
        "name": conv.name,
        "username": conv.username or "",
        "account": {"uuid": account.uuid, "name": account.name, "active": bool(account.is_active)} if account else None,
        "free_status": conv.free_status,
        #: The admin's package this chat asked for or got; null: not yet (it goes with the default one).
        "package_id": conv.free_package_id,
        "free_grants": conv.free_grants or 0,
        #: Never had a free test or an account on this panel.
        "first_time": free_test.is_first_time(conv) if conv.free_status == FreeStatus.pending else False,
        "unread": conv.unread or 0,
        "last_text": conv.last_text,
        "last_sender": conv.last_sender,
        "last_at": conv.last_at.isoformat() if conv.last_at else None,
    }


def _accounts_of(conversations: list[Conversation]) -> dict[str, User]:
    uuids = [c.user_uuid for c in conversations if c.user_uuid]
    return {u.uuid: u for u in User.query.filter(User.uuid.in_(uuids), User.deleted.is_(False)).all()} if uuids else {}


def _message_out(message: Message) -> dict[str, Any]:
    return {"id": message.id, "sender": message.sender, "kind": message.kind, "text": message.text, "at": message.created_at.isoformat()}


def _free_out() -> dict[str, Any]:
    admin = g.account
    package = free_test.package_of(admin)
    username = _bot_username()
    payload = free_test.start_payload(admin)
    inherited = package.owner is not None and package.owner.id != admin.id
    own = free_test.own_set(admin)
    return {
        #: The package offered in the bot: the default one.
        "package": package.to_dict(),
        #: The admin's own default package (null: it uses its parent's).
        "own": package.to_dict() if own is not None else None,
        #: All of the admin's own packages, the default one included; only the default one is offered.
        "packages": own["packages"] if own is not None else [],
        "default_id": own["default"] if own is not None else None,
        "max_packages": free_test.MAX_PACKAGES,
        "can_edit": free_test.can_define(admin) and not hutils.node.is_child(),
        "inherited_from": package.owner.name if inherited and package.owner else None,
        "link": f"https://t.me/{username}?start={payload}" if username else None,
        "app_link": f"tg://resolve?domain={username}&start={payload}" if username else None,
        "has_room": admin.can_have_more_users(),
        "limits": {"max_days": free_test.MAX_DAYS, "max_usage_gb": free_test.MAX_USAGE_GB, "min_usage_gb": free_test.MIN_USAGE_GB},
    }


def _mine(conversation_id: int) -> Conversation:
    conv = db.session.get(Conversation, conversation_id)
    if conv is None or conv.admin_id != g.account.id:
        abort(404, "Conversation not found")
    return conv


def _thread_out(conv: Conversation) -> dict[str, Any]:
    messages = Message.query.filter(Message.conversation_id == conv.id).order_by(Message.id.desc()).limit(MAX_MESSAGES).all()
    return {"conversation": _conversation_out(conv, _accounts_of([conv])), "messages": [_message_out(m) for m in reversed(messages)]}


class InboxApi(MethodView):
    decorators = [login_required(ROLES)]

    def get(self):
        """Inbox: the bot, this admin's free test package and link, and its conversations (newest first)"""
        conversations = Conversation.query.filter(Conversation.admin_id == g.account.id).order_by(Conversation.last_at.desc()).limit(MAX_CONVERSATIONS).all()
        accounts = _accounts_of(conversations)
        return {
            "bot_username": _bot_username(),
            "free": _free_out(),
            "conversations": [_conversation_out(c, accounts) for c in conversations],
            **free_test.counts(g.account),
        }


class InboxCountsApi(MethodView):
    decorators = [login_required(ROLES)]

    def get(self):
        """Inbox: conversations with unread messages and free test requests waiting (the menu badge)"""
        return free_test.counts(g.account)


class FreePackageApi(MethodView):
    decorators = [login_required(ROLES)]

    def put(self):
        """Free test: set this admin's packages (``{"packages": [...], "default": id}``; ``{"inherit": true}`` goes back to the parent's)"""
        if not free_test.can_define(g.account):
            abort(403, "Missing capability: modify_free_package")
        if hutils.node.is_child():
            abort(400, "Managed on the parent panel")
        body = request.get_json(silent=True) or {}
        free_test.set_package(g.account, None if body.get("inherit") else body)
        db.session.commit()
        return _free_out()


class ConversationApi(MethodView):
    decorators = [login_required(ROLES)]

    def get(self, conversation_id: int):
        """Inbox: one conversation and its messages; opening it marks it read"""
        conv = _mine(conversation_id)
        if conv.unread:
            conv.unread = 0
            db.session.commit()
        return _thread_out(conv)

    def post(self, conversation_id: int):
        """Inbox: send a message to the person over the Telegram bot"""
        conv = _mine(conversation_id)
        text = str((request.get_json(silent=True) or {}).get("text", "")).strip()
        if not text:
            abort(400, "The message is empty")
        if len(text) > free_test.MAX_TEXT:
            abort(400, "The message is too long")
        if not _bot_username():
            abort(400, "The Telegram bot is not set up")
        from hiddifypanel.panel.commercial.telegrambot import free

        try:
            free.deliver(conv, text)
        except Exception as e:
            db.session.rollback()
            abort(400, f"Telegram did not deliver the message: {e}")
        return _thread_out(conv)

    def delete(self, conversation_id: int):
        """Inbox: delete a conversation and its messages (the person's account stays)"""
        conv = _mine(conversation_id)
        if conv.free_grants:
            # The record that this chat had its free test must outlive the messages.
            Message.query.filter(Message.conversation_id == conv.id).delete(synchronize_session=False)
            conv.last_text, conv.unread = "", 0
            if conv.free_status == FreeStatus.pending:
                conv.free_status = FreeStatus.declined.value
        else:
            db.session.delete(conv)
        db.session.commit()
        return {"ok": True}


class FreeAnswerApi(MethodView):
    decorators = [login_required(ROLES)]

    def post(self, conversation_id: int):
        """Free test: ``approve`` or ``decline`` a waiting request, or ``grant`` one without a request (another free
        test for someone who already had one)"""
        conv = _mine(conversation_id)
        action = str((request.get_json(silent=True) or {}).get("action", ""))
        from hiddifypanel.panel.commercial.telegrambot import free

        try:
            if action in ("approve", "grant"):
                if action == "approve" and conv.free_status != FreeStatus.pending:
                    raise FreeTestError("not_pending")
                account = free_test.grant(conv)
                free.send_account(conv, account)
            elif action == "decline":
                free_test.decline(conv)
                free.tell_declined(conv)
            else:
                abort(400, "Unknown action")
        except FreeTestError as e:
            db.session.rollback()
            abort(400, e.code)
        return _thread_out(conv)
