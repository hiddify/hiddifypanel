"""Self-signed certificates: for decoy (fake) domains, and as a stand-in until (or when) a real one can not be issued.

HAProxy needs a certificate for every domain it serves (and at least one to start at all).
"""

from __future__ import annotations

import ipaddress
from datetime import UTC, datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

DAYS = 90


def san_for(host: str) -> x509.GeneralName:
    """An IP address SAN for an address, a DNS one for a name."""
    try:
        return x509.IPAddress(ipaddress.ip_address(host.strip("[]")))
    except ValueError:
        return x509.DNSName(host)


def make(host: str, days: int = DAYS) -> tuple[str, str]:
    """(certificate PEM, private key PEM) of a self-signed certificate for ``host`` (a name or an IP address)."""
    host = (host or "").strip().lower()
    key = ec.generate_private_key(ec.SECP256R1())
    # Same subject as acme.sh's self-signed ones; the CN is at most 64 characters (x509), the SAN has the whole name.
    name = x509.Name([x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Google Trust Services LLC"), x509.NameAttribute(NameOID.COMMON_NAME, host[:64] or "localhost")])
    now = datetime.now(UTC)
    builder = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=days))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
    )
    if host:
        builder = builder.add_extension(x509.SubjectAlternativeName([san_for(host)]), critical=False)
    cert = builder.sign(key, hashes.SHA256())
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    key_pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    return cert_pem, key_pem
