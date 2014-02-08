
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

class AccountConflict(AuthError):
    def __init__(self):
        AuthError.__init__(self, "Logins to different accounts can not be joined")

def normalize_email(email):
    if email:
        try:
            email_name, domain_part = email.strip().rsplit('@', 1)
        except ValueError:
            pass
        else:
            email = '@'.join([email_name, domain_part.lower()])
    return email

class CelLogin(object):
    def __init__(self, registry_store, loginid):
        self._store = registry_store
        self._loginid = loginid
        self._login = self._store.get_login(loginid)

    @property
    def account(self):
        return self._login.account

    @property
    def address(self):
        return self._login.address

    @property
    def confirmed(self):
        return self._login.confirmed

    def must_join_account(self):
        if self.account:
            return False
        return self.address and not self._store.is_free_address(self.address)

    def confirmation_required(self):
        if self.address and not self.confirmed:
            if self._store.assigned_account(self.address):
                return True
        return False

    def can_create_account(self):
        if self.account:
            return False
        return self.address and self._store.is_free_address(self.address)

    def create_account(self):
        account = self._store.create_account(self._loginid)
        assert account
        if self.address and self._store.is_free_address(self.address):
            self._store.assign(self.address, account)

class CelRegistry(object):
    def __init__(self, registry_store, mailer):
        self._store = registry_store
        self._mailer = mailer

    def get_login(self, loginid):
        assert loginid
        return CelLogin(self._store, loginid)

    def _equiv_loginids(self, loginid):
        if not loginid:
            return []
        account = self._store.account(loginid)
        return self._store.loginids(account) if account else [loginid]

    def _send_code(self, address):
        # os.urandom(5) will produce about 1 trillion possibilities
        code = b32encode(os.urandom(5))
        self._store.save_confirmation_code(code, address)
        self._mailer.send_code(code, address)

    def remind_pending_claim(self, loginid):
        login = self.get_login(loginid)
        if login.address:
            if login.account and not self._store.is_free_address(login.address):
                # either loginid and it's address are assigned to the same account
                # or they both point to different accounts
                # in either case, there is no point in sending a confirmation code
                return
            self._send_code(login.address)

    def _handle_openid(self, openid_case):
        new_loginid = self._store.note_openid(openid_case)
        address = normalize_email(openid_case.email)
        if address:
            self._store.set_address(new_loginid, address)
        return new_loginid

    def _join_logins(self, loginid, new_loginid):
        """
        Raises:
            AccountConflict
        """
        account = self._store.account(loginid)
        new_account = self._store.account(new_loginid)
        if account and new_account:
            raise AccountConflict
        if account and new_loginid:
            self._store.set_account(new_loginid, account)
        if new_account and loginid:
            self._store.set_account(loginid, new_account)

    def _handle_confirmation(self, code, loginid):
        registry = self._store
        address = registry.confirm_email(loginid, code)
        if not address:
            raise InvalidConfirmationCode
        account = self._store.account(loginid)
        if account:
            if not registry.add_address(account, address):
                raise AddressAccountConflict
        else:
            account = registry.assigned_account(address)
            if account:
                registry.set_account(loginid, account)

def make_auth_gate(registry_store, mailer, session_store):
        registry = CelRegistry(registry_store, mailer)
        session = CelSession(session_store)
        return AuthGate(registry, session)

class AuthGate():
    def __init__(self, cel_registry, cel_session):
        self._registry = cel_registry
        self._session = cel_session

    @property
    def loginid(self):
        return self._session.loginid

    @property
    def account(self):
        return self._registry.get_login(self.loginid).account if self.loginid else None

    @property
    def _logins(self):
        return map(self._registry.get_login, self._registry._equiv_loginids(self.loginid))

    def addresses(self):
        return list(set([ l.address for l in self._logins ]))

    def addresses_pending(self):
        return list(set([ l.address for l in self._logins if not l.confirmed ]))

    def addresses_confirmed(self):
        return list(set([ l.address for l in self._logins if l.confirmed ]))

    def must_join_account(self):
        if not self.loginid:
            return False
        return self._registry.get_login(self.loginid).must_join_account()

    def login(self, openid_case):
        """
        Raises:
            AccountConflict
        """
        new_loginid = self._registry._handle_openid(openid_case)
        self._registry._join_logins(self.loginid, new_loginid)
        self._registry.remind_pending_claim(new_loginid)
        self._session.set_loginid(new_loginid)

    def logout(self):
        self._session.clear()

    def claim(self, email_address):
        address = normalize_email(email_address)
        self._registry._send_code(address)

    def confirmation_required(self):
        if not self.loginid:
            return False
        return self._registry.get_login(self.loginid).confirmation_required()

    def confirm_email(self, code):
        """Register that login is confirming email confirmation code.
        Raises:
            InvalidConfirmationCode
            AddressAccountConflict: Email address is already assigned to
                another acccount.
        """
        self._registry._handle_confirmation(code, self.loginid)
        self._session.account_update()

    def can_create_account(self):
        if not self.loginid:
            return False
        return self._registry.get_login(self.loginid).can_create_account()

    def create_account(self):
        if not self.loginid:
            raise NotLoggedInError
        if self.account:
            raise AccountAlreadyExists
        if not self.can_create_account():
            raise AuthError("Account can not be created") 
        self._registry.get_login(self.loginid).create_account()
        self._session.account_update()

