from django.db import models
from apps.employees.models import Employee
from apps.assets.models import Asset

class Assignment(models.Model):

    class AssignmentStatus(models.TextChoices):
        ASSIGNED = "ASSIGNED", "Assigned"
        RETURNED = "RETURNED", "Returned"

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    updated_at = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.ASSIGNED,
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.asset.asset_tag} → {self.employee}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.status == self.AssignmentStatus.ASSIGNED:
            self.asset.status = Asset.AssetStatus.ASSIGNED
        elif self.status == self.AssignmentStatus.RETURNED:
            self.asset.status = Asset.AssetStatus.IN_STOCK

        self.asset.save()