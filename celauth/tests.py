#!/usr/bin/env python

""" The celauth tests module implements unittests closely to the mathematical
formalization of the Claimed Email Login model.
"""

# django.utils.unittest is Python 2.7 unittest backported
# django.utils.unittest used while Python 2.6 supported
# use unittest2 to remove Django dependency on Python 2.6 
from django.utils import unittest

from core import make_auth_gate
from session import CelSession
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

class TestCelRegistryStore(object):
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

    def all_uris_by_account(self):
        """For testing"""
        inverse = dict()
        for uri, account in self.loginid2account.iteritems():
            if account:
                uris = inverse.setdefault(account, set())
                uris.add(uri)
        for address, account in self.address2account.iteritems():
            if account:
                uris = inverse.setdefault(account, set())
                uris.add('mailto:' + address)
        return set(map(frozenset,inverse.values()))
    
    def loginids(self, account):
        lids = self.loginids
        return [l for l, a in self.loginid2account.items() if a == account]

    def account(self, loginid):
        return self.loginid2account[loginid] if loginid else None

    def addresses(self, loginid):
        return [a for (l, a) in self.claims if l == loginid]

    def addresses_not_confirmed(self, loginid):
        pendings = self.claims - self.confirms
        return [a for (l, a) in pendings if l == loginid]

    def addresses_confirmed(self, loginid):
        return [a for (l, a) in self.confirms if l == loginid]

    def addresses_credible(self, loginid):
        return [a for (l, a) in self.credibles if l == loginid]

    def is_confirmed_claim(self, loginid, address):
        return (loginid, address) in self.confirms

    def is_free_address(self, address):
        return address not in self.address2account.keys()

    def assign(self, address, account):
        assert self.is_free_address(address)
        self.address2account[address] = account

    def note_openid(self, openid_case):
        loginid = openid_case.claimed_id
        self.loginid2account.setdefault(loginid, None)
        return loginid

    def claim(self, loginid, address, credible):
        self.claims.add((loginid, address))
        if credible:
            self.credibles.add((loginid, address))

    def disclaim(self, loginid, address):
        claim = (loginid, address)
        self.confirms.discard(claim)
        self.credibles.discard(claim)
        self.claims.discard(claim)

    def save_confirmation_code(self, code, address):
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
        if not address in self.address2account:
            self.address2account[address] = account
            return True
        return account == self.address2account[address]

    def remove_address(self, account, address):
        if address == self.address2account.get(account, None):
            del self.address2account[account]

    def set_account(self, loginid, account):
        self.loginid2account[loginid] = account

    def create_account(self, loginid):
        accts = self.loginid2account.values() + self.address2account.values()
        account_num = len(set(accts)) + 1
        if loginid.startswith('mailto:'):
            address = loginid[7:]
            self.address2account[address] = account_num
        else:
            self.loginid2account[loginid] = account_num
        return account_num

    def has_incredible_claims(self, loginid):
        incredibles = self.claims - self.credibles
        return len([l for (l, a) in incredibles if l == loginid]) > 0

class FakeMailer(object):
    last_code = None

    def send_code(self, code, address):
        FakeMailer.last_code = code

def code_in_email():
    return FakeMailer.last_code is not None

def take_code_from_email():
    ret = FakeMailer.last_code
    FakeMailer.last_code = None
    return ret

def openid(tld, name, address=None):
    luri = 'https://example.' + tld + '/' + name
    credible = (tld == 'com')
    email = address if address else '%s@example.%s' % (name, tld)
    return OpenIDCase(claimed_id=luri, display_id=luri,
                      email=email, credible=credible)

class CelTestCase(unittest.TestCase):
    def setUp(self):
        self.store = TestCelRegistryStore()
        self.gate = make_auth_gate(self.store, FakeMailer(), TestSessionStore())

    def login_as(self, loginid):
        self.gate.login(loginid)
        self.assertTrue(self.gate.loginid)

    def new_account(self, loginid):
        self.assertFalse(self.gate.loginid)
        self.assertFalse(self.gate.account)
        self.login_as(loginid)
        self.assertFalse(self.gate.account)
        if loginid.credible:
            self.assertFalse(self.gate.confirmation_required())
        else:
            self.assertTrue(self.gate.confirmation_required())
            self.assertFalse(self.gate.can_create_account())
            self.assertTrue(code_in_email())
            self.gate.confirm_email(take_code_from_email())
        self.assertTrue(self.gate.can_create_account())
        self.gate.create_account()
        self.assertTrue(self.gate.account)
        if code_in_email():
            # even if confirmation was not required, confirm it anyway
            self.gate.confirm_email(take_code_from_email())

class NewAcountTests(CelTestCase):
    def test_new_account_credible_email(self):
        self.new_account(openid('com', 'joe'))
        self.assertEqual(self.gate.addresses(), ['joe@example.com'])
        self.assertEqual(self.store.all_uris_by_account(), set([
            frozenset(['mailto:joe@example.com', 'https://example.com/joe']),
                        ]))

    def test_new_account_incredible_email(self):
        self.new_account(openid('org', 'joe'))
        self.assertEqual(self.gate.addresses(), ['joe@example.org'])
        self.assertEqual(self.gate.addresses_confirmed(), ['joe@example.org'])
        self.assertEqual(self.store.all_uris_by_account(), set([
            frozenset(['mailto:joe@example.org', 'https://example.org/joe']),
                        ]))

    def test_email_dislclaim(self):
        gate = self.gate
        self.assertFalse(gate.loginid)
        self.login_as(openid('org', 'joe'))
        self.assertFalse(gate.account)
        self.assertTrue(gate.addresses())
        self.assertTrue(gate.confirmation_required())
        self.assertFalse(gate.can_create_account())
        self.assertTrue(code_in_email())
        take_code_from_email()
        gate.disclaim_pending()
        self.assertFalse(gate.addresses())

class AssignedAccountTests(CelTestCase):
    def setUp(self):
        CelTestCase.setUp(self)
        self.store.create_account('mailto:admin@example.org')
        self.store.create_account('mailto:admin@example.com')
        self.assertEqual(self.store.all_uris_by_account(), set([
            frozenset(['mailto:admin@example.org']),
            frozenset(['mailto:admin@example.com']),
                        ]))

    def login_to_assigned(self, loginid):
        self.assertFalse(self.gate.loginid)
        self.login_as(loginid)
        self.assertFalse(self.gate.account)
        self.assertTrue(self.gate.confirmation_required())
        self.assertFalse(self.gate.can_create_account())
        self.assertTrue(code_in_email())
        self.gate.confirm_email(take_code_from_email())
        self.assertFalse(self.gate.can_create_account())
        self.assertTrue(self.gate.account)

    def test_incredible_email(self):
        self.login_to_assigned(openid('org', 'admin'))

    def test_credible_email(self):
        self.login_to_assigned(openid('com', 'admin'))

class ExistingAccountTests(CelTestCase):
    def setUp(self):
        CelTestCase.setUp(self)
        self.new_account(openid('com', 'me'))
        self.gate.logout()
        self.assertEqual(self.store.all_uris_by_account(), set([
            frozenset(['mailto:me@example.com', 'https://example.com/me']),
                        ]))

    def test_2nd_account(self):
        self.new_account(openid('com', 'joe'))
        self.assertEqual(self.gate.addresses(), ['joe@example.com'])
        self.assertEqual(self.store.all_uris_by_account(), set([
            frozenset(['mailto:me@example.com', 'https://example.com/me']),
            frozenset(['mailto:joe@example.com', 'https://example.com/joe']),
                        ]))

    def test_join_account(self):
        self.login_as(openid('com', 'me2', 'me@example.com'))
        self.assertFalse(self.gate.account)
        self.assertFalse(self.gate.confirmation_required())
        self.assertFalse(self.gate.can_create_account())
        self.assertTrue(self.gate.addresses_joinable())
        self.assertEqual(self.store.all_uris_by_account(), set([
            frozenset(['mailto:me@example.com', 'https://example.com/me']),
                        ]))
        self.login_as(openid('com', 'me'))
        self.assertEqual(self.store.all_uris_by_account(), set([
            frozenset([
                'mailto:me@example.com',
                'https://example.com/me',
                'https://example.com/me2',
            ]),
                        ]))

class EmailTests(CelTestCase):
    def test_anon_address_entry(self):
        self.assertFalse(code_in_email())
        self.gate.claim('me@example.com')
        self.assertTrue(code_in_email())
        take_code_from_email()


if __name__ == '__main__':
    unittest.main()

