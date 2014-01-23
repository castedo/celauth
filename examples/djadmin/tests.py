from django.utils import unittest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core import mail

class DjadminTest(TestCase):
    def get_confirmation_code(self):
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Confirmation Code')
        return mail.outbox[0].body.split('\n')[-2] #code on last line

    def test_super_user_credible_email(self):
        self._test_super_user('duper', "com")

    def test_super_user_incredible_email(self):
        self._test_super_user('super', "org")

    def _test_super_user(self, name, tld):
        UserModel = get_user_model()
        email = '%s@example.%s' % (name, tld)
        UserModel.objects.create_superuser(name, email, None)

        response = self.client.get("/admin/")
        self.assertRedirects(response, "http://testserver/openid/login?next=/admin/")

        response = self.client.get("/admin/", follow=True)
        self.assertContains(response, "Log in")

        data = {
            'openid_identifier':'http://example.%s/%s#%s' % (tld, name, name),
            'login':'Log in',
            'next':'/admin/',
        }
        response = self.client.post("/openid/login", data, follow=True, HTTP_HOST='testserver')
        self.assertContains(response, "confirmation code")

        data = {
            'code':self.get_confirmation_code(),
            'next':'/admin/',
        }
        response = self.client.post("/openid/confirm_email/", data, follow=True, HTTP_HOST='testserver')
        self.assertContains(response, "Site administration")

