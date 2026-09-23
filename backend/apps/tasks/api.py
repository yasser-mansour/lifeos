from rest_framework import serializers, viewsets

from apps.tasks.models import Task


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            "id", "title", "description", "status", "priority", "due_date", "due_time", "start_date",
            "project", "course", "person", "tags", "estimated_minutes", "completed_at",
            "waiting_on", "waiting_for_person", "follow_up_date", "notes",
            "created_at", "updated_at", "version",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "version"]


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    queryset = Task.objects.all()
    filterset_fields = ["status", "priority", "project", "course"]
