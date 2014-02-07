from django.utils import unittest
from django.utils.module_loading import import_by_path
from django.conf import settings
from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.core import mail
from celauth.tests import CelTestCase, FakeMailer, TestSessionStore
from celauth import providers
from celauth.core import make_auth_gate
from celauth.dj.celauth.models import DjangoCelModelStore, delete_registry_data

providers.enable_test_openids()

class DjModelStoreTestCase(CelTestCase):
    def setUp(self):
        AccountManager = import_by_path(settings.CEL_ACCOUNTANT)
        self.store = DjangoCelModelStore(AccountManager())
        self.gate = make_auth_gate(self.store, FakeMailer(), TestSessionStore())

    def tearDown(self):
        self.store = None
        self.gate = None
        delete_registry_data()

class CelDjTestCase(TestCase):
    def login_as(self, tld, id, email_id, next_url=None):
        openid = 'https://example.%s/%s' % (tld, id)
        if email_id:
            openid += '#' + email_id
        data = {
            'openid_identifier':openid,
            'login':'Log in',
        }
        if next_url:
            data['next'] = next_url
        path = reverse('celauth:login')
        response = self.client.post(path, data, follow=True, HTTP_HOST='testserver')
        return response

    def new_account(self, tld, id, email_id):
        next_url = '/there'
        response = self.login_as(tld, id, email_id, next_url)
        self.assertContains(response, "Create new account")
        data = {}
        data['next'] = next_url
        path = reverse('celauth:create_account')
        response = self.client.post(path, data, HTTP_HOST='testserver')
        self.assertRedirects(response, next_url, target_status_code=404)
        response = self.follow_email_confirmation_link()
        address = '%s@example.%s' % (email_id, tld)
        self.assertContains(response, address)

    def logout(self):
        response = self.client.post(reverse('celauth:logout'))
        response = self.client.get(reverse('celauth:default'))
        self.assertContains(response, "Log in")
        return response

    def follow_email_confirmation_link(self):
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Confirmation Code')
        url = mail.outbox[0].body.split('\n')[1] #url on 2nd line
        code = mail.outbox[0].body.split('\n')[-1] #code on last line
        return self.client.get(url, follow=True)


class BasicTest(CelDjTestCase):
    def test_login_provider_text(self):
        response = self.client.get(reverse('celauth:login'))
        self.assertContains(response, "Log in")
        self.assertContains(response, "Google")
        self.assertContains(response, "Yahoo!")
        self.assertContains(response, "Any OpenID")

    def test_full_cycle(self):
        path = reverse('celauth:login') + '?next=/there'
        response = self.client.get(path)
        html = "<input name='next' type='hidden' value='/there' />"
        self.assertContains(response, html, html=True)

        response = self.client.post(reverse('celauth:login'))
        self.assertContains(response, "OpenID")

        self.new_account('com', 'myid', 'mybox')

        response = self.client.get(reverse('celauth:default'))
        self.assertContains(response, "Log out")
        self.assertContains(response, "mybox@example.com")

        self.logout()

    def test_confirmation(self):
        response = self.login_as('org', 'dude', 'dude', '/there')
        self.assertContains(response, "confirmation code")
        self.assertContains(response, "dude@example.org")
        response = self.follow_email_confirmation_link()
        self.assertContains(response, "Create new account")

        data = { 'next':'/there' }
        path = reverse('celauth:create_account')
        response = self.client.post(path, data, HTTP_HOST='testserver')
        self.assertRedirects(response, "/there", target_status_code=404)

        response = self.client.get(reverse('celauth:default'))
        self.assertContains(response, "dude@example.org")

        self.logout()

class ExistingAccountTests(CelDjTestCase):
        def setUp(self):
            self.new_account('com', 'myid', 'mybox')
            self.logout()

        def test_join_account(self):
            final_url = '/there'
            response = self.login_as('com', 'myid2', 'mybox', final_url)
            self.assertContains(response, "existing account")
            response = self.login_as('com', 'myid', 'mybox', final_url)
            self.assertRedirects(response, final_url, target_status_code=404)
            self.logout()
            response = self.login_as('com', 'myid2', 'mybox', final_url)
            self.assertRedirects(response, final_url, target_status_code=404)

