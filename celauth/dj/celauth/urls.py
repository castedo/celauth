from django.conf.urls import patterns, include, url
import views

urlpatterns = patterns('',
    url(r'^$', views.default_view, name='default'),
    url(r'^login$', views.login, name='login'),
    url(r'^login_return$', views.login_return, name='login_return'),
    url(r'^create_account$', views.create_account, name='create_account'),
    url(r'^enter_address$', views.enter_address, name='enter_address'),
    url(r'^confirm_email/(\w*)$', views.confirm_email, name='confirm_email'),
    url(r'^logout$', views.logout, name='logout'),
)

