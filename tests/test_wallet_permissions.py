"""Wallet management remains owner-only even when bypassing browser controls."""
from tests.support import LedgerFixture


class WalletPermissionTests(LedgerFixture):
    def test_staff_can_view_but_cannot_manage_wallets_or_funding(self):
        self.req("staff", name="View only staff", password="Fictional-password-19")
        self.req("login", name="View only staff", password="Fictional-password-19")
        before = self.req("state")[1]
        wallet = before["accounts"][0]
        changes = [
            ("account", dict(name="Unauthorized", provider="Other", kind="Normal", opening=0)),
            ("account", dict(id=wallet["id"], name="Changed", provider=wallet["provider"], kind=wallet["kind"], active=True)),
            ("account", dict(id=wallet["id"], name=wallet["name"], provider=wallet["provider"], kind=wallet["kind"], active=False)),
            ("entry", dict(id="staff-add-funds", type="funds_in", amount=100, account_id=wallet["id"], note="Blocked")),
            ("entry", dict(id="staff-remove-funds", type="funds_out", amount=100, account_id=wallet["id"], note="Blocked")),
        ]
        for endpoint, payload in changes:
            with self.subTest(endpoint=endpoint, payload=payload):
                self.assertEqual(self.req(endpoint, **payload)[0], 400)
        after = self.req("state")[1]
        self.assertEqual(before["accounts"], after["accounts"])
        self.assertEqual(before["entries"], after["entries"])
        self.assertEqual(before["cash"], after["cash"])
        self.assertEqual(self.entry("staff-customer-deposit", "cash_in", 100000, wallet["id"])[0], 200)
