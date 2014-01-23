
from collections import namedtuple

OpenIDCase = namedtuple('OpenIDCase', ['claimed_id',
                                       'display_id',
                                       'email',
                                       'credible'])

class TrivialAccountant(object):

    def __init__(self, ignore=None):
        self.account_count = 0

    def assigned_account(self, email_address):
        return None

    def create_account(self, email_address):
        self.account_count += 1
        return self.account_count

