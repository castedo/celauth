from django.utils import unittest
from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.core import mail
from celauth import providers

providers.enable_test_openids()

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

    def new_account(self, tld, id, email_id, next_url=None):
        response = self.login_as(tld, id, email_id, next_url)
        self.assertContains(response, "Create new account")
        data = {}
        if next_url:
            data['next'] = next_url
        path = reverse('celauth:create_account')
        return self.client.post(path, data, HTTP_HOST='testserver')

    def logout(self):
        response = self.client.post(reverse('celauth:logout'))
        response = self.client.get(reverse('celauth:default'))
        self.assertContains(response, "Log in")
        return response

class BasicTest(CelDjTestCase):
    def test_login_provider_text(self):
        response = self.client.get("/openid/login")
        self.assertContains(response, "Log in")
        self.assertContains(response, "Google")
        self.assertContains(response, "Yahoo!")
        self.assertContains(response, "Any OpenID")

    def test_full_cycle(self):
        response = self.client.get("/openid/login?next=/there")
        html = "<input name='next' type='hidden' value='/there' />"
        self.assertContains(response, html, html=True)

        response = self.client.post("/openid/login")
        self.assertContains(response, "OpenID")

        response = self.new_account('com', 'myid', 'mybox', '/there')
        self.assertRedirects(response, "/there", target_status_code=404)

        response = self.client.get(reverse('celauth:default'))
        self.assertContains(response, "Log out")
        self.assertContains(response, "mybox@example.com")

        self.logout()

    def test_confirmation(self):
        response = self.login_as('org', 'dude', 'dude', '/there')
        self.assertContains(response, "confirmation code")
        self.assertContains(response, "dude@example.org")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Confirmation Code')

        url = mail.outbox[0].body.split('\n')[1] #url on 2nd line
        code = mail.outbox[0].body.split('\n')[-1] #code on last line
        response = self.client.get(url)
        self.assertContains(response, "Create new account")

        data = { 'next':'/there' }
        path = reverse('celauth:create_account')
        response = self.client.post(path, data, HTTP_HOST='testserver')
        self.assertRedirects(response, "/there", target_status_code=404)

        response = self.client.get("/openid/")
        self.assertContains(response, "dude@example.org")

        self.logout()

    def test_email_disclaim(self):
        response = self.login_as('org', 'dude', 'bad', '/there')
        self.assertContains(response, "confirmation code")
        self.assertContains(response, "bad@example.org")

        response = self.client.post(reverse('celauth:disclaim'))
        self.assertContains(response, "Enter your email address")

class ExistingAccountTests(CelDjTestCase):
        def setUp(self):
            self.new_account('com', 'myid', 'mybox', '/there')
            self.logout()

        def test_join_account(self):
            final_url = '/there'
            response = self.login_as('com', 'myid2', 'mybox', final_url)
            self.assertContains(response, "existing account")
            response = self.login_as('com', 'myid', 'mybox', final_url)
            self.assertRedirects(response, final_url, target_status_code=404)

