from dal import autocomplete
from django.db.models import Q
from django.http import Http404
from django.views.generic import DetailView, ListView

from djiffy.models import Canvas, Manifest


class ManifestList(ListView):
    '''List view for :class:`~djiffy.models.Manifest`.  Rendered with
    djiffy/manifest_list.html template.
    '''
    model = Manifest
    template_name = 'djiffy/manifest_list.html'
    context_object_name = 'manifests'


class ManifestDetail(DetailView):
    '''Detail view for a single :class:`~djiffy.models.Manifest`.
    Rendered with  djiffy/manifest_detail.html template.
    '''
    model = Manifest
    template_name = 'djiffy/manifest_detail.html'
    context_object_name = 'manifest'

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = Manifest.objects.all()

        try:
            return queryset.get(short_id=self.kwargs['id'])
        except queryset.model.DoesNotExist:
            raise Http404("No manifest found with id %(id)s" % self.kwargs)


class CanvasDetail(DetailView):
    '''Detail view for a single :class:`~djiffy.models.Canvas`.
    Rendered with  djiffy/canvast_detail.html template.
    '''
    model = Canvas
    template_name = 'djiffy/canvas_detail.html'
    context_object_name = 'canvas'

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = Canvas.objects.all()

        try:
            return queryset.get(short_id=self.kwargs['id'],
                manifest__short_id=self.kwargs['manifest_id'])
        except queryset.model.DoesNotExist:
            raise Http404("No canvas found with id %(id)s and manifest %(manifest_id)s" % \
                self.kwargs)


class CanvasAutocomplete(autocomplete.Select2QuerySetView):
    '''Canvas autocomplete view, e.g. for admin interface lookup'''
    def get_queryset(self):
        return Canvas.objects.filter(
            Q(label__icontains=self.q) |
            Q(uri__contains=self.q) |
            Q(manifest__label__icontains=self.q)
        )
