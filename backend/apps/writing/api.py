from rest_framework import serializers, viewsets

from apps.devices.sync import ConflictAwareUpdateMixin
from apps.writing.models import Book, Chapter


class ChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = ["id", "book", "title", "order", "content", "status", "word_count", "created_at", "updated_at", "version"]
        read_only_fields = ["id", "word_count", "created_at", "updated_at", "version"]


class BookSerializer(serializers.ModelSerializer):
    chapters = ChapterSerializer(many=True, read_only=True)
    total_word_count = serializers.ReadOnlyField()

    class Meta:
        model = Book
        fields = ["id", "title", "description", "status", "chapters", "total_word_count", "created_at", "updated_at", "version"]
        read_only_fields = ["id", "created_at", "updated_at", "version"]


class BookViewSet(viewsets.ModelViewSet):
    serializer_class = BookSerializer
    queryset = Book.objects.all()


class ChapterViewSet(ConflictAwareUpdateMixin, viewsets.ModelViewSet):
    serializer_class = ChapterSerializer
    queryset = Chapter.objects.all()
    conflict_entity_type = "chapter"
