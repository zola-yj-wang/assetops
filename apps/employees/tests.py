from django.test import TestCase
from django.urls import reverse

from apps.assignments.models import Assignment
from apps.assignments.services import assign_asset
from apps.assets.models import Asset
from apps.employees.models import Employee


class EmployeeListPageTestCase(TestCase):
    def test_employee_list_page_renders_and_links_to_detail(self):
        employee = Employee.objects.create(
            first_name="Linus",
            last_name="Torvalds",
            email="linus-list@example.com",
            employment_status=Employee.EmploymentStatus.ACTIVE,
        )

        response = self.client.get(reverse("employee-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Employee List")
        self.assertContains(response, "Linus Torvalds")
        self.assertContains(response, reverse("employee-detail", kwargs={"employee_id": employee.id}))


class EmployeeDetailPageTestCase(TestCase):
    def test_employee_detail_page_renders(self):
        employee = Employee.objects.create(
            first_name="Ada",
            last_name="Lovelace",
            email="ada-page@example.com",
            employment_status=Employee.EmploymentStatus.ACTIVE,
        )

        response = self.client.get(
            reverse("employee-detail", kwargs={"employee_id": employee.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ada Lovelace")
        self.assertContains(response, "Employee detail")

    def test_employee_detail_page_returns_404_for_missing_employee(self):
        response = self.client.get(reverse("employee-detail", kwargs={"employee_id": 9999}))
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Employee Not Found", status_code=404)

    def test_employee_detail_active_assignment_can_transfer_owner(self):
        owner = Employee.objects.create(
            first_name="Owner",
            last_name="One",
            email="owner-one@example.com",
            employment_status=Employee.EmploymentStatus.ACTIVE,
        )
        target = Employee.objects.create(
            first_name="Owner",
            last_name="Two",
            email="owner-two@example.com",
            employment_status=Employee.EmploymentStatus.ACTIVE,
        )
        asset = Asset.objects.create(
            asset_tag="LT-EMP-1",
            serial_number="SN-EMP-1",
            asset_type=Asset.AssetType.LAPTOP,
            status=Asset.AssetStatus.IN_STOCK,
        )
        original_assignment = assign_asset(employee=owner, asset=asset)

        response = self.client.post(
            reverse("asset-transfer-owner-submit", kwargs={"asset_id": asset.id}),
            data={
                "to_employee_id": target.id,
                "notes": "move in employee detail",
                "next": reverse("employee-detail", kwargs={"employee_id": owner.id}),
            },
            follow=False,
        )
        self.assertRedirects(
            response,
            reverse("employee-detail", kwargs={"employee_id": owner.id}),
            fetch_redirect_response=False,
        )

        original_assignment.refresh_from_db()
        self.assertEqual(original_assignment.status, Assignment.AssignmentStatus.RETURNED)
        new_assignment = Assignment.objects.get(
            asset=asset,
            status=Assignment.AssignmentStatus.ASSIGNED,
        )
        self.assertEqual(new_assignment.employee_id, target.id)


class EmployeeCrudPageTestCase(TestCase):
    def test_employee_create_update_delete_flow(self):
        create_response = self.client.post(
            reverse("employee-create"),
            data={
                "first_name": "New",
                "last_name": "User",
                "email": "new-user@example.com",
                "department": Employee.Department.IT,
                "location": "Amsterdam",
                "employment_status": Employee.EmploymentStatus.ACTIVE,
                "start_date": "",
                "end_date": "",
            },
            follow=False,
        )
        employee = Employee.objects.get(email="new-user@example.com")
        self.assertRedirects(
            create_response,
            reverse("employee-detail", kwargs={"employee_id": employee.id}),
            fetch_redirect_response=False,
        )

        update_response = self.client.post(
            reverse("employee-update", kwargs={"employee_id": employee.id}),
            data={
                "first_name": "Updated",
                "last_name": "User",
                "email": "new-user@example.com",
                "department": Employee.Department.ENGINEERING,
                "location": "Rotterdam",
                "employment_status": Employee.EmploymentStatus.ACTIVE,
                "start_date": "",
                "end_date": "",
            },
            follow=False,
        )
        self.assertRedirects(
            update_response,
            reverse("employee-detail", kwargs={"employee_id": employee.id}),
            fetch_redirect_response=False,
        )
        employee.refresh_from_db()
        self.assertEqual(employee.first_name, "Updated")
        self.assertEqual(employee.location, "Rotterdam")

        delete_response = self.client.post(
            reverse("employee-delete", kwargs={"employee_id": employee.id}),
            follow=False,
        )
        self.assertRedirects(
            delete_response,
            reverse("employee-list"),
            fetch_redirect_response=False,
        )
        self.assertFalse(Employee.objects.filter(id=employee.id).exists())
