
from datetime import datetime, timedelta
from django.db import models

def delete_registry_data():
    EmailAddress.objects.all().delete()
    OpenID.objects.all().delete()
    ConfirmationCode.objects.all().delete()

class OpenIDNonce(models.Model):
    server_url = models.URLField(max_length=255)
    timestamp  = models.IntegerField()
    salt       = models.CharField(max_length=40)

    def __unicode__(self):
        return u"OpenIDNonce: %i %s" % (self.timestamp, self.server_url)

class OpenIDAssociation(models.Model):
    server_url = models.URLField(db_index=True)
    handle     = models.CharField(max_length=255, db_index=True)
    secret     = models.TextField(max_length=255) # Stored base64 encoded
    issued     = models.IntegerField()
    lifetime   = models.IntegerField()
    assoc_type = models.TextField(max_length=64)

    def __unicode__(self):
        return u"OpenIDAssociation: %s %s" % (self.server_url, self.handle)

class EmailAddress(models.Model):
    address = models.EmailField(primary_key=True)
    account = models.PositiveIntegerField(blank=True, null=True, db_index=True)

    def __unicode__(self):
        return u"(%s, %s)" % (self.address, self.account)

class OpenID(models.Model):
    claimed_id = models.URLField(max_length=255, primary_key=True)
    display_id = models.URLField(max_length=255)
    account = models.PositiveIntegerField(blank=True, null=True, db_index=True)
    email = models.ForeignKey(EmailAddress, blank=True, null=True)
    confirmed = models.BooleanField(default=False)

    @property
    def address(self):
        return self.email.address if self.email else None

    def __unicode__(self):
        return self.display_id

class ConfirmationCode(models.Model):
    email = models.ForeignKey(EmailAddress)
    code = models.CharField(unique=True, max_length=64)
    expiration = models.DateTimeField()

class DjangoCelModelStore(object):
    def __init__(self, accountant):
        self._accountant = accountant

    def all_uris_by_account(self):
        """For testing"""
        inverse = dict()
        for openid in OpenID.objects.all():
            if openid.account:
                uris = inverse.setdefault(openid.account, set())
                uris.add(openid.claimed_id)
        for email in EmailAddress.objects.all():
            if email.account:
                uris = inverse.setdefault(email.account, set())
                uris.add('mailto:' + email.address)
        return set(map(frozenset,inverse.values()))
    
    def loginids(self, account):
        return OpenID.objects.filter(account=account)

    def get_login(self, loginid):
        assert loginid
        return loginid

    def account(self, loginid):
        return loginid.account if loginid else None

    def addresses(self, loginid):
        assert loginid
        email = loginid.email
        return [email.address] if email else []

    def addresses_confirmed(self, loginid):
        assert loginid
        return [loginid.email.address] if loginid.email and loginid.confirmed else []

    def is_free_address(self, address):
        try:
            email = EmailAddress.objects.get(address=address)
            return email.account is None
        except EmailAddress.DoesNotExist:
            return True

    def assign(self, address, account):
        free = EmailAddress.objects.get(address=address, account=None)
        free.account = account
        free.save()

    def note_openid(self, openid_case):
        ret, new = OpenID.objects.get_or_create(
                                    claimed_id = openid_case.claimed_id,
                                    display_id = openid_case.display_id)
        return ret

    def get_address(self, loginid):
        assert loginid
        return loginid.email.address if loginid and loginid.email else None

    def set_address(self, loginid, email_address):
        assert loginid
        email = self._get_email_address(email_address)
        loginid.email = email
        loginid.save()

    def save_confirmation_code(self, code, email_address):
        expire = datetime.utcnow() + timedelta(hours=12)
        ConfirmationCode.objects.create(email=self._get_email_address(email_address),
                                        code=code,
                                        expiration=expire)

    def confirm_email(self, loginid, code):
        try:
            assert loginid
            rec = ConfirmationCode.objects.get(code=code)
            if datetime.utcnow() > rec.expiration:
                return False
            assert loginid.email == rec.email
            if loginid.email == rec.email:
                loginid.confirmed = True
                loginid.save()
                return loginid.email.address
            else:
                return None
        except ConfirmationCode.DoesNotExist:
            return None

    def assigned_account(self, address):
        email = self._get_email_address(address)
        if not email.account:
            email.account = self._accountant.assigned_account(address)
            email.save()
        if email.account:
            if OpenID.objects.filter(account=email.account).exists():
                return None
        return email.account

    def add_address(self, account, address):
        email = self._get_email_address(address)
        if email.account is None:
            email.account = account
            email.save()
            return True
        return account == email.account

    def set_account(self, loginid, account):
        loginid.account = account
        loginid.save()

    def create_account(self, loginid):
        assert loginid
        if isinstance(loginid, str) and loginid.startswith('mailto:'):
            address = loginid[7:]
            account = self._accountant.create_account([address])
            self.add_address(account, address)
            return account
        openid = loginid
        openid.account = self._accountant.create_account(self.addresses(openid))
        openid.save()
        return openid.account

    def _get_email_address(self, address):
        ret, new = EmailAddress.objects.get_or_create(pk=address)
        return ret

