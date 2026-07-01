"""Type-safe Jinja template context variables."""

from .cert import CertVar
from .ctx_client import ClientContextDomainAlpnVar, ClientContextDomainVar, ClientContextVar
from .ctx_server import ServerContextVar
from .domain import DomainIPVar
from .hconfig import HConfigVar
from .ip import IPVar
from .platform import PlatformVar
from .proxy import ProxyDomainAlpnVar, ProxyDomainVar, ProxyVar
from .user import UserVar
from .version import PlatformPart, TemplateVersion

DomainVar = DomainIPVar

_BUILDER_EXPORTS = frozenset({
    'build_client_context',
    'build_server_context',
    'build_var_context',
    'domain_var',
    'hconfig_var',
    'ip_var',
    'platform_var',
    'proxy_var',
    'reality_public_key',
    'user_var',
})

__all__ = [
    'CertVar',
    'ClientContextDomainAlpnVar',
    'ClientContextDomainVar',
    'ClientContextVar',
    'DomainIPVar',
    'DomainVar',
    'HConfigVar',
    'IPVar',
    'PlatformPart',
    'PlatformVar',
    'ProxyDomainAlpnVar',
    'ProxyDomainVar',
    'ProxyVar',
    'ServerContextVar',
    'TemplateVersion',
    'UserVar',
    *sorted(_BUILDER_EXPORTS),
]


def __getattr__(name: str):
    if name in _BUILDER_EXPORTS:
        from . import builder

        return getattr(builder, name)
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
