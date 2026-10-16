"""On a node, users and admins come from the parent panel (hutils/node/sync_feed.py): the node shows them read-only."""

from apiflask import abort

from hiddifypanel import hutils

READ_ONLY_MESSAGE = "Users and admins are managed on the parent panel; on a node they are read-only"


def is_read_only() -> bool:
    return hutils.node.is_child()


def deny_write_on_node() -> None:
    """Call first in an endpoint that changes users or admins (an edit here would be undone by the next parent sync)."""
    if is_read_only():
        abort(403, READ_ONLY_MESSAGE)
