from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.assignments.models import Assignment
from apps.employees.forms import EmployeeForm
from apps.employees.models import Employee


def employee_list_view(request):
    employees = Employee.objects.order_by("last_name", "first_name")
    context = {
        "employees": employees,
    }
    return render(request, "employees/list.html", context)


def employee_detail_view(request, employee_id):
    employee = Employee.objects.filter(pk=employee_id).first()
    if employee is None:
        return render(
            request,
            "employees/detail.html",
            {
                "employee": None,
                "active_assignments": [],
                "assignment_history": [],
            },
            status=404,
        )

    assignments = Assignment.objects.filter(employee=employee).select_related("asset")
    active_assignments = assignments.filter(status=Assignment.AssignmentStatus.ASSIGNED)
    assignment_history = assignments
    eligible_employees = list(
        Employee.objects.filter(
            employment_status__in=[
                Employee.EmploymentStatus.ACTIVE,
                Employee.EmploymentStatus.ONBOARDING,
            ]
        )
        .exclude(pk=employee.id)
        .order_by("last_name", "first_name")
    )
    active_assignment_rows = [
        {
            "assignment": assignment,
            "transfer_candidates": eligible_employees,
        }
        for assignment in active_assignments
    ]

    context = {
        "employee": employee,
        "active_assignments": active_assignments,
        "active_assignment_rows": active_assignment_rows,
        "assignment_history": assignment_history,
    }
    return render(request, "employees/detail.html", context)


def employee_create_view(request):
    if request.method == "POST":
        form = EmployeeForm(request.POST)
        if form.is_valid():
            employee = form.save()
            messages.success(request, "Employee created successfully.")
            return redirect("employee-detail", employee_id=employee.id)
    else:
        form = EmployeeForm()

    return render(
        request,
        "employees/form.html",
        {"form": form, "page_title": "Create Employee", "submit_label": "Create Employee"},
    )


def employee_update_view(request, employee_id):
    employee = get_object_or_404(Employee, pk=employee_id)
    if request.method == "POST":
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            employee = form.save()
            messages.success(request, "Employee updated successfully.")
            return redirect("employee-detail", employee_id=employee.id)
    else:
        form = EmployeeForm(instance=employee)

    return render(
        request,
        "employees/form.html",
        {"form": form, "page_title": "Edit Employee", "submit_label": "Save Changes"},
    )


@require_POST
def employee_delete_view(request, employee_id):
    employee = get_object_or_404(Employee, pk=employee_id)
    has_active_assignment = Assignment.objects.filter(
        employee=employee,
        status=Assignment.AssignmentStatus.ASSIGNED,
    ).exists()
    if has_active_assignment:
        messages.error(request, "Cannot delete an employee with active assignments.")
        return redirect("employee-detail", employee_id=employee.id)

    employee.delete()
    messages.success(request, "Employee deleted successfully.")
    return redirect("employee-list")
