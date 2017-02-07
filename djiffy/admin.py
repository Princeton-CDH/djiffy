from django.contrib import admin

from .models import IfBook, IfPage

class PageInline(admin.StackedInline):
    model = IfPage

class BookAdmin(admin.ModelAdmin):
    inlines = [PageInline]
    list_display = ('admin_thumbnail', 'label', 'short_id', 'created',
        'last_modified')

class PageAdmin(admin.ModelAdmin):
    list_display = ('admin_thumbnail', 'label', 'short_id', 'book')


admin.site.register(IfBook, BookAdmin)
admin.site.register(IfPage, PageAdmin)

