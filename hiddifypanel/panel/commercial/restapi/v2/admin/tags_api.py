"""Tags API of the new dashboard: the shared tag list and the tags on users and admins.

The default tags (family, friends, work, important, free) always exist. Every admin can add tags and put
tags on the users it can see; changing a tag's name or color, or deleting a custom tag, needs a super admin.
"""

from __future__ import annotations

import re
from typing import Any

from apiflask import abort
from flask import request
from flask.views import MethodView

from hiddifypanel import g
from hiddifypanel.auth import login_required
from hiddifypanel.database import db
from hiddifypanel.models import AdminUser, User
from hiddifypanel.models.role import Role
from hiddifypanel.models.tag import COLORS, KINDS, MAX_TAGS, Tag, TagLink, set_tags, tags_of

ALL_ROLES = {Role.super_admin, Role.admin, Role.agent}


def _tag_out(tag: Tag, counts: dict[int, int]) -> dict[str, Any]:
    return {"id": tag.id, "name": tag.name, "color": tag.color, "is_default": bool(tag.is_default), "count": counts.get(tag.id, 0)}


def _list_out() -> dict[str, Any]:
    Tag.seed_defaults()
    db.session.commit()
    counts: dict[int, int] = {}
    for (tag_id,) in db.session.query(TagLink.tag_id).all():
        counts[tag_id] = counts.get(tag_id, 0) + 1
    return {"tags": [_tag_out(t, counts) for t in Tag.ordered()], "colors": list(COLORS)}


def _clean(body: dict[str, Any], tag: Tag | None) -> tuple[str, str]:
    name = re.sub(r"\s+", " ", str(body.get("name", tag.name if tag else "")).strip())[:60]
    color = str(body.get("color", tag.color if tag else "blue"))
    if not name:
        abort(400, "Name is required")
    if color not in COLORS:
        abort(400, "Unknown color")
    if Tag.query.filter(db.func.lower(Tag.name) == name.lower(), Tag.id != (tag.id if tag else 0)).first():
        abort(400, "A tag with this name exists")
    return name, color


class TagsApi(MethodView):
    decorators = [login_required(ALL_ROLES)]

    def get(self):
        """Tags: the shared list (defaults first, then custom ones) with how many accounts use each"""
        return _list_out()

    def post(self):
        """Tags: add a custom tag"""
        Tag.seed_defaults()  # custom tags always come after the defaults
        if Tag.query.count() >= MAX_TAGS:
            abort(400, "Too many tags")
        name, color = _clean(request.get_json(silent=True) or {}, None)
        last = db.session.query(db.func.max(Tag.position)).scalar() or 0
        tag = Tag(name=name, color=color, is_default=False, position=last + 1)
        db.session.add(tag)
        db.session.commit()
        return {"created_id": tag.id, **_list_out()}


class TagApi(MethodView):
    decorators = [login_required(ALL_ROLES)]

    @staticmethod
    def _tag(tag_id: int) -> Tag:
        if g.account.role != Role.super_admin:
            abort(403, "Only a super admin can change or delete tags")
        return db.session.get(Tag, tag_id) or abort(404, "Tag not found")

    def patch(self, tag_id: int):
        """Tags: rename a tag or change its color (super admin)"""
        tag = self._tag(tag_id)
        tag.name, tag.color = _clean(request.get_json(silent=True) or {}, tag)
        db.session.commit()
        return _list_out()

    def delete(self, tag_id: int):
        """Tags: delete a custom tag (super admin; it is taken off every user)"""
        tag = self._tag(tag_id)
        if tag.is_default:
            abort(400, "The default tags can not be deleted")
        TagLink.query.filter(TagLink.tag_id == tag.id).delete(synchronize_session=False)
        db.session.delete(tag)
        db.session.commit()
        return _list_out()


def _visible_uuid(kind: str, uuid: str) -> str:
    """The uuid of a user the signed-in admin may tag (404 otherwise)."""
    actor: AdminUser = g.account
    user = User.query.filter(User.uuid == uuid, User.deleted.is_(False), User.added_by.in_(actor.recursive_sub_admins_ids())).first()
    return user.uuid if user else abort(404, "Not found")


class TagAssignApi(MethodView):
    decorators = [login_required(ALL_ROLES)]

    def put(self):
        """Tags: set the tags of one user (several allowed; an empty list takes all off)"""
        body = request.get_json(silent=True) or {}
        kind = str(body.get("kind") or "")
        if kind not in KINDS:
            abort(400, "Unknown kind")
        uuid = _visible_uuid(kind, str(body.get("uuid") or ""))
        try:
            ids = [int(i) for i in body.get("tag_ids") or []]
        except (TypeError, ValueError):
            abort(400, "Invalid tags")
        kept = set_tags(kind, uuid, ids)
        db.session.commit()
        return {"uuid": uuid, "tag_ids": kept}

    def post(self):
        """Tags: add and / or remove tags on many users at once"""
        body = request.get_json(silent=True) or {}
        kind = str(body.get("kind") or "")
        if kind not in KINDS:
            abort(400, "Unknown kind")
        try:
            add = [int(i) for i in body.get("add") or []]
            remove = {int(i) for i in body.get("remove") or []}
        except (TypeError, ValueError):
            abort(400, "Invalid tags")
        uuids = [_visible_uuid(kind, str(u)) for u in body.get("uuids") or []]
        current = tags_of(kind, uuids)
        for uuid in uuids:
            ids = [i for i in current.get(uuid, []) if i not in remove]
            set_tags(kind, uuid, [*ids, *[i for i in add if i not in ids]])
        db.session.commit()
        return {"count": len(uuids)}
