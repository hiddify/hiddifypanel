import unittest

from hiddifypanel.hutils.crypto import vless_encryption_decryption, vless_encryption_error, vless_encryption_pair
from hiddifypanel.proxy_v3.context_vars.hconfig import HConfigVar

try:
    from cryptography.hazmat.primitives.asymmetric.mlkem import MLKEM768PrivateKey  # noqa: F401

    HAS_MLKEM = True
except ImportError:
    HAS_MLKEM = False


class VlessEncryptionTest(unittest.TestCase):
    def setUp(self):
        self.enc, self.dec = vless_encryption_decryption()

    def test_off(self):
        for enc, dec in (("", ""), ("", "none"), ("none", "none"), (None, None)):
            self.assertIsNone(vless_encryption_error(enc, dec))

    def test_generated_pair(self):
        self.assertIsNone(vless_encryption_error(self.enc, self.dec))

    @unittest.skipUnless(HAS_MLKEM, "cryptography without ML-KEM")
    def test_generated_post_quantum_pair(self):
        self.assertIsNone(vless_encryption_error(*vless_encryption_decryption(quantum=True)))

    def test_padding_and_ticket_range(self):
        method, mode, _, key = self.dec.split(".")
        dec = ".".join((method, mode, "300-600s", "100-111-1111", "75-0-111", key))
        self.assertIsNone(vless_encryption_error(self.enc, dec))

    def test_decryption_xray_refuses(self):
        # each of these stops Xray: "VLESS settings: unsupported decryption"
        method, mode, _, key = self.dec.split(".")
        for dec in ("abc", "mlkem768x25519plus", ".".join((method, "fast", "600s", key)), ".".join((method, mode, "0rtt", key)), self.enc, self.dec + "x"):
            self.assertEqual(vless_encryption_error("", dec), "decryption", dec)

    def test_encryption_invalid(self):
        method, mode, _, key = self.enc.split(".")
        for enc in ("abc", ".".join((method, mode, "600s", key)), self.dec):
            self.assertEqual(vless_encryption_error(enc, "none"), "encryption", enc)

    def test_pair(self):
        other_enc, other_dec = vless_encryption_decryption()
        self.assertEqual(vless_encryption_error(self.enc, ""), "pair")
        self.assertEqual(vless_encryption_error("", self.dec), "pair")
        self.assertEqual(vless_encryption_error(other_enc, self.dec), "pair")
        self.assertEqual(vless_encryption_error(self.enc.replace(".native.", ".xorpub."), self.dec), "pair")
        self.assertIsNone(vless_encryption_error(other_enc, other_dec))

    def test_pair_off_when_invalid(self):
        self.assertEqual(vless_encryption_pair(self.enc, self.dec), (self.enc, self.dec))
        self.assertEqual(vless_encryption_pair("", "abc"), ("", "none"))
        self.assertEqual(vless_encryption_pair(self.enc, ""), ("", "none"))

    def test_templates_never_get_a_refused_value(self):
        h = HConfigVar({"vless_encryption": "", "vless_decryption": "abc"}, server_side=True)
        self.assertEqual((h.vless_encryption, h.vless_decryption), ("", "none"))
        h = HConfigVar({"vless_encryption": self.enc, "vless_decryption": self.dec})
        self.assertEqual((h.vless_encryption, h.vless_decryption), (self.enc, self.dec))
        self.assertIsNone(HConfigVar({"vless_flow": "xtls-rprx-vision"}).vless_decryption)


if __name__ == "__main__":
    unittest.main()
