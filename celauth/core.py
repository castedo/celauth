
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


class CelRegistry(object):
    def __init__(self, registry_store, mailer):
        self._registry = registry_store
        self._mailer = mailer

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

    def _make_claim(self, loginid, email_address, credible):
        self._registry.claim(loginid, email_address, credible)
        # os.urandom(5) will produce about 1 trillion possibilities
        code = b32encode(os.urandom(5))
        self._registry.save_confirmation_code(code, email_address)
        #TODO if already confirmed, send email to that effect
        #TODO catch any user conflict exception and send email to that effect
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
        return self._registry.account(self.loginid)

    @property
    def _loginids(self):
        r = self._registry
        return r.loginids(self.account) if self.account else [self.loginid]

    def addresses(self):
        return self._addresses(self._loginids)

    def addresses_pending(self):
        return self._addresses_pending(self._loginids)

    def addresses_confirmed(self):
        return self._addresses_confirmed(self._loginids)

    def addresses_joinable(self):
        if self.account:
            return []
        r = self._registry
        credibles = r.addresses_credible(self.loginid)
        return [a for a in credibles if not r.is_free_address(a)]

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
        self._make_claim(self.loginid, address, False)

    def confirmation_required(self):
        registry = self._registry
        for a in registry.addresses_not_confirmed(self.loginid):
            if registry.assigned_account(a):
                return True
        return registry.has_incredible_claims(self.loginid)

    def confirm_email(self, code):
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
        return True

    def can_create_account(self):
        if self.account or not self.loginid:
            return False
        registry = self._registry
        if self.addresses_joinable():
            return False
        if registry.has_incredible_claims(self.loginid):
            return False
        return bool(registry.addresses_credible(self.loginid))

    def create_account(self):
        if not self.loginid:
            raise NotLoggedInError
        if self.account:
            raise AccountAlreadyExists
        registry = self._registry
        if not self.can_create_account():
            raise AuthError("Account can not be created") 
        account = registry.create_account(self.loginid)
        assert account
        for addr in registry.addresses_credible(self.loginid):
            if registry.is_free_address(addr):
                registry.assign(addr, account)
        assert not registry.is_free_address(addr)
        self._session.account_update()

