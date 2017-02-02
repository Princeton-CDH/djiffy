from django.views.generic import DetailView, ListView

from .models import IfBook, IfPage


class BookList(ListView):
    model = IfBook
    template_name = 'djiffy/book_list.html'
    context_object_name = 'books'


class BookDetail(DetailView):
    model = IfBook
    template_name = 'djiffy/book_detail.html'
    context_object_name = 'book'

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = IfBook.objects.all()
        return queryset.get(short_id=self.kwargs['id'])


class PageDetail(DetailView):
    model = IfPage
    template_name = 'djiffy/page_detail.html'
    context_object_name = 'page'

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = IfPage.objects.all()
        return queryset.get(short_id=self.kwargs['id'],
            book__short_id=self.kwargs['book_id'])
