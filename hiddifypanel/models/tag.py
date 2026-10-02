"""Colored tags (like the macOS Finder's) an admin puts on users to find them again.

A tag has a name and one of a few colors. An account can have several tags; links point at the
account's uuid so they follow users that are renamed, deleted and recreated.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from hiddifypanel.database import db

COLORS = ("red", "orange", "green", "blue", "black")
KINDS = ("user",)
#: Always there, in this order; they can not be deleted or renamed.
DEFAULT_TAGS = (
    ("family", "green"),
    ("friends", "red"),
    ("work", "blue"),
    ("important", "orange"),
    ("free", "black"),
)
MAX_TAGS = 100


class Tag(db.Model):  # type: ignore
    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    color: Mapped[str] = mapped_column(String(20), default="blue")
    is_default: Mapped[bool] = mapped_column(default=False)
    position: Mapped[int] = mapped_column(default=0)

    @staticmethod
    def seed_defaults() -> None:
        """Create the default tags that are missing."""
        # Only on a panel without them: a super admin may rename or recolor the defaults later.
        if Tag.query.filter(Tag.is_default.is_(True)).count():
            return
        have = {name for (name,) in db.session.query(Tag.name).all()}
        for i, (name, color) in enumerate(DEFAULT_TAGS, start=1):
            if name not in have:
                db.session.add(Tag(name=name, color=color, is_default=True, position=i))
        db.session.flush()

    @staticmethod
    def ordered() -> list[Tag]:
        return Tag.query.order_by(Tag.position, Tag.id).all()


class TagLink(db.Model):  # type: ignore
    __tablename__ = "tag_link"
    __table_args__ = (Index("ix_tag_link_account", "kind", "account_uuid"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(10))
    account_uuid: Mapped[str] = mapped_column(String(36))


def tags_of(kind: str, uuids: list[str] | None = None) -> dict[str, list[int]]:
    """Tag ids per account uuid (only accounts that have some)."""
    query = TagLink.query.filter(TagLink.kind == kind)
    if uuids is not None:
        query = query.filter(TagLink.account_uuid.in_(uuids))
    out: dict[str, list[int]] = {}
    for link in query.order_by(TagLink.id).all():
        out.setdefault(link.account_uuid, []).append(link.tag_id)
    return out


def set_tags(kind: str, uuid: str, tag_ids: list[int]) -> list[int]:
    """Replace the tags of one account; unknown ids are ignored. Returns the ids kept."""
    valid = {t.id for t in Tag.query.filter(Tag.id.in_(tag_ids)).all()} if tag_ids else set()
    keep = [i for i in dict.fromkeys(tag_ids) if i in valid]
    TagLink.query.filter(TagLink.kind == kind, TagLink.account_uuid == uuid).delete(synchronize_session=False)
    for tag_id in keep:
        db.session.add(TagLink(tag_id=tag_id, kind=kind, account_uuid=uuid))
    return keep


def export_tags() -> list[dict]:
    """Backup rows of the tag list, in order."""
    from hiddifypanel.models.external_model.tag import TagModel

    return [TagModel(name=t.name, color=t.color, is_default=bool(t.is_default), position=t.position).to_dict() for t in Tag.ordered()]


def export_links() -> list[dict]:
    """Backup rows of who has which tag (by tag name, so ids stay local)."""
    from hiddifypanel.models.external_model.tag import TagLinkModel

    names = {t.id: t.name for t in Tag.query.all()}
    links = TagLink.query.order_by(TagLink.id).all()
    return [TagLinkModel(kind=l.kind, account_uuid=l.account_uuid, tag=names[l.tag_id]).to_dict() for l in links if l.tag_id in names]


def restore_tags(rows, links, *, kinds: set[str]) -> None:
    """Add / update tags by name, then replace the tags of the accounts in ``links`` (only the given kinds). Commits nothing."""
    from hiddifypanel.models.external_model.tag import TagLinkModel, TagModel

    existing = {t.name.lower(): t for t in Tag.query.all()}
    for m in TagModel.coerce_many(rows):
        tag = existing.get(m.name.lower())
        if tag is None:
            tag = existing[m.name.lower()] = Tag(name=m.name)
            db.session.add(tag)
        tag.color = m.color
        tag.position = m.position
        tag.is_default = tag.is_default or m.is_default
    db.session.flush()

    wanted: dict[tuple[str, str], list[int]] = {}
    for link in TagLinkModel.coerce_many(links):
        tag = existing.get(link.tag.lower())
        if tag is not None and link.kind in kinds:
            wanted.setdefault((link.kind, link.account_uuid), []).append(tag.id)
    for (kind, uuid), ids in wanted.items():
        set_tags(kind, uuid, ids)
