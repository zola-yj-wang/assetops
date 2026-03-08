from django.contrib import admin

from apps.assignments.models import Assignment
from apps.assignments.services import assign_asset, return_asset

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

    def save_model(self, request, obj, form, change):
        if not change:
            assignment = assign_asset(
                employee=obj.employee,
                asset=obj.asset,
                notes=obj.notes,
            )
            obj.pk = assignment.pk
            obj.status = assignment.status
            obj.created_at = assignment.created_at
            obj.updated_at = assignment.updated_at
            return

        previous = Assignment.objects.get(pk=obj.pk)
        if (
            previous.status == Assignment.AssignmentStatus.ASSIGNED
            and obj.status == Assignment.AssignmentStatus.RETURNED
        ):
            updated = return_asset(assignment=previous, notes=obj.notes)
            obj.status = updated.status
            obj.updated_at = updated.updated_at
            return

        super().save_model(request, obj, form, change)
