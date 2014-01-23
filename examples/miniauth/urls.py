from django.conf.urls import patterns, include, url
import celauth

urlpatterns = patterns('',
    url(r'^openid/', include('celauth.dj.celauth.urls', namespace='celauth')),
)
