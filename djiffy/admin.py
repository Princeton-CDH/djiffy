from django.contrib import admin

from .models import IfBook, IfPage

class PageInline(admin.StackedInline):
    model = IfPage

class BookAdmin(admin.ModelAdmin):
    inlines = [PageInline]

admin.site.register(IfBook, BookAdmin)
admin.site.register(IfPage)

