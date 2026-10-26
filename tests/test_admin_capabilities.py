import unittest
from types import SimpleNamespace as N

from hiddifypanel import admin_capabilities as caps
from hiddifypanel.models.admin import AdminMode


def admin(*, mode=AdminMode.agent, capabilities=None, can_add_admin=False):
    return N(mode=mode, capabilities=capabilities, can_add_admin=can_add_admin)


class AdminCapabilitiesTests(unittest.TestCase):
    def test_normalize_fills_all_keys(self):
        self.assertEqual(caps.normalize({"add_sub_admins": 1, "unknown": True}), {**caps.empty(), "add_sub_admins": True})
        self.assertEqual(caps.normalize(None), caps.empty())

    def test_super_admin_has_every_capability(self):
        a = admin(mode=AdminMode.super_admin, capabilities=caps.empty())
        self.assertEqual(caps.of(a), caps.full())
        self.assertTrue(caps.has(a, caps.MODIFY_OUTBOUNDS))

    def test_defaults_agents_cannot_override_outbound(self):
        d = caps.defaults_for_mode(AdminMode.agent, can_add_admin=True)
        self.assertTrue(d[caps.ADD_SUB_ADMINS])
        self.assertFalse(d[caps.OVERRIDE_PREFERRED_OUTBOUND])
        self.assertTrue(d[caps.ADD_EXTRA_SUBLINKS])
        self.assertFalse(d[caps.MODIFY_DOMAINS])
        self.assertFalse(d[caps.MODIFY_OUTBOUNDS])

    def test_defaults_admin_mode_keeps_domains_not_outbounds(self):
        d = caps.defaults_for_mode(AdminMode.admin, can_add_admin=False)
        self.assertTrue(d[caps.OVERRIDE_PREFERRED_OUTBOUND])
        self.assertTrue(d[caps.MODIFY_DOMAINS])
        self.assertFalse(d[caps.MODIFY_OUTBOUNDS])
        self.assertFalse(d[caps.ADD_SUB_ADMINS])

    def test_merge_cannot_grant_what_actor_lacks(self):
        actor = admin(capabilities={**caps.empty(), caps.ADD_SUB_ADMINS: True, caps.OVERRIDE_PREFERRED_OUTBOUND: True})
        target = caps.merge_for_actor(
            actor,
            {
                caps.ADD_SUB_ADMINS: True,
                caps.OVERRIDE_PREFERRED_OUTBOUND: True,
                caps.MODIFY_OUTBOUNDS: True,
                caps.MODIFY_DOMAINS: True,
            },
            creating=True,
        )
        self.assertTrue(target[caps.ADD_SUB_ADMINS])
        self.assertTrue(target[caps.OVERRIDE_PREFERRED_OUTBOUND])
        self.assertFalse(target[caps.MODIFY_OUTBOUNDS])
        self.assertFalse(target[caps.MODIFY_DOMAINS])
        # Creating starts empty: keys the parent does not send stay False.
        self.assertFalse(caps.merge_for_actor(actor, {caps.ADD_SUB_ADMINS: True}, creating=True)[caps.ADD_EXTRA_SUBLINKS])

    def test_merge_leaves_keys_actor_lacks_unchanged(self):
        actor = admin(capabilities={**caps.empty(), caps.ADD_SUB_ADMINS: True})
        existing = {**caps.empty(), caps.MODIFY_DOMAINS: True, caps.ADD_SUB_ADMINS: False}
        merged = caps.merge_for_actor(actor, {caps.ADD_SUB_ADMINS: True, caps.MODIFY_DOMAINS: False}, existing=existing)
        self.assertTrue(merged[caps.ADD_SUB_ADMINS])
        # Actor cannot touch modify_domains, so the target keeps True.
        self.assertTrue(merged[caps.MODIFY_DOMAINS])

    def test_of_falls_back_when_capabilities_missing(self):
        a = admin(mode=AdminMode.agent, capabilities=None, can_add_admin=True)
        self.assertEqual(caps.of(a), caps.defaults_for_mode(AdminMode.agent, can_add_admin=True))


if __name__ == "__main__":
    unittest.main()
