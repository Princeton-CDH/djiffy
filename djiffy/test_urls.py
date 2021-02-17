"""Test URL configuration for djiffy
"""
from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView

from djiffy import urls as djiffy_urls


urlpatterns = [
    path('', RedirectView.as_view(pattern_name='admin:index'),
         name='site-index'),
    path('iiif/', include(djiffy_urls, namespace='djiffy')),
    path('admin/', admin.site.urls),
]
