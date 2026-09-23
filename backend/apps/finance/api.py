from decimal import Decimal

from rest_framework import serializers, viewsets

from apps.devices.sync import ConflictAwareUpdateMixin, DeletionAwareSyncMixin
from apps.finance.models import Account, Allocation, Budget, Category, Fund, RecurringCommitment, Transaction, Transfer
from apps.finance.services import account_balance, create_transfer, fund_balance


def _deleted(obj):
    """A device's incremental pull (?modified_since=...) needs to tell a
    genuine update apart from a tombstone — see DeletionAwareSyncMixin."""
    return obj.deleted_at is not None


class AccountSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()
    deleted = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = ["id", "name", "institution", "account_type", "context", "currency", "opening_balance", "balance", "notes", "active", "archived", "created_at", "updated_at", "version", "deleted"]
        read_only_fields = ["id", "created_at", "updated_at", "version", "deleted"]

    def get_balance(self, obj):
        # A soft-deleted account has no meaningful balance to compute (its
        # transactions/transfers may themselves be in a torn-down state) —
        # only ever called for a live account in practice, but stay safe.
        return str(account_balance(obj)) if obj.deleted_at is None else "0"

    def get_deleted(self, obj):
        return _deleted(obj)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "color", "context", "is_custom", "archived"]


class FundSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()
    deleted = serializers.SerializerMethodField()

    class Meta:
        model = Fund
        fields = ["id", "name", "context", "project", "notes", "archived", "balance", "created_at", "updated_at", "version", "deleted"]
        read_only_fields = ["id", "created_at", "updated_at", "version", "deleted"]

    def get_balance(self, obj):
        return str(fund_balance(obj)) if obj.deleted_at is None else "0"

    def get_deleted(self, obj):
        return _deleted(obj)


class AllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Allocation
        fields = ["id", "transaction", "category", "amount", "period", "description"]
        read_only_fields = ["id"]


class TransactionSerializer(serializers.ModelSerializer):
    allocations = AllocationSerializer(many=True, read_only=True)
    deleted = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            "id", "account", "fund", "amount", "currency", "type", "direction", "date", "category", "description",
            "project", "person", "organization", "tags", "notes", "refund_of", "recurring_commitment", "allocations",
            "created_at", "updated_at", "version", "deleted",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "version", "deleted"]

    def validate_amount(self, value):
        if value < Decimal("0"):
            raise serializers.ValidationError("Amount must be positive — type/direction controls the sign.")
        return value

    def get_deleted(self, obj):
        return _deleted(obj)


class TransferSerializer(serializers.ModelSerializer):
    deleted = serializers.SerializerMethodField()

    class Meta:
        model = Transfer
        fields = [
            "id", "from_account", "to_account", "from_fund", "to_fund", "amount", "currency", "date", "description", "notes",
            "created_at", "updated_at", "version", "deleted",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "version", "deleted"]

    def get_deleted(self, obj):
        return _deleted(obj)

    def validate(self, attrs):
        # Mirrors Transfer.clean() (Finance V2 spec §58): a same-account
        # transfer is fine as long as the Fund actually changes — that's a
        # logical transfer, e.g. taking project profit into a personal fund
        # without the money physically moving anywhere.
        accounts_differ = attrs.get("from_account") and attrs.get("to_account") and attrs["from_account"] != attrs["to_account"]
        funds_differ = attrs.get("from_fund") != attrs.get("to_fund")
        if not accounts_differ and not funds_differ:
            raise serializers.ValidationError("A transfer needs to actually move something — a different account, a different fund, or both.")
        return attrs

    def create(self, validated_data):
        return create_transfer(**validated_data)


class RecurringCommitmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurringCommitment
        fields = [
            "id", "name", "account", "fund", "amount", "currency", "category", "frequency", "custom_interval_days",
            "next_due_date", "project", "person", "organization", "context", "is_income", "active", "notes",
        ]
        read_only_fields = ["id"]


class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = ["id", "category", "amount", "month", "context"]
        read_only_fields = ["id"]


class AccountViewSet(DeletionAwareSyncMixin, viewsets.ModelViewSet):
    serializer_class = AccountSerializer
    queryset = Account.objects.all()


class FundViewSet(DeletionAwareSyncMixin, viewsets.ModelViewSet):
    serializer_class = FundSerializer
    queryset = Fund.objects.all()


class TransactionViewSet(DeletionAwareSyncMixin, ConflictAwareUpdateMixin, viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    queryset = Transaction.objects.all()
    filterset_fields = ["account", "type", "category", "project", "person"]
    conflict_entity_type = "transaction"


class TransferViewSet(DeletionAwareSyncMixin, viewsets.ModelViewSet):
    serializer_class = TransferSerializer
    queryset = Transfer.objects.all()


class RecurringCommitmentViewSet(viewsets.ModelViewSet):
    serializer_class = RecurringCommitmentSerializer
    queryset = RecurringCommitment.objects.all()


class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    queryset = Budget.objects.all()


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    queryset = Category.objects.all()
