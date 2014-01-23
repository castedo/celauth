#!/usr/bin/env python

""" The celauth tests module implements unittests closely to the mathematical
formalization of the Claimed Email Login model.
"""

# django.utils.unittest is Python 2.7 unittest backported
# django.utils.unittest used while Python 2.6 supported
# use unittest2 to remove Django dependency on Python 2.6 
from django.utils import unittest

from core import AuthGate
from session import CelSession, CelRegistryBase
from celauth import OpenIDCase

class TestSessionStore(object):
    """A 'session store' saves the session specific state of CelSession
    """
    def __init__(self, request=None):
        self._loginids = []

    @property
    def loginids(self):
        return self._loginids

    def update(self):
        """Let implementation follow up with database updates, login/logouts, etc...
        for any changes made to self.loginids
        """
        pass

class TestCelRegistry(CelRegistryBase):
    """ Implementation of CEL registry state using simple Python dictionaries and sets
    """

    def __init__(self):
        """Initialization of member variables representing the fundamental mathematical
        parts of the Claimed Email Login formalization"""

        self.loginid2account = dict()
        self.address2account = dict()
        self.code2address = dict()
        self.claims = set()
        self.credibles = set()
        self.confirms = set()

    def loginids(self, account):
        lids = self.loginids
        return [l for l, a in self.loginid2account.items() if a == account]

    def account(self, loginid):
        return self.loginid2account[loginid] if loginid else None

    def addresses(self, loginid):
        return [a for (l, a) in self.claims if l == loginid]

    def addresses_pending(self, loginid):
        pendings = self.claims - self.confirms
        return [a for (l, a) in pendings if l == loginid]

    def addresses_confirmed(self, loginid):
        return [a for (l, a) in self.confirms if l == loginid]

    def addresses_credible(self, loginid):
        return [a for (l, a) in self.credibles if l == loginid]

    def is_free_address(self, address):
        return address not in self.address2account.keys()

    def assign(self, address, account):
        assert self.is_free_address(address)
        self.address2account[address] = account

    def note_openid(self, openid_case):
        loginid = openid_case.claimed_id
        self.loginid2account[loginid] = None
        return loginid

    def make_claim(self, loginid, email_address, credible):
        address = self._normalize_email(email_address)
        self.claims.add((loginid, address))
        if credible:
            self.credibles.add((loginid, address))

    def save_confirmation_code(self, code, email_address):
        address = self._normalize_email(email_address)
        assert code not in self.code2address
        self.code2address[code] = address

    def confirm_email(self, loginid, code):
        if code not in self.code2address:
            #TODO should raise exception
            return None
        address = self.code2address[code]
        self.claims.add((loginid, address))
        self.credibles.add((loginid, address))
        self.confirms.add((loginid, address))
        return address

    def assigned_account(self, address):
        account = self.address2account.get(address, None)
        if account and account in self.loginid2account.values():
            return None
        return account

    def add_address(self, account, address):
        if address in self.address2account:
            return False
        self.address2account[address] = account
        return True

    def set_account(self, loginid, account):
        loginid2account[loginid] = account

    def create_account(self, loginid):
        accts = self.loginid2account.values() + self.address2account.values()
        account_num = len(set(accts))
        self.loginid2account[loginid] = account_num
        return account_num

    def has_incredible_claims(self, loginid):
        incredibles = self.claims - self.credibles
        return len([l for (l, a) in incredibles if l == loginid]) > 0

class FakeMailer(object):
    last_code = None

    def send_code(self, code, address):
        FakeMailer.last_code = code

def id(tld, name, address=None):
    luri = 'http://example.' + tld + '/' + name
    credible = (tld == 'com')
    email = address if address else '%s@example.%s' % (name, tld)
    return OpenIDCase(claimed_id=luri, display_id=luri,
                      email=email, credible=credible)

class NewAcountTests(unittest.TestCase):
    def setUp(self):
        self.registry = TestCelRegistry()
        self.session = TestSessionStore()
        self.gate = AuthGate(self.registry, self.session, FakeMailer())

    def test_assigned_account(self):
        address = 'super@example.org'
        luri = 'http://example.org/super'
        self.registry.address2account = {address:1}

        self.assertFalse(self.gate.loginid)
        self.gate.new_auth(id('org', 'super'))
        self.assertEqual(self.gate.loginid, luri)

    def test_new_account_credible_email(self):
        gate = self.gate
        self.assertFalse(gate.loginid)
        gate.new_auth(id('com', 'joe'))
        self.assertTrue(gate.loginid)
        self.assertFalse(gate.account)
        self.assertFalse(gate.confirmation_required())
        self.assertTrue(gate.can_create_account())
        gate.create_account()
        self.assertTrue(gate.account)
        self.assertEqual(gate.addresses(), ['joe@example.com'])
        self.assertEqual(gate.addresses_pending(), ['joe@example.com'])

    def test_new_account_incredible_email(self):
        gate = self.gate
        self.assertFalse(gate.loginid)
        gate.new_auth(id('org', 'joe'))
        self.assertTrue(gate.loginid)
        self.assertFalse(gate.account)
        self.assertTrue(gate.confirmation_required())
        self.assertFalse(gate.can_create_account())
        self.assertTrue(FakeMailer.last_code)
        gate.confirm_email(FakeMailer.last_code)
        FakeMailer.last_code = None
        self.assertTrue(gate.can_create_account())
        gate.create_account()
        self.assertTrue(gate.account)
        self.assertEqual(gate.addresses(), ['joe@example.org'])
        self.assertEqual(gate.addresses_confirmed(), ['joe@example.org'])
        self.assertEqual(self.registry.loginid2account, {'http://example.org/joe':1})
        self.assertEqual(self.registry.address2account, {'joe@example.org':1})

if __name__ == '__main__':
    unittest.main()

