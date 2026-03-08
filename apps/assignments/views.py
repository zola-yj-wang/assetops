import json

from django.core.exceptions import ValidationError
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.assignments.models import Assignment
from apps.assignments.services import assign_asset, offboarding_check, return_asset
from apps.assets.models import Asset
from apps.employees.models import Employee


@require_GET
def assignment_dashboard_view(request):
    employees = Employee.objects.order_by("last_name", "first_name")
    available_assets = Asset.objects.filter(status=Asset.AssetStatus.IN_STOCK).order_by(
        "asset_tag"
    )
    active_assignments = Assignment.objects.filter(
        status=Assignment.AssignmentStatus.ASSIGNED
    ).select_related("employee", "asset")

    selected_employee = None
    offboarding_result = None
    employee_id = request.GET.get("employee_id")
    if employee_id:
        selected_employee = get_object_or_404(Employee, pk=employee_id)
        offboarding_result = offboarding_check(employee=selected_employee)

    context = {
        "employees": employees,
        "available_assets": available_assets,
        "active_assignments": active_assignments,
        "selected_employee": selected_employee,
        "offboarding_result": offboarding_result,
    }
    return render(request, "assignments/dashboard.html", context)


@require_POST
def assign_submit_view(request):
    employee = get_object_or_404(Employee, pk=request.POST.get("employee_id"))
    asset = get_object_or_404(Asset, pk=request.POST.get("asset_id"))
    notes = request.POST.get("notes", "")

    try:
        assign_asset(employee=employee, asset=asset, notes=notes)
        messages.success(request, "Asset assigned successfully.")
    except ValidationError as exc:
        messages.error(request, str(exc))

    return redirect("assignment-dashboard")


@require_POST
def return_submit_view(request, assignment_id):
    assignment = get_object_or_404(Assignment, pk=assignment_id)
    notes = request.POST.get("notes")

    try:
        return_asset(assignment=assignment, notes=notes)
        messages.success(request, "Asset returned successfully.")
    except ValidationError as exc:
        messages.error(request, str(exc))

    return redirect("assignment-dashboard")


@require_POST
def assign_asset_view(request):
    payload = json.loads(request.body or "{}")
    employee = Employee.objects.get(pk=payload["employee_id"])
    asset = Asset.objects.get(pk=payload["asset_id"])

    try:
        assignment = assign_asset(
            employee=employee,
            asset=asset,
            notes=payload.get("notes", ""),
        )
    except ValidationError as exc:
        return JsonResponse({"errors": exc.message_dict}, status=400)

    return JsonResponse(
        {
            "id": assignment.id,
            "status": assignment.status,
            "employee_id": assignment.employee_id,
            "asset_id": assignment.asset_id,
        },
        status=201,
    )


@require_POST
def return_asset_view(request, assignment_id):
    assignment = Assignment.objects.get(pk=assignment_id)
    payload = json.loads(request.body or "{}")

    try:
        updated = return_asset(
            assignment=assignment,
            notes=payload.get("notes"),
        )
    except ValidationError as exc:
        return JsonResponse({"errors": exc.message_dict}, status=400)

    return JsonResponse(
        {
            "id": updated.id,
            "status": updated.status,
            "employee_id": updated.employee_id,
            "asset_id": updated.asset_id,
        }
    )


@require_GET
def offboarding_check_view(request, employee_id):
    employee = Employee.objects.get(pk=employee_id)
    result = offboarding_check(employee=employee)
    return JsonResponse(
        {
            "employee_id": result["employee_id"],
            "can_offboard": result["can_offboard"],
            "active_assignment_count": result["active_assignment_count"],
            "active_asset_tags": [
                assignment.asset.asset_tag for assignment in result["active_assignments"]
            ],
        }
    )
