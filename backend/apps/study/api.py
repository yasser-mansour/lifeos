from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.devices.auth import request_device as _request_device
from apps.devices.sync import ConflictAwareUpdateMixin
from apps.study import services
from apps.study.models import StudyGoal, StudySession, StudySessionEvent


class StudySessionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudySessionEvent
        fields = ["id", "session", "event_type", "timestamp", "device", "metadata"]
        read_only_fields = ["id"]


class StudySessionSerializer(serializers.ModelSerializer):
    events = StudySessionEventSerializer(many=True, read_only=True)
    duration_seconds = serializers.ReadOnlyField()
    remaining_seconds = serializers.ReadOnlyField()

    class Meta:
        model = StudySession
        fields = [
            "id", "domain", "course", "topic", "task", "project", "book", "mode", "status",
            "planned_duration_seconds", "pomodoro_focus_seconds", "pomodoro_short_break_seconds",
            "pomodoro_long_break_seconds", "pomodoro_cycles_before_long_break", "current_phase",
            "completed_focus_cycles", "started_at", "ended_at", "origin_device", "ending_device",
            "corrected_duration_seconds", "correction_reason", "notes", "duration_seconds",
            "remaining_seconds", "events", "created_at", "updated_at", "version",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "version", "duration_seconds", "remaining_seconds"]


class StudyGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyGoal
        fields = ["id", "period", "target_seconds", "active"]
        read_only_fields = ["id"]


class StudySessionViewSet(ConflictAwareUpdateMixin, viewsets.ModelViewSet):
    serializer_class = StudySessionSerializer
    queryset = StudySession.objects.all()
    filterset_fields = ["domain", "course", "project", "task", "book", "status", "mode"]
    conflict_entity_type = "study_session"

    def create(self, request, *args, **kwargs):
        session = self._start_from_request(request)
        return Response(self.get_serializer(session).data, status=201)

    def _start_from_request(self, request):
        data = request.data
        from apps.projects.models import Project
        from apps.school.models import Course, Topic
        from apps.tasks.models import Task
        from apps.writing.models import Book

        def _get(model, key):
            value = data.get(key)
            return model.objects.filter(pk=value).first() if value else None

        device = _request_device(request)
        return services.start_session(
            client_id=data.get("id"),
            domain=data.get("domain", "other"),
            course=_get(Course, "course"),
            topic=_get(Topic, "topic"),
            task=_get(Task, "task"),
            project=_get(Project, "project"),
            book=_get(Book, "book"),
            mode=data.get("mode", "stopwatch"),
            planned_duration_seconds=data.get("planned_duration_seconds") or None,
            device=device,
        )

    @action(detail=False, methods=["get"])
    def active(self, request):
        session = services.active_session()
        if not session:
            return Response(None)
        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        device = _request_device(request)
        # phase: a Pomodoro client pauses to end one phase and resumes to
        # start the next (see StudySessionSerializer's current_phase) — the
        # service already accepted this kwarg, but nothing ever passed it
        # through, so no client's Pomodoro phase transitions ever reached
        # the server via the API (only the desktop web UI's own form-post
        # start/finish views did).
        session = services.pause_session(self.get_object(), device=device, phase=request.data.get("phase"))
        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        device = _request_device(request)
        session = services.resume_session(self.get_object(), device=device, phase=request.data.get("phase"))
        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=["post"])
    def finish(self, request, pk=None):
        device = _request_device(request)
        session = services.finish_session(self.get_object(), device=device)
        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        device = _request_device(request)
        session = services.cancel_session(self.get_object(), device=device)
        return Response(self.get_serializer(session).data)


class StudyGoalViewSet(viewsets.ModelViewSet):
    serializer_class = StudyGoalSerializer
    queryset = StudyGoal.objects.all()
