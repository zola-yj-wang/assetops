import json

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.accounts.decorators import assetops_operator_required
from apps.accounts.services import notify_default_admin_group_for_change
from apps.assignments.models import Assignment
from apps.assignments.serializers import (
    AssignAssetRequestSerializer,
    AssignmentResponseSerializer,
    OffboardingCheckResponseSerializer,
    ReturnAssetRequestSerializer,
    TransferAssetRequestSerializer,
)
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


@assetops_operator_required
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


@assetops_operator_required
@require_POST
def assign_submit_view(request):
    try:
        request_serializer = AssignAssetRequestSerializer(
            data={
                "employee_id": request.POST.get("employee_id"),
                "asset_id": request.POST.get("asset_id"),
                "notes": request.POST.get("notes", ""),
            }
        )
        request_serializer.is_valid(raise_exception=True)

        assignment = assign_asset(
            employee=request_serializer.validated_data["employee"],
            asset=request_serializer.validated_data["asset"],
            notes=request_serializer.validated_data.get("notes", ""),
        )
        notify_default_admin_group_for_change(
            actor=request.user,
            resource_type="assignment",
            action="assign",
            object_label=str(assignment),
            object_instance=assignment,
        )
        messages.success(request, "Asset assigned successfully.")
    except DRFValidationError as exc:
        messages.error(request, str(exc.detail))
    except ValidationError as exc:
        messages.error(request, str(_format_validation_error(exc)))

    return redirect("assignment-dashboard")


@assetops_operator_required
@require_POST
def return_submit_view(request, assignment_id):
    assignment = get_object_or_404(Assignment, pk=assignment_id)

    try:
        request_serializer = ReturnAssetRequestSerializer(
            data={
                "notes": request.POST.get("notes"),
                "physical_location": request.POST.get("physical_location"),
            },
            context={"require_physical_location": True},
        )
        request_serializer.is_valid(raise_exception=True)

        updated_assignment = return_asset(
            assignment=assignment,
            notes=request_serializer.validated_data.get("notes"),
            physical_location=request_serializer.validated_data.get("physical_location"),
        )
        notify_default_admin_group_for_change(
            actor=request.user,
            resource_type="assignment",
            action="return",
            object_label=str(updated_assignment),
            object_instance=updated_assignment,
        )
        messages.success(request, "Asset returned successfully.")
    except DRFValidationError as exc:
        messages.error(request, str(exc.detail))
    except ValidationError as exc:
        messages.error(request, str(_format_validation_error(exc)))

    return redirect(_resolve_next_url(request, "assignment-dashboard"))


@assetops_operator_required
@require_POST
def transfer_submit_view(request, assignment_id):
    assignment = get_object_or_404(Assignment, pk=assignment_id)

    try:
        request_serializer = TransferAssetRequestSerializer(
            data={
                "to_employee_id": request.POST.get("to_employee_id"),
                "notes": request.POST.get("notes", ""),
            }
        )
        request_serializer.is_valid(raise_exception=True)

        new_assignment = transfer_asset(
            assignment=assignment,
            to_employee=request_serializer.validated_data["to_employee"],
            notes=request_serializer.validated_data.get("notes", ""),
        )
        notify_default_admin_group_for_change(
            actor=request.user,
            resource_type="assignment",
            action="transfer",
            object_label=str(new_assignment),
            object_instance=new_assignment,
        )
        messages.success(request, "Asset owner transferred successfully.")
    except DRFValidationError as exc:
        messages.error(request, str(exc.detail))
    except ValidationError as exc:
        messages.error(request, str(_format_validation_error(exc)))

    return redirect("asset-list")


@assetops_operator_required
@require_POST
def transfer_owner_submit_view(request, asset_id):
    asset = get_object_or_404(Asset, pk=asset_id)

    try:
        request_serializer = TransferAssetRequestSerializer(
            data={
                "to_employee_id": request.POST.get("to_employee_id"),
                "notes": request.POST.get("notes", ""),
            }
        )
        request_serializer.is_valid(raise_exception=True)
        to_employee = request_serializer.validated_data["to_employee"]
        notes = request_serializer.validated_data.get("notes", "")

        if asset.status == Asset.AssetStatus.IN_STOCK:
            assignment = assign_asset(employee=to_employee, asset=asset, notes=notes)
            notify_default_admin_group_for_change(
                actor=request.user,
                resource_type="assignment",
                action="assign",
                object_label=str(assignment),
                object_instance=assignment,
            )
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
            new_assignment = transfer_asset(
                assignment=assignment,
                to_employee=to_employee,
                notes=notes,
            )
            notify_default_admin_group_for_change(
                actor=request.user,
                resource_type="assignment",
                action="transfer",
                object_label=str(new_assignment),
                object_instance=new_assignment,
            )
            messages.success(request, "Asset owner transferred successfully.")
        else:
            raise ValidationError(
                {"asset": "Only in-stock or assigned assets can transfer owner."}
            )
    except DRFValidationError as exc:
        messages.error(request, str(exc.detail))
    except ValidationError as exc:
        messages.error(request, str(_format_validation_error(exc)))

    return redirect(_resolve_next_url(request, "asset-list"))


@assetops_operator_required
@require_POST
def assign_asset_view(request):
    try:
        payload = _parse_json_payload(request)
        request_serializer = AssignAssetRequestSerializer(data=payload)
        if not request_serializer.is_valid():
            return JsonResponse({"errors": request_serializer.errors}, status=400)

        assignment = assign_asset(
            employee=request_serializer.validated_data["employee"],
            asset=request_serializer.validated_data["asset"],
            notes=request_serializer.validated_data.get("notes", ""),
        )
        notify_default_admin_group_for_change(
            actor=request.user,
            resource_type="assignment",
            action="assign",
            object_label=str(assignment),
            object_instance=assignment,
        )
    except ValidationError as exc:
        return JsonResponse({"errors": _format_validation_error(exc)}, status=400)

    response_serializer = AssignmentResponseSerializer(instance=assignment)
    return JsonResponse(response_serializer.data, status=201)


@assetops_operator_required
@require_POST
def return_asset_view(request, assignment_id):
    try:
        payload = _parse_json_payload(request)
        request_serializer = ReturnAssetRequestSerializer(data=payload)
        if not request_serializer.is_valid():
            return JsonResponse({"errors": request_serializer.errors}, status=400)

        assignment = Assignment.objects.filter(pk=assignment_id).first()
        if assignment is None:
            return JsonResponse(
                {"errors": {"assignment": ["Assignment not found."]}},
                status=404,
            )

        updated = return_asset(
            assignment=assignment,
            notes=request_serializer.validated_data.get("notes"),
            physical_location=request_serializer.validated_data.get("physical_location"),
        )
        notify_default_admin_group_for_change(
            actor=request.user,
            resource_type="assignment",
            action="return",
            object_label=str(updated),
            object_instance=updated,
        )
    except ValidationError as exc:
        return JsonResponse({"errors": _format_validation_error(exc)}, status=400)

    response_serializer = AssignmentResponseSerializer(instance=updated)
    return JsonResponse(response_serializer.data)


@assetops_operator_required
@require_GET
def offboarding_check_view(request, employee_id):
    employee = Employee.objects.filter(pk=employee_id).first()
    if employee is None:
        return JsonResponse(
            {"errors": {"employee": ["Employee not found."]}},
            status=404,
        )
    result = offboarding_check(employee=employee)
    response_serializer = OffboardingCheckResponseSerializer(
        data={
            "employee_id": result["employee_id"],
            "can_offboard": result["can_offboard"],
            "active_assignment_count": result["active_assignment_count"],
            "active_asset_tags": [
                assignment.asset.asset_tag for assignment in result["active_assignments"]
            ],
        }
    )
    response_serializer.is_valid(raise_exception=True)
    return JsonResponse(response_serializer.validated_data)


@assetops_operator_required
@require_POST
def transfer_asset_view(request, assignment_id):
    try:
        payload = _parse_json_payload(request)
        request_serializer = TransferAssetRequestSerializer(data=payload)
        if not request_serializer.is_valid():
            return JsonResponse({"errors": request_serializer.errors}, status=400)

        assignment = Assignment.objects.filter(pk=assignment_id).first()
        if assignment is None:
            return JsonResponse(
                {"errors": {"assignment": ["Assignment not found."]}},
                status=404,
            )

        new_assignment = transfer_asset(
            assignment=assignment,
            to_employee=request_serializer.validated_data["to_employee"],
            notes=request_serializer.validated_data.get("notes", ""),
        )
        notify_default_admin_group_for_change(
            actor=request.user,
            resource_type="assignment",
            action="transfer",
            object_label=str(new_assignment),
            object_instance=new_assignment,
        )
    except ValidationError as exc:
        return JsonResponse({"errors": _format_validation_error(exc)}, status=400)

    response_serializer = AssignmentResponseSerializer(instance=new_assignment)
    return JsonResponse(response_serializer.data, status=201)
