from django.db import models

class Employee(models.Model):
    class Department(models.TextChoices):
        IT = "IT", "IT"
        HR = "HR", "HR"
        FINANCE = "FINANCE", "Finance"
        OPERATIONS = "OPERATIONS", "Operations"
        ENGINEERING = "ENGINEERING", "Engineering"
        OTHER = "OTHER", "Other"

    class EmploymentStatus(models.TextChoices):
        ONBOARDING = "ONBOARDING", "Onboarding"
        ACTIVE = "ACTIVE", "Active"
        OFFBOARDING = "OFFBOARDING", "Offboarding"
        INACTIVE = "INACTIVE", "Inactive"

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    department = models.CharField(
        max_length=30,
        choices=Department.choices,
        default=Department.OTHER,
    )
    location = models.CharField(max_length=100, blank=True)
    employment_status = models.CharField(
        max_length=20,
        choices=EmploymentStatus.choices,
        default=EmploymentStatus.ONBOARDING,
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"