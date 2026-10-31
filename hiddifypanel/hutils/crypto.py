import base64
import functools
import os
import re
import subprocess
import tempfile

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, x25519

_VLESS_ENC_METHOD = "mlkem768x25519plus"
_VLESS_ENC_MODE = "native"
_VLESS_ENC_MODES = ("native", "xorpub", "random")
_B64URL = re.compile(r"[A-Za-z0-9_-]+")


def _b64url_nopad(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def get_ed25519_private_public_pair():
    privkey = ed25519.Ed25519PrivateKey.generate()
    pubkey = privkey.public_key()
    priv_bytes = privkey.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.OpenSSH,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = pubkey.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    )
    return priv_bytes.decode(), pub_bytes.decode()


def get_wg_private_public_psk_pair():
    try:
        private_key = subprocess.run(["wg", "genkey"], capture_output=True, text=True, check=True).stdout.strip()
        public_key = subprocess.run(["wg", "pubkey"], input=private_key, capture_output=True, text=True, check=True).stdout.strip()
        psk = subprocess.run(["wg", "genpsk"], capture_output=True, text=True, check=True).stdout.strip()
        return private_key, public_key, psk
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return None, None, None


def generate_x25519_keys(base_64_encode=True):
    priv = x25519.X25519PrivateKey.generate()
    pub = priv.public_key()
    priv_bytes = priv.private_bytes(encoding=serialization.Encoding.Raw, format=serialization.PrivateFormat.Raw, encryption_algorithm=serialization.NoEncryption())
    pub_bytes = pub.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
    if base_64_encode:
        pub_str = _b64url_nopad(pub_bytes)
        priv_str = _b64url_nopad(priv_bytes)
    else:
        pub_str = pub_bytes.hex()
        priv_str = priv_bytes.hex()
    return {"private_key": priv_str, "public_key": pub_str}


def vless_encryption_decryption(quantum: bool = False) -> tuple[str, str]:
    """Return Xray ``vlessenc`` client encryption and server decryption strings.

    Matches ``executeVLESSEnc``: X25519 when ``quantum`` is false, ML-KEM-768 when true.
    The two authentications must not be mixed. Ephemeral exchange is post-quantum either way.
    """
    if quantum:
        from cryptography.hazmat.primitives.asymmetric.mlkem import MLKEM768PrivateKey

        key = MLKEM768PrivateKey.generate()
        server_key = _b64url_nopad(key.private_bytes_raw())
        client_key = _b64url_nopad(key.public_key().public_bytes_raw())
    else:
        pair = generate_x25519_keys(base_64_encode=True)
        server_key = pair["private_key"]
        client_key = pair["public_key"]
    decryption = ".".join((_VLESS_ENC_METHOD, _VLESS_ENC_MODE, "600s", server_key))
    encryption = ".".join((_VLESS_ENC_METHOD, _VLESS_ENC_MODE, "0rtt", client_key))
    return encryption, decryption


def _b64url_decode(text: str) -> bytes | None:
    if not _B64URL.fullmatch(text) or len(text) % 4 == 1:
        return None
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _vless_enc_parts(value: str, *, server: bool) -> tuple[str, list[bytes]] | None:
    """(mode, keys) of a VLESS ``decryption`` (server) or ``encryption`` (client) value, checked as Xray parses it
    (infra/conf/vless.go): ``method.mode.time[.padding…].key[.key…]``. ``("none", [])`` when off, None when Xray
    refuses it (a refused ``decryption`` stops Xray from starting)."""
    if value in ("", "none"):
        return "none", []
    s = value.split(".")
    if len(s) < 4 or s[0] != _VLESS_ENC_METHOD or s[1] not in _VLESS_ENC_MODES:
        return None
    if server:  # ticket lifetime: "600s" or "300-600s"
        if not re.fullmatch(r"\d+(-\d+)?", s[2].removesuffix("s")):
            return None
    elif s[2] not in ("0rtt", "1rtt"):
        return None
    sizes = (32, 64) if server else (32, 1184)  # X25519 / ML-KEM-768: private key or seed, public key
    keys = []
    for part in s[3:]:
        if len(part) < 20:  # a padding block
            continue
        key = _b64url_decode(part)
        if key is None or len(key) not in sizes:
            return None
        keys.append(key)
    return (s[1], keys) if keys else None


def _vless_client_key(server_key: bytes) -> bytes | None:
    """The client (public) key of a server key; None when this cryptography has no ML-KEM to tell."""
    if len(server_key) == 32:
        return x25519.X25519PrivateKey.from_private_bytes(server_key).public_key().public_bytes_raw()
    try:
        from cryptography.hazmat.primitives.asymmetric.mlkem import MLKEM768PrivateKey
    except ImportError:
        return None
    return MLKEM768PrivateKey.from_seed_bytes(server_key).public_key().public_bytes_raw()


@functools.lru_cache(maxsize=32)
def vless_encryption_error(encryption: str, decryption: str) -> str | None:
    """None when Xray accepts both and clients can connect with them: both off, or a server ``decryption`` with the
    client ``encryption`` made from it (one ``xray vlessenc`` output). Else what is wrong: ``"decryption"``,
    ``"encryption"`` or ``"pair"`` (only one of them set, or from different outputs)."""
    dec = _vless_enc_parts(decryption or "", server=True)
    if dec is None:
        return "decryption"
    enc = _vless_enc_parts(encryption or "", server=False)
    if enc is None:
        return "encryption"
    if dec[0] != enc[0] or len(dec[1]) != len(enc[1]):
        return "pair"
    for server_key, client_key in zip(dec[1], enc[1]):
        derived = _vless_client_key(server_key)
        if derived is not None and derived != client_key:
            return "pair"
    return None


def vless_encryption_pair(encryption: str, decryption: str) -> tuple[str, str]:
    """The (encryption, decryption) Xray and the clients get: the settings when they work together, else off, so one
    wrong value never keeps Xray from starting or the clients from connecting."""
    if vless_encryption_error(encryption, decryption):
        return "", "none"
    return encryption, decryption


def generate_ssh_host_keys():
    # DSA is gone from modern OpenSSH ("unknown key type dsa"); callers only use rsa/ecdsa/ed25519.
    key_types = ["ecdsa", "ed25519", "rsa"]
    keys_dict = {}

    with tempfile.TemporaryDirectory(prefix="hiddify-ssh-host-") as tmp:
        for key_type in key_types:
            key_file = os.path.join(tmp, f"ssh_host_{key_type}_key")
            subprocess.run(
                ["ssh-keygen", "-t", key_type, "-f", key_file, "-N", ""],
                check=True,
                capture_output=True,
                text=True,
            )
            with open(key_file) as f:
                pk = f.read()
            with open(f"{key_file}.pub") as f:
                pub = f.read()
            keys_dict[key_type] = {"pk": pk, "pub": pub}

    return keys_dict
