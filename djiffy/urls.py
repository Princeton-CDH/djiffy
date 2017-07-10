from django.conf.urls import url

from djiffy import views

urlpatterns = [
    url(r'^$', views.ManifestList.as_view(), name='list'),
    url(r'^(?P<id>[^/]+)/$', views.ManifestDetail.as_view(), name='manifest'),
    url(r'^(?P<manifest_id>[^/]+)/canvases/(?P<id>[^/]+)/$',
        views.CanvasDetail.as_view(), name='canvas'),
    url(r'^canvas/autocomplete/$', views.CanvasAutocomplete.as_view(),
        name='canvas-autocomplete'),
]
