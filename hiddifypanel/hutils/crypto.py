import base64
import os
import subprocess
import sys
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import x25519, ed25519

_VLESS_ENC_METHOD = "mlkem768x25519plus"
_VLESS_ENC_MODE = "native"


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
    priv_bytes = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    pub_bytes = pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    if base_64_encode:
        pub_str = _b64url_nopad(pub_bytes)
        priv_str = _b64url_nopad(priv_bytes)
    else:
        pub_str=pub_bytes.hex()
        priv_str=priv_bytes.hex()
    return {'private_key': priv_str, 'public_key': pub_str}


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


def generate_ssh_host_keys():
    key_types = ["dsa", "ecdsa", "ed25519", "rsa"]
    keys_dict = {}

    # Generate and read keys
    for key_type in key_types:
        key_file = f"ssh_host_{key_type}_key"

        subprocess.run([
            "ssh-keygen", "-t", key_type,
            "-f", key_file,
            "-N", "" 
        ], check=True,stdout=sys.stderr)

        keys_dict[key_type]={}
        with open(key_file, "r") as f:
            keys_dict[key_type]['pk'] = f.read()
        with open(f"{key_file}.pub", "r") as f:
            keys_dict[key_type]['pub'] = f.read()

        os.remove(key_file)
        os.remove(f"{key_file}.pub")  # Remove the public key if not needed
    return keys_dict