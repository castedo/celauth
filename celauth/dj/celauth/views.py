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
from celauth.core import AuthGate
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
    auth = get_auth_gate(request)
    vals = {
        'account': auth.account,
        'addresses_confirmed': list(auth.addresses_confirmed()),
        'addresses_pending': list(auth.addresses_pending()),
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
            'addresses': gate.addresses(),
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

def choose_openid_response(request, gate):
    final_url = request.REQUEST.get(REDIRECT_FIELD_NAME, None)
    openid_form = None
    providers = OPENID_PROVIDERS
    name_prefix = LOGIN_BUTTON_NAME + '-'
    button_names = [name_prefix + s for s in providers.ids()]
    if request.method == 'POST':
        for i in range(providers.num()):
          if button_names[i] in request.POST:
              openid_url = providers.url(i)
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
        'choices': zip(button_names, providers.texts()),
        'openid_url_field': openid_form,
        'login_button_name': LOGIN_BUTTON_NAME,
        'next_name': REDIRECT_FIELD_NAME,
        'next_url': final_url,
        'addresses': gate.addresses(),
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
        return failure('OpenID Discovery Failure', ex)

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
    auth.new_auth(case)
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
            'fields': form,
            'next_name': REDIRECT_FIELD_NAME,
            'next_url': request.REQUEST.get(REDIRECT_FIELD_NAME, None),
        }
        return render(request, 'celauth/enter_address.html', vals)

    address = form.cleaned_data['address']
    auth.claim(address)
    return enter_code_response(request, auth)

@require_http_methods(["GET", "POST"])
def confirm_email(request, confirmation_code):
    gate = get_auth_gate(request)
    if not gate.loginid:
        return choose_openid_response(request, gate)
    if not confirmation_code:
        confirmation_code = request.REQUEST.get('code', None)
    if gate.confirm_email(confirmation_code):
        return login_response(request, gate)
    else:
        return enter_code_response(request, gate, confirmation_code)

class EnterCodeForm(forms.Form):
    code = forms.CharField(required=True, label='Confirmation code')

def enter_code_response(request, gate, invalid_confirmation_code=None):
    if invalid_confirmation_code:
        form = EnterCodeForm({'code': invalid_confirmation_code})
        form.errors['code'] = ["invalid or expired"]
    else:
        form = EnterCodeForm()
    vals = {
        'fields': form,
        'addresses_pending': list(gate.addresses_pending()),
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
    if not settings.DEBUG:
        exception = None
    return render(request,
                  'celauth/failure.html',
                  dict(message=str(message), exception=str(exception)),
                  status=403
                 )

