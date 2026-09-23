from django.db import models

from apps.core.models import BaseModel, Tag

# Multi-dimensional by design (spec §4/§5 of the Finance V2 mandate) — an
# entity can carry more than one of these at once (Heroku is just
# "service_provider"; a school can be both "client" AND "service_provider" if
# you're also paying them tuition while they pay you for tutoring). There is
# deliberately no separate CUSTOMER_DIRECTION enum: "they pay me" vs "I pay
# them" is answered by which of these tags are present plus the real
# transaction history (see apps.finance.services.counterparty_summary), not
# by a second field that could disagree with the first.
RELATIONSHIP_CHOICES = [
    ("client", "Client"),
    ("prospect", "Prospect"),
    ("service_provider", "Service Provider"),
    ("supplier", "Supplier"),
    ("employer_payer", "Employer / Payer"),
    ("friend", "Friend"),
    ("family", "Family"),
    ("teacher", "Teacher"),
    ("school", "School"),
    ("bank", "Bank"),
    ("landlord", "Landlord"),
    ("platform", "Platform"),
    ("partner", "Partner"),
    ("collaborator", "Collaborator"),
    ("contact", "Contact"),
    ("other", "Other"),
]


class RelationshipLabelMixin:
    """Shared by Person and Organization — both carry the same free-form,
    multi-select relationship vocabulary above (spec §3/§4: one entity type
    enum each, but relationships are a separate, multi-valued dimension)."""

    @property
    def relationship_labels(self):
        mapping = dict(RELATIONSHIP_CHOICES)
        return [mapping.get(r, r) for r in self.relationship_types]

    @property
    def is_client(self):
        return "client" in self.relationship_types


class Person(RelationshipLabelMixin, BaseModel):
    name = models.CharField(max_length=150)
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=40, blank=True, default="")
    organization = models.CharField(max_length=150, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    relationship_types = models.JSONField(default=list, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="people")
    next_follow_up = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("people:detail", args=[self.pk])


class Organization(RelationshipLabelMixin, BaseModel):
    """The other half of "People & Organizations" (spec §2/§3): Heroku, a
    bank, a school-as-an-institution, a landlord company — entities you deal
    with financially that are not a person and shouldn't be forced into a
    fake first/last name. Deliberately a separate model rather than a
    "is_organization" flag bolted onto Person: the field sets genuinely
    differ (a website instead of an email-only contact, a category instead
    of an employer), and every existing Person row/FK stays completely
    untouched by this addition."""

    CATEGORY_CHOICES = [
        ("saas", "SaaS / Software"),
        ("hosting", "Hosting / Infrastructure"),
        ("bank", "Bank"),
        ("telecom", "Telecom / Internet"),
        ("school", "School / University"),
        ("landlord", "Landlord"),
        ("supplier", "Supplier"),
        ("client_org", "Client Organization"),
        ("government", "Government / Administration"),
        ("other", "Other"),
    ]

    name = models.CharField(max_length=150)
    website = models.URLField(blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=40, blank=True, default="")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="other")
    notes = models.TextField(blank=True, default="")
    relationship_types = models.JSONField(default=list, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="organizations")
    archived = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("people:org_detail", args=[self.pk])
