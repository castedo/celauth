from django.conf.urls import patterns, include, url
from djadmin import active_staff_required
import celauth

from django.contrib import admin
admin.autodiscover()

admin.site.login = active_staff_required(admin.site.login)

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^openid/', include('celauth.dj.celauth.urls', namespace='celauth')),
)
