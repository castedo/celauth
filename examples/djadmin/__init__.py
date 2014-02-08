import os
from binascii import hexlify
import django.contrib.auth
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import user_passes_test

def active_staff_required(function):
    def ensure_is_active_staff(user):
        if not user.is_authenticated():
            return False
        if user.is_active and user.is_staff:
            return True
        raise PermissionDenied
    return user_passes_test(ensure_is_active_staff)(function)

class DjangoUserManager():
    def assigned_account(self, email_address):
        UserModel = django.contrib.auth.get_user_model()
        try:
            user = UserModel.objects.get(username=email_address, is_active=True)
            return user.id
        except UserModel.DoesNotExist:
            users = UserModel.objects.filter(email=email_address, is_active=True)
            #TODO raise exception if multiple users
            return users[0].id if len(users) == 1 else None

    def create_account(self, email_address):
        assert email_address
        UserModel = django.contrib.auth.get_user_model()
        existing = UserModel.objects.filter(username=email_address)
        assert not existing
        existing = UserModel.objects.filter(email=email_address)
        assert not existing
        user = UserModel.objects.create_user(email_address, email_address)
        return user.id

class TrivialBackend:
    def authenticate(self, user_id=None, **kwargs):
        return self.get_user(user_id)

    def get_user(self, user_id):
        UserModel = django.contrib.auth.get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None

