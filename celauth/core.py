
import os
from base64 import b32encode
from warnings import warn
from celauth.session import CelSession

class AuthError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __unicode__(self):
        return unicode(self.msg)

class NotLoggedInError(AuthError):
    def __init__(self):
        AuthError.__init__(self, "Not logged in")

class AccountAlreadyExists(AuthError):
    def __init__(self):
        AuthError.__init__(self, "Account already exists")

class InvalidConfirmationCode(AuthError):
    def __init__(self):
        AuthError.__init__(self, "Invalid email confirmation code")

class AddressAccountConflict(AuthError):
    def __init__(self):
        AuthError.__init__(self, "Email address assigned to different account")


class CelLogin(object):
    def __init__(self, registry_store, loginid):
        self._store = registry_store
        self._loginid = loginid

    @property
    def account(self):
        return self._store.account(self._loginid)

    def addresses_joinable(self):
        if self.account:
            return []
        credibles = self._store.addresses_credible(self._loginid)
        return [a for a in credibles if not self._store.is_free_address(a)]

    def can_create_account(self):
        if self.account:
            return False
        if self.addresses_joinable():
            return False
        if self._store.has_incredible_claims(self._loginid):
            return False
        return bool(self._store.addresses_credible(self._loginid))

    def create_account(self):
        account = self._store.create_account(self._loginid)
        assert account
        for addr in self._store.addresses_credible(self._loginid):
            if self._store.is_free_address(addr):
                self._store.assign(addr, account)

class CelRegistry(object):
    def __init__(self, registry_store, mailer):
        self._registry = registry_store
        self._mailer = mailer

    def get_login(self, loginid):
        assert loginid
        return CelLogin(self._registry, loginid)

    def _equiv_loginids(self, loginid):
        account = self._registry.account(loginid)
        return self._registry.loginids(account) if account else [loginid]

    def _make_claim(self, loginid, email_address, credible):
        self._registry.claim(loginid, email_address, credible)
        # os.urandom(5) will produce about 1 trillion possibilities
        if not self._registry.is_confirmed_claim(loginid, email_address):
            self._send_code(email_address)

    def _send_code(self, email_address):
        code = b32encode(os.urandom(5))
        self._registry.save_confirmation_code(code, email_address)
        self._mailer.send_code(code, email_address)

    def _addresses(self, loginids):
        ret = set()
        for lid in loginids:
            ret |= set(self._registry.addresses(lid))
        return list(ret)

    def _addresses_pending(self, loginids):
        ret = set()
        for lid in loginids:
            ret |= set(self._registry.addresses_not_confirmed(lid))
        #TODO fix bug: should return addresss not confirmed by all loginids, not any one loginid
        return list(ret)

    def _addresses_confirmed(self, loginids):
        ret = set()
        for lid in loginids:
            ret |= set(self._registry.addresses_confirmed(lid))
        return list(ret)

class AuthGate(CelRegistry):
    def __init__(self, cel_registry, session_store, mailer):
        self._session = CelSession(session_store)
        CelRegistry.__init__(self, cel_registry, mailer)

    @property
    def loginid(self):
        return self._session.loginid

    @property
    def account(self):
        return self.get_login(self.loginid).account if self.loginid else None

    @property
    def _loginids(self):
        return self._equiv_loginids(self.loginid)

    def addresses(self):
        return self._addresses(self._loginids)

    def addresses_pending(self):
        return self._addresses_pending(self._loginids)

    def addresses_confirmed(self):
        return self._addresses_confirmed(self._loginids)

    def addresses_joinable(self):
        if not self.loginid:
            return None
        return self.get_login(self.loginid).addresses_joinable()

    def disclaim_pending(self):
        if self.account:
            for a in self._addresses_pending(self._loginids):
                self._registry.remove_address(self.account, a)
            self._registry.remove_address(self.account, a)
        for lid in self._loginids:
            for a in self._registry.addresses_not_confirmed(lid):
                self._registry.disclaim(lid, a)

    def new_auth(self, openid_case):
        self.login(openid_case)

    def login(self, openid_case):
        new_loginid = self._registry.note_openid(openid_case)
        address = self._normalize_email(openid_case.email)
        if address and address not in self.addresses():
            self._make_claim(new_loginid, address, openid_case.credible)
        account = self._registry.account(new_loginid)
        if account and self._session.loginid:
            self._registry.set_account(self._session.loginid, account)
        self._session.set_loginid(new_loginid)

    def logout(self):
        self._session.clear()

    def claim(self, email_address):
        address = self._normalize_email(email_address)
        if self.loginid:
            self._make_claim(self.loginid, address, False)
        else:
            self._send_code(address)

    def confirmation_required(self):
        registry = self._registry
        for a in registry.addresses_not_confirmed(self.loginid):
            if registry.assigned_account(a):
                return True
        return registry.has_incredible_claims(self.loginid)

    def confirm_email(self, code):
        """Register that login is confirming email confirmation code.
        Raises:
            InvalidConfirmationCode
            AddressAccountConflict: Email address is already assigned to
                another acccount.
        """
        registry = self._registry
        session = self._session
        address = registry.confirm_email(self.loginid, code)
        if not address:
            raise InvalidConfirmationCode
        account = registry.account(self.loginid)
        if account:
            if not registry.add_address(account, address):
                raise AddressAccountConflict
        else:
            account = registry.assigned_account(address)
            if account:
                registry.set_account(self.loginid, account)
                session.account_update()

    def can_create_account(self):
        if not self.loginid:
            return False
        return self.get_login(self.loginid).can_create_account()

    def create_account(self):
        if not self.loginid:
            raise NotLoggedInError
        if self.account:
            raise AccountAlreadyExists
        if not self.can_create_account():
            raise AuthError("Account can not be created") 
        self.get_login(self.loginid).create_account()
        self._session.account_update()

    @classmethod
    def _normalize_email(cls, email):
        if email:
            try:
                email_name, domain_part = email.strip().rsplit('@', 1)
            except ValueError:
                pass
            else:
                email = '@'.join([email_name, domain_part.lower()])
        return email

