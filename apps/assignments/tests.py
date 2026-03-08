from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.assignments.models import Assignment
from apps.assets.models import Asset
from apps.employees.models import Employee


class AssignmentRulesTestCase(TestCase):
    def setUp(self):
        self.employee_1 = Employee.objects.create(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            employment_status=Employee.EmploymentStatus.ACTIVE,
        )
        self.employee_2 = Employee.objects.create(
            first_name="Alan",
            last_name="Turing",
            email="alan@example.com",
            employment_status=Employee.EmploymentStatus.ACTIVE,
        )
        self.employee_inactive = Employee.objects.create(
            first_name="Grace",
            last_name="Hopper",
            email="grace@example.com",
            employment_status=Employee.EmploymentStatus.INACTIVE,
        )
        self.asset = Asset.objects.create(
            asset_tag="LT-001",
            serial_number="SN-LT-001",
            asset_type=Asset.AssetType.LAPTOP,
            status=Asset.AssetStatus.IN_STOCK,
        )

    def test_assigning_asset_updates_asset_status_to_assigned(self):
        Assignment.objects.create(employee=self.employee_1, asset=self.asset)

        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, Asset.AssetStatus.ASSIGNED)

    def test_returning_assignment_updates_asset_status_to_in_stock(self):
        assignment = Assignment.objects.create(employee=self.employee_1, asset=self.asset)

        assignment.status = Assignment.AssignmentStatus.RETURNED
        assignment.save()

        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, Asset.AssetStatus.IN_STOCK)

    def test_cannot_create_second_active_assignment_for_same_asset(self):
        Assignment.objects.create(employee=self.employee_1, asset=self.asset)

        with self.assertRaises(ValidationError):
            Assignment.objects.create(employee=self.employee_2, asset=self.asset)

    def test_cannot_assign_asset_that_is_not_in_stock(self):
        self.asset.status = Asset.AssetStatus.IN_REPAIR
        self.asset.save(update_fields=["status", "updated_at"])

        with self.assertRaises(ValidationError):
            Assignment.objects.create(employee=self.employee_1, asset=self.asset)

    def test_cannot_create_assignment_directly_as_returned(self):
        with self.assertRaises(ValidationError):
            Assignment.objects.create(
                employee=self.employee_1,
                asset=self.asset,
                status=Assignment.AssignmentStatus.RETURNED,
            )

    def test_database_constraint_blocks_duplicate_active_assignment(self):
        Assignment.objects.create(employee=self.employee_1, asset=self.asset)

        with self.assertRaises(IntegrityError):
            Assignment.objects.bulk_create(
                [
                    Assignment(
                        employee=self.employee_2,
                        asset=self.asset,
                        status=Assignment.AssignmentStatus.ASSIGNED,
                    )
                ]
            )

    def test_cannot_assign_asset_to_inactive_employee(self):
        with self.assertRaises(ValidationError):
            Assignment.objects.create(employee=self.employee_inactive, asset=self.asset)

    def test_returned_assignment_cannot_be_reopened(self):
        assignment = Assignment.objects.create(employee=self.employee_1, asset=self.asset)
        assignment.status = Assignment.AssignmentStatus.RETURNED
        assignment.save()

        assignment.status = Assignment.AssignmentStatus.ASSIGNED
        with self.assertRaises(ValidationError):
            assignment.save()
