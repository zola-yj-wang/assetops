import json

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from apps.assignments.models import Assignment
from apps.assignments.services import (
    assign_asset,
    offboarding_check,
    return_asset,
    transfer_asset,
)
from apps.assets.models import Asset
from apps.employees.models import Employee


def _format_validation_error(exc):
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    return {"non_field_errors": exc.messages}


def _parse_json_payload(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        raise ValidationError({"payload": "Invalid JSON payload."})


def _resolve_next_url(request, default_route_name):
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return reverse(default_route_name)


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
        messages.error(request, str(_format_validation_error(exc)))

    return redirect("assignment-dashboard")


@require_POST
def return_submit_view(request, assignment_id):
    assignment = get_object_or_404(Assignment, pk=assignment_id)
    notes = request.POST.get("notes")
    physical_location = request.POST.get("physical_location")

    try:
        return_asset(
            assignment=assignment,
            notes=notes,
            physical_location=physical_location,
        )
        messages.success(request, "Asset returned successfully.")
    except ValidationError as exc:
        messages.error(request, str(_format_validation_error(exc)))

    return redirect(_resolve_next_url(request, "assignment-dashboard"))


@require_POST
def transfer_submit_view(request, assignment_id):
    assignment = get_object_or_404(Assignment, pk=assignment_id)
    to_employee_id = request.POST.get("to_employee_id")
    notes = request.POST.get("notes", "")

    try:
        if not to_employee_id:
            raise ValidationError({"employee": "Please select a target employee."})
        to_employee = Employee.objects.filter(pk=to_employee_id).first()
        if to_employee is None:
            raise ValidationError({"employee": "Target employee not found."})

        transfer_asset(
            assignment=assignment,
            to_employee=to_employee,
            notes=notes,
        )
        messages.success(request, "Asset owner transferred successfully.")
    except ValidationError as exc:
        messages.error(request, str(_format_validation_error(exc)))

    return redirect("asset-list")


@require_POST
def transfer_owner_submit_view(request, asset_id):
    asset = get_object_or_404(Asset, pk=asset_id)
    to_employee_id = request.POST.get("to_employee_id")
    notes = request.POST.get("notes", "")

    try:
        if not to_employee_id:
            raise ValidationError({"employee": "Please select a target employee."})
        to_employee = Employee.objects.filter(pk=to_employee_id).first()
        if to_employee is None:
            raise ValidationError({"employee": "Target employee not found."})

        if asset.status == Asset.AssetStatus.IN_STOCK:
            assign_asset(employee=to_employee, asset=asset, notes=notes)
            messages.success(request, "Asset owner assigned successfully.")
        elif asset.status == Asset.AssetStatus.ASSIGNED:
            assignment = Assignment.objects.filter(
                asset=asset,
                status=Assignment.AssignmentStatus.ASSIGNED,
            ).first()
            if assignment is None:
                raise ValidationError(
                    {"asset": "Asset is marked assigned but has no active assignment."}
                )
            transfer_asset(
                assignment=assignment,
                to_employee=to_employee,
                notes=notes,
            )
            messages.success(request, "Asset owner transferred successfully.")
        else:
            raise ValidationError(
                {"asset": "Only in-stock or assigned assets can transfer owner."}
            )
    except ValidationError as exc:
        messages.error(request, str(_format_validation_error(exc)))

    return redirect(_resolve_next_url(request, "asset-list"))


@require_POST
def assign_asset_view(request):
    try:
        payload = _parse_json_payload(request)
        employee_id = payload.get("employee_id")
        asset_id = payload.get("asset_id")
        if not employee_id:
            raise ValidationError({"employee": "employee_id is required."})
        if not asset_id:
            raise ValidationError({"asset": "asset_id is required."})

        employee = Employee.objects.filter(pk=employee_id).first()
        if employee is None:
            raise ValidationError({"employee": "Employee not found."})

        asset = Asset.objects.filter(pk=asset_id).first()
        if asset is None:
            raise ValidationError({"asset": "Asset not found."})

        assignment = assign_asset(
            employee=employee,
            asset=asset,
            notes=payload.get("notes", ""),
        )
    except ValidationError as exc:
        return JsonResponse({"errors": _format_validation_error(exc)}, status=400)

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
    try:
        payload = _parse_json_payload(request)
        assignment = Assignment.objects.filter(pk=assignment_id).first()
        if assignment is None:
            return JsonResponse(
                {"errors": {"assignment": ["Assignment not found."]}},
                status=404,
            )

        updated = return_asset(
            assignment=assignment,
            notes=payload.get("notes"),
            physical_location=payload.get("physical_location"),
        )
    except ValidationError as exc:
        return JsonResponse({"errors": _format_validation_error(exc)}, status=400)

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
    employee = Employee.objects.filter(pk=employee_id).first()
    if employee is None:
        return JsonResponse(
            {"errors": {"employee": ["Employee not found."]}},
            status=404,
        )
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


@require_POST
def transfer_asset_view(request, assignment_id):
    try:
        payload = _parse_json_payload(request)
        to_employee_id = payload.get("to_employee_id")
        if not to_employee_id:
            raise ValidationError({"employee": "to_employee_id is required."})

        assignment = Assignment.objects.filter(pk=assignment_id).first()
        if assignment is None:
            return JsonResponse(
                {"errors": {"assignment": ["Assignment not found."]}},
                status=404,
            )

        to_employee = Employee.objects.filter(pk=to_employee_id).first()
        if to_employee is None:
            raise ValidationError({"employee": "Employee not found."})

        new_assignment = transfer_asset(
            assignment=assignment,
            to_employee=to_employee,
            notes=payload.get("notes", ""),
        )
    except ValidationError as exc:
        return JsonResponse({"errors": _format_validation_error(exc)}, status=400)

    return JsonResponse(
        {
            "id": new_assignment.id,
            "status": new_assignment.status,
            "employee_id": new_assignment.employee_id,
            "asset_id": new_assignment.asset_id,
        },
        status=201,
    )
