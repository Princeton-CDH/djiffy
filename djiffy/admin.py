from django.contrib import admin
from django.forms import Select
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import Manifest, Canvas


class ManifestSelectWidget(Select):
    '''Select widget for a :class:`~djiffy.models.Manifest` that also
    displays thumbnail and links to view and edit the Manifest.'''

    def render(self, name, value, attrs=None):
        widget = super(ManifestSelectWidget, self).render(name, value, attrs)
        if value:
            manifest = Manifest.objects.get(pk=value)
            # NOTE: should really only display edit link if user has
            # the change permission on manifests
            # FIXME: formatting / layout issues
            return mark_safe(
                '<div>%s</div><br/> <div style="float:left">%s <a href="%s">view</a> | <a href="%s">edit</a></div>' % \
                    (widget, manifest.admin_thumbnail() or '',
                     manifest.get_absolute_url(),
                     reverse('admin:djiffy_manifest_change', args=[manifest.id]))
                )

        return widget


class CanvasInline(admin.StackedInline):
    model = Canvas


class ManifestAdmin(admin.ModelAdmin):
    inlines = [CanvasInline]
    list_display = ('admin_thumbnail', 'label', 'short_id', 'created',
        'last_modified')
    list_display_links = ('admin_thumbnail', 'label')
    search_fields = ('label', 'short_id', 'uri', 'metadata', 'extra_data')


class CanvasAdmin(admin.ModelAdmin):
    list_display = ('admin_thumbnail', 'label', 'short_id', 'manifest')


admin.site.register(Manifest, ManifestAdmin)
admin.site.register(Canvas, CanvasAdmin)

