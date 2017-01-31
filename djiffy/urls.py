from django.conf.urls import url

from djiffy import views

urlpatterns = [
    url(r'^$', views.BookList.as_view(), name='list'),
    url(r'^(?P<id>[^/]+)/$', views.BookDetail.as_view(), name='book'),
    url(r'^(?P<book_id>[^/]+)/pages/(?P<id>[^/]+)/$',
        views.PageDetail.as_view(), name='page'),
]
