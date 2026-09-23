from django.contrib import admin

from apps.people.models import Organization, Person


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "email", "relationship_types")
    search_fields = ("name", "organization", "email")


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "relationship_types", "archived")
    search_fields = ("name", "website", "email")
    list_filter = ("category", "archived")
