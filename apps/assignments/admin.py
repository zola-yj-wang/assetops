from django.contrib import admin
from apps.assignments.models import Assignment

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "asset",
        "employee",
        "status",
        "updated_at",
    )

    search_fields = (
        "asset__asset_tag",
        "asset__serial_number",
        "employee__first_name",
        "employee__last_name",
        "employee__email",
    )

    list_filter = (
        "status",
        "updated_at",
    )