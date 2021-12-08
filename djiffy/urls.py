from django.urls import path, re_path

from djiffy import views

app_name = 'djiffy'

urlpatterns = [
    path('', views.ManifestList.as_view(), name='list'),
    re_path(r'^(?P<id>[^/]+)/$', views.ManifestDetail.as_view(),
            name='manifest'),
    re_path(r'^(?P<manifest_id>[^/]+)/canvases/(?P<id>[^/]+)/$',
            views.CanvasDetail.as_view(), name='canvas'),
    path(r'canvas/autocomplete/', views.CanvasAutocomplete.as_view(),
         name='canvas-autocomplete'),
]
