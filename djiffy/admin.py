from django.contrib import admin

from .models import Manifest, Canvas

class CanvasInline(admin.StackedInline):
    model = Canvas

class ManifestAdmin(admin.ModelAdmin):
    inlines = [CanvasInline]
    list_display = ('admin_thumbnail', 'label', 'short_id', 'created',
        'last_modified')

class CanvasAdmin(admin.ModelAdmin):
    list_display = ('admin_thumbnail', 'label', 'short_id', 'manifest')


admin.site.register(Manifest, ManifestAdmin)
admin.site.register(Canvas, CanvasAdmin)

