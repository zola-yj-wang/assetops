from django.contrib.auth.models import Group, User
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.assignments.models import Assignment
from apps.assignments.services import assign_asset
from apps.assets.models import Asset, AssetType
from apps.employees.models import Employee


def get_asset_type(code):
    return AssetType.objects.get(code=code)


class EmployeeOperatorAccessMixin:
    operator_group = "HR"

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username=f"{self.operator_group.lower()}-operator",
            email=f"{self.operator_group.lower()}-operator@example.com",
            password="password123",
        )
        operator_group, _ = Group.objects.get_or_create(name=self.operator_group)
        self.user.groups.add(operator_group)
        self.client.force_login(self.user)


class EmployeeListPageTestCase(EmployeeOperatorAccessMixin, TestCase):
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


class EmployeeDetailPageTestCase(EmployeeOperatorAccessMixin, TestCase):
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
            asset_type=get_asset_type(Asset.AssetType.LAPTOP),
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


class EmployeeCrudPageTestCase(EmployeeOperatorAccessMixin, TestCase):
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

    def test_non_hr_change_sends_notification_to_hr_group(self):
        hr_group, _ = Group.objects.get_or_create(name="HR")
        hr_user = User.objects.create_user(
            username="hr-admin",
            email="hr-admin@example.com",
            password="password123",
        )
        hr_user.groups.add(hr_group)

        om_group, _ = Group.objects.get_or_create(name="OM")
        self.user.groups.clear()
        self.user.groups.add(om_group)

        response = self.client.post(
            reverse("employee-create"),
            data={
                "first_name": "Cross",
                "last_name": "Group",
                "email": "cross-group@example.com",
                "department": Employee.Department.HR,
                "location": "Amsterdam",
                "employment_status": Employee.EmploymentStatus.ACTIVE,
                "start_date": "",
                "end_date": "",
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["hr-admin@example.com"])

    def test_anonymous_user_cannot_access_employee_pages(self):
        self.client.logout()
        response = self.client.get(reverse("employee-list"))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('employee-list')}",
            fetch_redirect_response=False,
        )
