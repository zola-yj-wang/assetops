from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.assets.models import Asset
from apps.employees.models import Employee


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

    updated_at = models.DateTimeField(auto_now=True)

    status = models.CharField(
        max_length=20,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.ASSIGNED,
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["asset"],
                condition=Q(status="ASSIGNED"),
                name="unique_active_assignment_per_asset",
            )
        ]

    def __str__(self):
        return f"{self.asset.asset_tag} → {self.employee}"

    def clean(self):
        super().clean()

        if self.status == self.AssignmentStatus.RETURNED and self._state.adding:
            raise ValidationError(
                {"status": "Cannot create a returned assignment directly."}
            )

        if not self._state.adding:
            previous = (
                Assignment.objects.only("status").get(pk=self.pk)
            )
            if (
                previous.status == self.AssignmentStatus.RETURNED
                and self.status != self.AssignmentStatus.RETURNED
            ):
                raise ValidationError(
                    {"status": "Returned assignments are immutable and cannot be reopened."}
                )
