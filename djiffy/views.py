from django.views.generic import DetailView, ListView

from .models import Manifest, Canvas


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
        return queryset.get(short_id=self.kwargs['id'])


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
        return queryset.get(short_id=self.kwargs['id'],
            manifest__short_id=self.kwargs['manifest_id'])
