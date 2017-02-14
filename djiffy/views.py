from django.views.generic import DetailView, ListView

from .models import Manifest, Canvas


class ManifestList(ListView):
    model = Manifest
    template_name = 'djiffy/manifest_list.html'
    context_object_name = 'manifests'


class ManifestDetail(DetailView):
    model = Manifest
    template_name = 'djiffy/manifest_detail.html'
    context_object_name = 'manifest'

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = Manifest.objects.all()
        return queryset.get(short_id=self.kwargs['id'])


class CanvasDetail(DetailView):
    model = Canvas
    template_name = 'djiffy/canvas_detail.html'
    context_object_name = 'canvas'

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = Canvas.objects.all()
        return queryset.get(short_id=self.kwargs['id'],
            manifest__short_id=self.kwargs['manifest_id'])
