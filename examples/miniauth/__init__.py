from models import Account

class Accountant(object):
    def assigned_account(self, email_address):
        return None

    def create_account(self, email_address):
        account = Account.objects.create()
        return account.id

