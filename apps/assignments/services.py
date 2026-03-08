from django.core.exceptions import ValidationError
from django.db import transaction
from typing import Optional

from apps.assignments.models import Assignment
from apps.assets.models import Asset
from apps.employees.models import Employee


def assign_asset(*, employee: Employee, asset: Asset, notes: str = "") -> Assignment:
    allowed_employee_statuses = {
        Employee.EmploymentStatus.ACTIVE,
        Employee.EmploymentStatus.ONBOARDING,
    }
    if employee.employment_status not in allowed_employee_statuses:
        raise ValidationError(
            {"employee": "Only onboarding or active employees can receive assets."}
        )

    with transaction.atomic():
        locked_asset = Asset.objects.select_for_update().get(pk=asset.pk)
        if locked_asset.status != Asset.AssetStatus.IN_STOCK:
            raise ValidationError({"asset": "Only in-stock assets can be assigned."})

        assignment = Assignment(
            employee=employee,
            asset=locked_asset,
            status=Assignment.AssignmentStatus.ASSIGNED,
            notes=notes,
        )
        assignment.full_clean()
        assignment.save()

        locked_asset.status = Asset.AssetStatus.ASSIGNED
        locked_asset.save(update_fields=["status", "updated_at"])
        return assignment


def return_asset(*, assignment: Assignment, notes: Optional[str] = None) -> Assignment:
    with transaction.atomic():
        locked_assignment = Assignment.objects.select_for_update().select_related(
            "asset"
        ).get(pk=assignment.pk)

        if locked_assignment.status != Assignment.AssignmentStatus.ASSIGNED:
            raise ValidationError({"status": "Only active assignments can be returned."})

        if notes is not None:
            locked_assignment.notes = notes
        locked_assignment.status = Assignment.AssignmentStatus.RETURNED
        locked_assignment.full_clean()
        locked_assignment.save(update_fields=["status", "notes", "updated_at"])

        locked_asset = locked_assignment.asset
        locked_asset.status = Asset.AssetStatus.IN_STOCK
        locked_asset.save(update_fields=["status", "updated_at"])
        return locked_assignment


def offboarding_check(*, employee: Employee) -> dict:
    active_assignments = list(
        Assignment.objects.filter(
            employee=employee,
            status=Assignment.AssignmentStatus.ASSIGNED,
        ).select_related("asset")
    )
    return {
        "employee_id": employee.id,
        "can_offboard": len(active_assignments) == 0,
        "active_assignments": active_assignments,
        "active_assignment_count": len(active_assignments),
    }
