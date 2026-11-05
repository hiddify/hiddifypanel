import unittest
from collections import namedtuple

from hiddifypanel.hutils.system_metrics import wire_counters

Nic = namedtuple("Nic", "bytes_sent bytes_recv")
# a proxied 300 MB download: loopback carries it once more each way, WARP once more
NICS = {"lo": Nic(300, 300), "eth0": Nic(4, 305), "warp": Nic(0, 0), "hiddifywg": Nic(0, 0), "docker0": Nic(7, 7)}


class WireCountersTest(unittest.TestCase):
    def test_physical_interfaces_only(self):
        got = wire_counters(NICS, physical=lambda name: name == "eth0")
        self.assertEqual((got.bytes_sent, got.bytes_recv), (4, 305))

    def test_no_physical_interface_skips_loopback_and_tunnels(self):
        nics = {**NICS, "venet0": Nic(10, 20)}
        nics.pop("eth0")
        got = wire_counters(nics, physical=lambda name: False)
        self.assertEqual((got.bytes_sent, got.bytes_recv), (10, 20))

    def test_several_nics_add_up(self):
        got = wire_counters({**NICS, "eth1": Nic(1, 2)}, physical=lambda name: name.startswith("eth"))
        self.assertEqual((got.bytes_sent, got.bytes_recv), (5, 307))


if __name__ == "__main__":
    unittest.main()
