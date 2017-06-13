"""Test URL configuration for djiffy
"""
from django.conf.urls import url, include
from django.contrib import admin
from django.views.generic.base import RedirectView

from djiffy import urls as djiffy_urls


urlpatterns = [
    url(r'^$', RedirectView.as_view(pattern_name='admin:index'), name='site-index'),
    url(r'^iiif/', include(djiffy_urls, namespace='djiffy')),
    url(r'^admin/', admin.site.urls),
]

