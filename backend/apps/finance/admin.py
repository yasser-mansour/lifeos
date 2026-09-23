from django.contrib import admin

from apps.finance.models import Account, Allocation, Budget, Card, Category, Fund, RecurringCommitment, Transaction, Transfer


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("name", "context", "account_type", "currency", "opening_balance", "active")
    list_filter = ("context", "account_type")


@admin.register(Fund)
class FundAdmin(admin.ModelAdmin):
    list_display = ("name", "context", "project", "archived")
    list_filter = ("context", "archived")


class AllocationInline(admin.TabularInline):
    model = Allocation
    extra = 0


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("date", "type", "amount", "currency", "account", "category")
    list_filter = ("type", "account")
    date_hierarchy = "date"
    inlines = [AllocationInline]


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ("date", "from_account", "to_account", "from_fund", "to_fund", "amount", "currency")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "context", "is_custom", "archived")


@admin.register(RecurringCommitment)
class RecurringCommitmentAdmin(admin.ModelAdmin):
    list_display = ("name", "amount", "frequency", "next_due_date", "context", "active")


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("category", "month", "amount", "context")


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("nickname", "account", "last_four", "card_type")
