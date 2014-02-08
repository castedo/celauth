from celauth.providers import enable_test_openids
from django.conf import settings
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
import django.contrib.auth

if settings.DEBUG:
    enable_test_openids()

class Mailer:
    def __init__(self, request, viewname):
        if 'HTTP_HOST' in request.META:
            self.root = "https" if request.is_secure() else "http"
            self.root += "://" + request.META['HTTP_HOST']
        else:
            self.root = None
        self.viewname = viewname

    def send_code(self, code, address):
        vals = { 'code':code, 'url':None }
        if self.root:
            vals['url'] = self.root + reverse(self.viewname, args=[code])
        subject = render_to_string("celauth/confirm_email_subject.txt", vals)
        subject = str.join("", subject.splitlines())
        body = render_to_string("celauth/confirm_email_body.txt", vals)
        send_mail(subject, body, settings.CONFIRM_EMAIL_FROM, [address])

class DjangoCelSessionStore(object):

    def __init__(self, request):
        self.request = request

    @property
    def vals(self):
        self.request.session.setdefault('authgate', dict())
        return self.request.session['authgate']

    def update(self):
        self.request.session.save()

class DjangoAuthCelSessionStore(DjangoCelSessionStore):

    def __init__(self, request):
        DjangoCelSessionStore.__init__(self, request)

    def update(self):
        loginid = self.vals.get('loginid', None)
        user_id = loginid.account if loginid else None
        if self.request.user.is_authenticated():
            if user_id != self.request.user.id:
                django.contrib.auth.logout(self.request)
        if user_id and not self.request.user.is_authenticated():
            user = django.contrib.auth.authenticate(user_id=user_id)
            assert user
            django.contrib.auth.login(self.request, user)
        self.request.session.save()

