from __future__ import annotations

from functools import lru_cache

from .fragment_loader import load_template_slug


@lru_cache(maxsize=16)
def default_sublink_link_template() -> str:
    from .client_builder import render_sublink_link_template
    from .proxy_matrix import ProxyCombination

    combo = ProxyCombination(
        l3='tls',
        transport='tcp',
        cdn='direct',
        proto='vless',
        enable=True,
        name='default',
    )
    return render_sublink_link_template(combo)


@lru_cache(maxsize=16)
def default_server_listen_snippet() -> str:
    return load_template_slug('xray/inbound/listen')


def default_server_inbound_template() -> str:
    listen = default_server_listen_snippet()
    return '{\n' + listen + '\n}'
