from rest_framework import serializers, viewsets

from apps.devices.sync import ConflictAwareUpdateMixin
from apps.journal.models import JournalEntry


class JournalEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalEntry
        fields = ["id", "date", "title", "body", "mood", "tags", "created_at", "updated_at", "version"]
        read_only_fields = ["id", "created_at", "updated_at", "version"]


class JournalEntryViewSet(ConflictAwareUpdateMixin, viewsets.ModelViewSet):
    serializer_class = JournalEntrySerializer
    queryset = JournalEntry.objects.all()
    conflict_entity_type = "journal_entry"
