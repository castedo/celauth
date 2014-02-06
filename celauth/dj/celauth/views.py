from django.shortcuts import render
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.urlresolvers import reverse
from django.utils.module_loading import import_by_path
from django.http import HttpResponse, HttpResponseRedirect
import urllib
from django import forms
from openid.consumer.discover import DiscoveryFailure
from celauth import OpenIDCase
from celauth.session import CelSession
from celauth.core import AuthGate, InvalidConfirmationCode, AddressAccountConflict
from celauth.providers import OPENID_PROVIDERS, facade
from celauth.dj.celauth import Mailer
from celauth.dj.celauth.models import DjangoCelRegistry

REDIRECT_FIELD_NAME = 'next'
LOGIN_BUTTON_NAME = 'login'
assert REDIRECT_FIELD_NAME != LOGIN_BUTTON_NAME


def get_auth_gate(request):
    AccountManager = import_by_path(settings.CEL_ACCOUNTANT)
    accounts = AccountManager()
    mailer = Mailer(request, 'celauth:confirm_email')
    SessionStore = import_by_path(settings.CEL_SESSION_STORE)
    return AuthGate(DjangoCelRegistry(accounts), SessionStore(request), mailer)


@require_http_methods(["GET", "POST"])
def default_view(request):
    gate = get_auth_gate(request)
    vals = {
        'gate': gate,
    }
    return render(request, 'celauth/default_view.html', vals)


@require_http_methods(["GET", "POST"])
def login(request):
    return login_response(request, get_auth_gate(request))

def login_response(request, gate):
    if not gate.loginid:
        return choose_openid_response(request, gate)

    if not gate.addresses():
        return enter_address_response(request, gate)

    if gate.confirmation_required():
        return enter_code_response(request, gate)

    if gate.addresses_joinable():
        return choose_openid_response(request, gate)

    if not gate.account:
        assert gate.can_create_account()
        vals = {
            'gate': gate,
            'next_name': REDIRECT_FIELD_NAME,
            'next_url': request.REQUEST.get(REDIRECT_FIELD_NAME, None),
        }
        return render(request, 'celauth/new_account.html', vals)

    return final_redirect(request)

class OpenIDLoginForm(forms.Form):
    openid_identifier = forms.URLField(
        required=True,
        label='',
        widget=forms.TextInput(attrs={'size':'64'}),
    )

def provider_buttons_iteritems():
    button_names = OPENID_PROVIDERS.ids(LOGIN_BUTTON_NAME + '-')
    return zip(button_names, OPENID_PROVIDERS.texts())

def choose_openid_response(request, gate):
    final_url = request.REQUEST.get(REDIRECT_FIELD_NAME, None)
    openid_form = None
    if request.method == 'POST':
        button_urls = OPENID_PROVIDERS.urls_by_id(LOGIN_BUTTON_NAME + '-')
        for button_name, openid_url in button_urls.iteritems():
          if button_name in request.POST:
              return initial_response(request, openid_url, final_url)

        if LOGIN_BUTTON_NAME in request.POST:
            # OpenID field should have been filled
            openid_form = OpenIDLoginForm(request.POST)
        else:
            openid_form = OpenIDLoginForm()

    if openid_form and openid_form.is_valid():
        openid_url = openid_form.cleaned_data['openid_identifier']
        return initial_response(request, openid_url, final_url)

    vals = {
        'gate': gate,
        'choices': provider_buttons_iteritems(),
        'openid_url_field': openid_form,
        'login_button_name': LOGIN_BUTTON_NAME,
        'next_name': REDIRECT_FIELD_NAME,
        'next_url': final_url,
    }
    if gate.addresses_joinable():
        return render(request, 'celauth/join_account.html', vals)
    else:
        return render(request, 'celauth/login.html', vals)

def initial_response(request, openid_url, final_url):
    try:
        return_url = request.build_absolute_uri(reverse('celauth:login_return'))
        if final_url and len(final_url) > 0:
            query_params = {REDIRECT_FIELD_NAME: final_url}
            return_url += '?' + urllib.urlencode(query_params)
        redir = facade.initial_response(request, openid_url, return_url)
        if redir.startswith('http'):
            return HttpResponseRedirect(redir)
        else:
            return HttpResponse(redir, content_type='text/html')
    except DiscoveryFailure, ex:
        return failure(request, 'OpenID Discovery Failure', ex)

def final_redirect(request):
    final_url = request.REQUEST.get(REDIRECT_FIELD_NAME,
                                    settings.LOGIN_REDIRECT_URL)
    #TODO verify final_url
    return HttpResponseRedirect(final_url)

@csrf_exempt
def login_return(request):
    case = facade.make_case(request)
    #TODO hacky return type error handling
    if not isinstance(case, OpenIDCase):
        return failure(request, str(case))
    auth = get_auth_gate(request)
    auth.login(case)
    return login_response(request, auth)


@require_http_methods(["POST"])
def create_account(request):
    auth = get_auth_gate(request)
    assert auth.loginid
    assert auth.can_create_account()
    auth.create_account()
    assert auth.account
    return final_redirect(request)


class EnterAddressForm(forms.Form):
    address = forms.EmailField(required=True, label='Your email address')

@require_http_methods(["GET", "POST"])
def enter_address(request):
    post_data = request.POST if request.method == 'POST' else None
    return enter_address_response(request, get_auth_gate(request), post_data)

def enter_address_response(request, gate, post_data = None):
    if post_data:
        form = EnterAddressForm(post_data)
    else:
        form = EnterAddressForm()
    if not form.is_valid():
        vals = {
            'gate': gate,
            'fields': form,
            'next_name': REDIRECT_FIELD_NAME,
            'next_url': request.REQUEST.get(REDIRECT_FIELD_NAME, None),
        }
        return render(request, 'celauth/enter_address.html', vals)

    gate.claim(form.cleaned_data['address'])
    return enter_code_response(request, gate, check_email_msg=True)

@require_http_methods(["GET", "POST"])
def confirm_email(request, confirmation_code):
    gate = get_auth_gate(request)
    if not gate.loginid:
        return enter_code_response(request, gate)
    if not confirmation_code:
        confirmation_code = request.REQUEST.get('code', None)
    try:
        gate.confirm_email(confirmation_code)
        return login_response(request, gate)
    except InvalidConfirmationCode:
        return enter_code_response(request, gate, confirmation_code)
    except AddressAccountConflict as ex:
        return failure(request,
                       "Email address is already assigned to another acccount.",
                       ex)

class EnterCodeForm(forms.Form):
    code = forms.CharField(required=True, label='Confirmation code')

def enter_code_response(request, gate, invalid_confirmation_code=None, check_email_msg=False):
    if invalid_confirmation_code:
        form = EnterCodeForm({'code': invalid_confirmation_code})
        form.errors['code'] = "'%s' is invalid or expired" % invalid_confirmation_code 
    else:
        form = EnterCodeForm()
    vals = {
        'gate': gate,
        'form': form,
        'choices': provider_buttons_iteritems(),
        'check_email_msg': check_email_msg,
        'openid_url_field': None,
        'login_button_name': LOGIN_BUTTON_NAME,
        'next_name': REDIRECT_FIELD_NAME,
        'next_url': request.REQUEST.get(REDIRECT_FIELD_NAME, None),
    }
    return render(request, 'celauth/enter_code.html', vals)


@require_http_methods(["POST"])
def disclaim(request):
    gate = get_auth_gate(request)
    gate.disclaim_pending()
    return login_response(request, gate)


@require_http_methods(["POST"])
def logout(request):
    auth = get_auth_gate(request)
    auth.logout()
    return default_view(request)


def failure(request, message, exception=None):
    gate = get_auth_gate(request)
    vals = {
        'gate': gate,
        'message': str(message),
    }
    if settings.DEBUG and exception:
        vals['exception'] = str(exception)
    return render(request, 'celauth/failure.html', vals, status=403)

