
import urlparse
from openid.consumer import consumer
from openid.extensions import sreg, ax
from celauth import OpenIDCase
from celauth.dj.celauth.openid_store import DjangoOpenIDStore

class OpenIDChoices(object):
    def __init__(self, data):
        self.data = data
    def ids(self, id_prefix=''):
        return [id_prefix + x[0] for x in self.data]
    def texts(self):
        return [x[1] for x in self.data]
    def urls_by_id(self, id_prefix=''):
        return dict( (id_prefix + x[0], x[2]) for x in self.data )
    def credible_email(self, claimed_id, email_address):
        netloc = urlparse.urlparse(claimed_id).netloc
        for x in self.data:
            provider = x[2]
            if netloc == urlparse.urlparse(provider).netloc:
                return True
        return False

OPENID_PROVIDERS = OpenIDChoices([
  ('google',        'Google',        'https://www.google.com/accounts/o8/id'),
  ('yahoo',         'Yahoo!',        'https://me.yahoo.com/'),
  ('aol',           'AOL',           'https://openid.aol.com/'),
  ('stackexchange', 'StackExchange', 'https://openid.stackexchange.com/'),
  ('launchpad',     'Launchpad',     'https://login.launchpad.net/'),
  ('intuit',        'Intuit',        'https://openid.intuit.com/openid/xrds'),
])

class TestOpenIDHelper:
    def __init__(self, real):
        self.case = None
        self.real = real

    def initial_response(self, request, user_url, return_url):
        urlp = urlparse.urlparse(user_url)
        if urlp.netloc not in ('example.com', 'example.org', 'example.net'):
            return self.real.initial_response(request, user_url, return_url)
        if urlp.fragment:
            email = urlp.fragment + '@' + urlp.netloc
            urlp = list(urlp)
            urlp[5] = '' # remove fragment
            user_url = urlparse.ParseResult(*urlp).geturl() 
        else:
            email = None
        credible = (urlparse.urlparse(user_url).netloc == 'example.com')
        self.case = OpenIDCase(user_url, user_url, email, credible)
        return return_url

    def make_case(self, request):
        if not self.case:
            return self.real.make_case(request)
        ret = self.case
        self.case = None
        return ret

EMAIL_AX_TYPE_URI = 'http://axschema.org/contact/email'

class LiveOpenIDHelper:

    def _openid_consumer(self, request):
        openid_store = DjangoOpenIDStore()
        return consumer.Consumer(request.session, openid_store)

    def initial_response(self, request, user_url, return_url):
        oc = self._openid_consumer(request)
        openid_request = oc.begin(user_url)

        if openid_request.endpoint.supportsType(ax.AXMessage.ns_uri):
            ax_request = ax.FetchRequest()
            ax_request.add(ax.AttrInfo(EMAIL_AX_TYPE_URI,
                                       alias='email',
                                       required=True,
                                      ))
            openid_request.addExtension(ax_request)
        else: 
            sreg_request = sreg.SRegRequest(required=['email'],
                                            optional=[],
                                           )
            openid_request.addExtension(sreg_request)

        realm = request.build_absolute_uri('/')

        if openid_request.shouldSendRedirect():
            return openid_request.redirectURL(realm, return_url)
        else:
            return openid_request.htmlMarkup(realm, return_url)

    def make_case(self, request):
        oc = self._openid_consumer(request)
        current_url = request.build_absolute_uri()
        query_params = dict(request.REQUEST.items())
        response = oc.complete(query_params, current_url)
        if response.status == consumer.CANCEL:
            return "OpenID sign in cancelled"
        if response.status == consumer.SUCCESS:
            email = None
            sreg_response = sreg.SRegResponse.fromSuccessResponse(response)
            if sreg_response:
                email = sreg_response.get('email', None)
            ax_response = ax.FetchResponse.fromSuccessResponse(response)
            if ax_response:
                email = ax_response.getSingle(EMAIL_AX_TYPE_URI, email)

            credible = OPENID_PROVIDERS.credible_email(response.identity_url, email)
            return OpenIDCase(response.identity_url, response.getDisplayIdentifier(), email, credible)
        return response.message or "Internal openid library error" #should throw exception


facade = LiveOpenIDHelper()

def enable_test_openids():
    global facade
    facade = TestOpenIDHelper(facade)

