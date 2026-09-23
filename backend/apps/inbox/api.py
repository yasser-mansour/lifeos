from rest_framework import serializers, viewsets

from apps.inbox.models import InboxItem


class InboxItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InboxItem
        fields = ["id", "content", "processed", "converted_to", "converted_at", "created_at", "updated_at", "version"]
        read_only_fields = ["id", "created_at", "updated_at", "version"]


class InboxItemViewSet(viewsets.ModelViewSet):
    serializer_class = InboxItemSerializer
    queryset = InboxItem.objects.all()
