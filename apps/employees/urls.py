from django.urls import path

from apps.employees.views import (
    employee_create_view,
    employee_delete_view,
    employee_detail_view,
    employee_list_view,
    employee_update_view,
)

urlpatterns = [
    path("", employee_list_view, name="employee-list"),
    path("create/", employee_create_view, name="employee-create"),
    path("<int:employee_id>/", employee_detail_view, name="employee-detail"),
    path("<int:employee_id>/edit/", employee_update_view, name="employee-update"),
    path("<int:employee_id>/delete/", employee_delete_view, name="employee-delete"),
]
