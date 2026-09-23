from rest_framework import serializers, viewsets

from apps.goals.models import Goal


class GoalSerializer(serializers.ModelSerializer):
    effective_current_value = serializers.ReadOnlyField()
    progress_percent = serializers.ReadOnlyField()

    class Meta:
        model = Goal
        fields = [
            "id", "title", "description", "goal_type", "target_value", "current_value", "unit", "deadline",
            "status", "project", "course", "derive_from_study_hours", "effective_current_value", "progress_percent",
            "created_at", "updated_at", "version",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "version"]


class GoalViewSet(viewsets.ModelViewSet):
    serializer_class = GoalSerializer
    queryset = Goal.objects.all()
