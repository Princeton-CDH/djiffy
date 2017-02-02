from django.contrib import admin

from .models import IfBook, IfPage

class PageInline(admin.StackedInline):
    model = IfPage

class BookAdmin(admin.ModelAdmin):
    inlines = [PageInline]
    list_display= ('admin_thumbnail', 'label', 'short_id', 'created',
        'last_modified')

admin.site.register(IfBook, BookAdmin)
admin.site.register(IfPage)

