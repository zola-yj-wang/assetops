from django import forms

from apps.employees.models import Employee


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            "first_name",
            "last_name",
            "email",
            "department",
            "location",
            "employment_status",
            "start_date",
            "end_date",
        ]
