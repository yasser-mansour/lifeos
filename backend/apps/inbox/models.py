from django.db import models

from apps.core.models import BaseModel


class InboxItem(BaseModel):
    content = models.TextField()
    processed = models.BooleanField(default=False)
    converted_to = models.CharField(max_length=20, blank=True, default="")
    converted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.content[:60]
