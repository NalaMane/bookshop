from django.contrib import admin
from django.utils.html import format_html_join

from .models import ImportLog


@admin.register(ImportLog)
class ImportLogAdmin(admin.ModelAdmin):
    """Lab 2 – history of all ERP imports (read-only, owner: Ami)."""

    list_display = ("created_at", "file_name", "status", "created_count", "updated_count", "failed_count")
    list_filter = ("status",)
    search_fields = ("file_name",)
    fields = ("created_at", "file_name", "status", "created_count", "updated_count", "failed_count", "error_list")
    readonly_fields = fields

    @admin.display(description="Errors")
    def error_list(self, log):
        if not log.errors:
            return "–"
        return format_html_join("", "<div>{}</div>", ((message,) for message in log.errors))

    # The log is written by the import only – staff can read it, not change it.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
