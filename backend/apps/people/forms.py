from django import forms

from apps.core.base_forms import StyledModelForm
from apps.people.models import RELATIONSHIP_CHOICES, Organization, Person


class PersonForm(StyledModelForm):
    relationship_types = forms.MultipleChoiceField(choices=RELATIONSHIP_CHOICES, required=False, widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = Person
        fields = ["name", "email", "phone", "organization", "relationship_types", "notes", "next_follow_up"]
        widgets = {"next_follow_up": forms.DateInput(attrs={"type": "date"})}


class OrganizationForm(StyledModelForm):
    relationship_types = forms.MultipleChoiceField(choices=RELATIONSHIP_CHOICES, required=False, widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = Organization
        fields = ["name", "category", "website", "email", "phone", "relationship_types", "notes"]
