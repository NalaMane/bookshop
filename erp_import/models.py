import re

from django.db import models

ROW_NUMBER = re.compile(r"^Row (\d+):")


class ImportLog(models.Model):
    """Lab 2 – one entry per ERP import (owner: Ami).

    Shows staff in /admin what happened: which file, when, how many products were
    created / updated, how many rows failed and why."""

    class Status(models.TextChoices):
        SUCCESS = "success", "Success"  # all rows imported
        PARTIAL = "partial", "Partial"  # some rows skipped because of errors
        FAILED = "failed", "Failed"  # nothing imported (invalid file or every row wrong)

    created_at = models.DateTimeField(auto_now_add=True)
    file_name = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=Status.choices)
    created_count = models.PositiveIntegerField("created", default=0)
    updated_count = models.PositiveIntegerField("updated", default=0)
    failed_count = models.PositiveIntegerField("failed rows", default=0)
    errors = models.JSONField(default=list, blank=True)  # list of error messages

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.file_name} ({self.get_status_display()}, {self.created_at:%d.%m.%Y %H:%M})"

    @classmethod
    def record(cls, file_name, created=0, updated=0, errors=None, file_error=None):
        """Save the result of one import and pick the right status.

        After a normal import:     ImportLog.record(name, created, updated, errors)
        If the file was rejected:  ImportLog.record(name, file_error="Required column(s) missing ...")
        """
        errors = list(errors or [])
        if file_error:
            return cls.objects.create(file_name=file_name, status=cls.Status.FAILED,
                                      failed_count=0, errors=[file_error])
        # one row can have several problems -> count each row only once
        failed = len({match.group(1) for match in map(ROW_NUMBER.match, errors) if match})
        if not errors:
            status = cls.Status.SUCCESS
        elif created or updated:
            status = cls.Status.PARTIAL
        else:
            status = cls.Status.FAILED
        return cls.objects.create(file_name=file_name, status=status, created_count=created,
                                  updated_count=updated, failed_count=failed, errors=errors)
