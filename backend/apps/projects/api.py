from rest_framework import serializers, viewsets

from apps.projects.models import Project


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "name", "description", "area", "status", "priority", "start_date", "target_date", "archived", "people", "created_at", "updated_at", "version"]
        read_only_fields = ["id", "created_at", "updated_at", "version"]


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    queryset = Project.objects.all()
