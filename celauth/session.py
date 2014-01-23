
class CelSession(object):
    def __init__(self, session_store):
        self._store = session_store

    @property
    def loginid(self):
        """Get the current loginid"""
        loginids = self._store.loginids
        assert(len(loginids) in [0, 1, 2])
        return loginids[0] if loginids else None

    def set_loginid(self, loginid):
        """Set the current loginid"""
        del self._store.loginids[:]
        assert loginid
        if loginid:
            self._store.loginids.append(loginid)
        self._store.update()

    @property
    def temp_loginid(self):
        """Get the temporary loginid"""
        loginids = self._store.loginids
        assert(len(loginids) in [0, 1, 2])
        return loginids[1] if len(loginids) > 1 else None

    @loginid.setter
    def temp_loginid(self, value):
        """Set or clear the temporary loginid"""
        loginids = self._store.loginids
        assert(len(loginids) == 2)
        if len(loginids) <= 2:
            if value:
                loginids[1] = value
            else:
                del loginids[1]
            self._store.update()

    def clear(self):
        """Clear all session authentication state"""
        del self._store.loginids[:]
        self._store.update()

    def account_update(self):
        self._store.update()

class CelRegistryBase(object):

    @classmethod
    def _normalize_email(cls, email):
        email = email or ''
        try:
            email_name, domain_part = email.strip().rsplit('@', 1)
        except ValueError:
            pass
        else:
            email = '@'.join([email_name, domain_part.lower()])
        return email

