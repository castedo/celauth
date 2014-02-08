
class CelSession(object):
    def __init__(self, session_store):
        self._store = session_store

    @property
    def loginid(self):
        """Get the current loginid"""
        return self._store.vals['loginid']

    @loginid.setter
    def loginid(self, value):
        """Set the current loginid"""
        self._store.vals['loginid'] = value
        self._store.update()

    def set_loginid(self, loginid):
        self.loginid = loginid

    @property
    def address(self):
        """Get the current confirmed email address"""
        return self._store.vals['address']

    @address.setter
    def address(self, value):
        """Set the current confirmed email address"""
        self._store.vals['address'] = value
        self._store.update()

    def clear(self):
        """Clear all session authentication state"""
        self.loginid = None
        self.address = None
        self._store.update()

    def account_update(self):
        self._store.update()

