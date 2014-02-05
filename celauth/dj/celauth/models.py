
from datetime import datetime, timedelta
from django.db import models
from celauth.session import CelRegistryBase

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
    claims = models.ManyToManyField(EmailAddress, through='EmailClaim')

    def __unicode__(self):
        return self.display_id

class EmailClaim(models.Model):
    openid = models.ForeignKey(OpenID)
    email = models.ForeignKey(EmailAddress)
    credible = models.BooleanField(default=False)
    confirmed = models.BooleanField(default=False)

class ConfirmationCode(models.Model):
    email = models.ForeignKey(EmailAddress)
    code = models.CharField(unique=True, max_length=64)
    expiration = models.DateTimeField()

class DjangoCelRegistry(CelRegistryBase):
    def __init__(self, accountant):
        self._accountant = accountant

    def loginids(self, account):
        return OpenID.objects.filter(account=account)

    def account(self, loginid):
        return loginid.account if loginid else None

    def addresses(self, loginid):
        #TODO order addresses with ID's email (if known) first, then by date
        claims = EmailClaim.objects.filter(openid=loginid)
        return [c.email.address for c in claims]

    def addresses_not_confirmed(self, loginid):
        claims = EmailClaim.objects.filter(openid=loginid, confirmed=False)
        return set([c.email.address for c in claims])

    def addresses_confirmed(self, loginid):
        claims = EmailClaim.objects.filter(openid=loginid, confirmed=True)
        return set([c.email.address for c in claims])

    def addresses_credible(self, loginid):
        claims = EmailClaim.objects.filter(openid=loginid, credible=True)
        return set([c.email.address for c in claims])

    def is_confirmed_claim(self, loginid, address):
        qset = EmailClaim.objects.filter(openid=loginid,
                                         email__address=address,
                                         confirmed=True)
        return qset.exists()

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

    def claim(self, loginid, email_address, credible):
        assert loginid
        email = self._get_email_address(email_address)
        claim = self._get_claim(loginid, email)
        if credible:
            claim.credible = True 
            claim.save()

    def disclaim(self, loginid, email_address):
        assert loginid
        email = self._get_email_address(email_address)
        claim = self._get_claim(loginid, email)
        claim.delete()

    def save_confirmation_code(self, code, email_address):
        expire = datetime.utcnow() + timedelta(hours=12)
        ConfirmationCode.objects.create(email=self._get_email_address(email_address),
                                        code=code,
                                        expiration=expire)

    def confirm_email(self, loginid, code):
        try:
            rec = ConfirmationCode.objects.get(code=code)
            if datetime.utcnow() > rec.expiration:
                return False
            claim = self._get_claim(loginid, rec.email)
            claim.credible = True
            claim.confirmed = True
            claim.save()
            return claim.email.address
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

    def remove_address(self, account, address):
        email = self._get_email_address(address)
        if account == email.account:
            email.account = None

    def set_account(self, loginid, account):
        loginid.account = account
        loginid.save()

    def create_account(self, openid):
        openid.account = self._accountant.create_account(self.addresses(openid))
        openid.save()
        return openid.account

    def has_incredible_claims(self, openid):
        return openid.claims.filter(emailclaim__credible=False).exists()

    def _get_email_address(self, address):
        norm = self._normalize_email(address)
        ret, new = EmailAddress.objects.get_or_create(pk=norm)
        return ret

    def _get_claim(self, openid, address_rec):
        ret, new = EmailClaim.objects.get_or_create(openid=openid,
                                                    email=address_rec)
        return ret

