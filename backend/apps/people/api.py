from rest_framework import serializers, viewsets

from apps.devices.sync import DeletionAwareSyncMixin
from apps.people.models import Organization, Person


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = ["id", "name", "email", "phone", "organization", "notes", "relationship_types", "next_follow_up", "created_at", "updated_at", "version"]
        read_only_fields = ["id", "created_at", "updated_at", "version"]


class OrganizationSerializer(serializers.ModelSerializer):
    deleted = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ["id", "name", "website", "email", "phone", "category", "notes", "relationship_types", "archived", "created_at", "updated_at", "version", "deleted"]
        read_only_fields = ["id", "created_at", "updated_at", "version", "deleted"]

    def get_deleted(self, obj):
        return obj.deleted_at is not None


class PersonViewSet(viewsets.ModelViewSet):
    serializer_class = PersonSerializer
    queryset = Person.objects.all()


class OrganizationViewSet(DeletionAwareSyncMixin, viewsets.ModelViewSet):
    serializer_class = OrganizationSerializer
    queryset = Organization.objects.all()
