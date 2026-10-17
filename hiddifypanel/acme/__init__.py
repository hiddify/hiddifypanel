"""Certificates issued by the panel (ACME: Let's Encrypt, then ZeroSSL), kept in tls_store, served by HAProxy.

- ``issue``: one certificate over HTTP-01; HAProxy answers the challenges from an in-memory map (``challenges``).
- ``store``: tls_store → data/cert files → the running HAProxy (no reload); self-signed stand-ins.
- ``renew``: which domains, in which order, in parallel, failures and rate limits; the domains page's job state.
- ``client``: the ACME accounts (``acme_email`` setting).

Replaces acme.sh and nginx (they only served the challenge files).
"""
