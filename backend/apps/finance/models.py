from decimal import Decimal

from django.db import models

from apps.core.models import BaseModel, Tag
from apps.people.models import Organization, Person
from apps.projects.models import Project

ACCOUNT_TYPE_CHOICES = [
    ("bank", "Bank"),
    ("cash", "Cash"),
    ("savings", "Savings"),
    ("wallet", "Wallet"),
    ("investment", "Investment"),
    ("other", "Other"),
]

ACCOUNT_CONTEXT_CHOICES = [
    ("personal", "Personal"),
    ("business", "Business"),
    ("shared", "Shared"),
    ("other", "Other"),
]

# Every Transaction type maps to a fixed cash-flow sign, EXCEPT "adjustment"
# and "other" whose sign is ambiguous by nature and comes from the explicit
# `direction` field instead. This mapping is the single source of truth for
# balance math — see apps.finance.services.account_balance.
TRANSACTION_TYPE_CHOICES = [
    ("expense", "Expense"),
    ("income", "Income"),
    ("refund", "Refund"),
    ("loan_given", "Loan Given"),
    ("loan_received", "Loan Received"),
    ("deposit_paid", "Refundable Deposit Paid"),
    ("deposit_returned", "Deposit Returned"),
    ("withdrawal", "Withdrawal"),
    ("investment", "Investment"),
    ("reimbursement", "Reimbursement"),
    ("adjustment", "Adjustment"),
    ("other", "Other"),
]

FIXED_SIGN_BY_TYPE = {
    "expense": -1,
    "income": 1,
    "refund": 1,
    "loan_given": -1,
    "loan_received": 1,
    "deposit_paid": -1,
    "deposit_returned": 1,
    "withdrawal": -1,
    "investment": -1,
    "reimbursement": 1,
}

# Types that represent real consumption/earning and therefore belong in
# expense/income statistics and budgets. Loans, deposits and investments are
# balance-sheet-like (they change what you own, not what you spent) and are
# deliberately excluded — see docs/FINANCE.md "What counts as spending".
EXPENSE_LIKE_TYPES = {"expense", "refund"}  # refund nets *against* expense
INCOME_LIKE_TYPES = {"income"}

DIRECTION_CHOICES = [("in", "In"), ("out", "Out")]


class Account(BaseModel):
    name = models.CharField(max_length=100)
    institution = models.CharField(max_length=100, blank=True, default="")
    account_type = models.CharField(max_length=12, choices=ACCOUNT_TYPE_CHOICES, default="bank")
    context = models.CharField(max_length=10, choices=ACCOUNT_CONTEXT_CHOICES, default="personal")
    currency = models.CharField(max_length=3, default="MAD")
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    notes = models.TextField(blank=True, default="")
    active = models.BooleanField(default=True)
    archived = models.BooleanField(default=False)

    class Meta:
        ordering = ["context", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("finance:account_detail", args=[self.pk])

    @property
    def balance(self):
        from apps.finance.services import account_balance

        return account_balance(self)


CATEGORY_CONTEXT_CHOICES = [("personal", "Personal"), ("business", "Business"), ("both", "Both")]


class Category(models.Model):
    # Kept on its original integer PK / plain Model base rather than moved
    # onto BaseModel's UUID PK (spec §50 only asks for create/rename/
    # archive, not a UUID) — there are zero Category rows in production as
    # of this change, so there's no real data at risk either way, but
    # migrating every FK that points at it (Transaction, Allocation,
    # RecurringCommitment, Budget) for no functional gain is exactly the
    # kind of unnecessary structural churn spec §0 warns against.
    name = models.CharField(max_length=60, unique=True)
    color = models.CharField(max_length=7, default="#8A5FD1")
    context = models.CharField(max_length=10, choices=CATEGORY_CONTEXT_CHOICES, default="both")
    is_custom = models.BooleanField(default=True)
    archived = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Fund(BaseModel):
    """What the money is *for*, as distinct from where it physically sits
    (Account) — Finance V2 spec §14/§15/§16: "Living", "Family Support",
    "Project Profits" inside the same bank account, or a per-project fund
    like "Northstar" alongside its own project fields. Deliberately additive
    and optional everywhere it's referenced (Transaction.fund,
    Transfer.from_fund/to_fund are all nullable): a Fund with no
    Transactions pointing at it is simply empty, and a Transaction with no
    Fund is not an error — it reads as "Unallocated" (spec §71), never a
    materialized row of that name. There is deliberately no separate
    AccountFundBalance/allocation cache table (spec §56 offers one as an
    option, not a mandate) — see apps.finance.services.fund_balance and
    account_fund_breakdown, which reconstruct every number from Transaction/
    Transfer rows the same way account_balance() already does, so a Fund's
    balance can never drift from the ledger that produced it.
    """

    name = models.CharField(max_length=100)
    context = models.CharField(max_length=10, choices=ACCOUNT_CONTEXT_CHOICES, default="personal")
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL, related_name="funds")
    notes = models.TextField(blank=True, default="")
    archived = models.BooleanField(default=False)

    class Meta:
        ordering = ["context", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("finance:fund_detail", args=[self.pk])

    @property
    def balance(self):
        from apps.finance.services import fund_balance

        return fund_balance(self)


class Transaction(BaseModel):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=14, decimal_places=2)  # always stored positive; sign derived from type
    currency = models.CharField(max_length=3, default="MAD")
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES, default="expense")
    direction = models.CharField(max_length=3, choices=DIRECTION_CHOICES, default="out")
    date = models.DateField()
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")
    description = models.CharField(max_length=255, blank=True, default="")
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")
    fund = models.ForeignKey(Fund, null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")
    # Both kept, both optional, exactly one normally set — see Person/
    # Organization docstrings. `person` is the original, untouched field
    # (real production data already points at it); `organization` is new.
    # A property below (`counterparty`) reads whichever is set so callers
    # don't need to check both everywhere.
    person = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")
    tags = models.ManyToManyField(Tag, blank=True, related_name="transactions")
    notes = models.TextField(blank=True, default="")
    refund_of = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="refunds")
    recurring_commitment = models.ForeignKey("finance.RecurringCommitment", null=True, blank=True, on_delete=models.SET_NULL, related_name="actual_transactions")

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.get_type_display()} {self.amount} {self.currency}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.amount is not None and self.amount < 0:
            raise ValidationError({"amount": "Amount must be positive — direction/type controls the sign."})
        if self.person_id and self.organization_id:
            raise ValidationError({"organization": "Choose either a person or an organization, not both — pick whichever this money actually moved with."})

    @property
    def signed_amount(self) -> Decimal:
        sign = FIXED_SIGN_BY_TYPE.get(self.type)
        if sign is None:
            sign = 1 if self.direction == "in" else -1
        return sign * self.amount

    @property
    def is_expense_like(self):
        return self.type in EXPENSE_LIKE_TYPES

    @property
    def counterparty(self):
        """Whichever of person/organization is actually set (spec §8's
        optional "Counterparty" on a transaction) — reads as one concept
        without a schema-level union type. None if neither is linked."""
        return self.person or self.organization

    @property
    def allocated_total(self) -> Decimal:
        return sum((a.amount for a in self.allocations.all()), Decimal("0.00"))

    @property
    def is_fully_allocated(self):
        allocations = list(self.allocations.all())
        if not allocations:
            return False
        return sum((a.amount for a in allocations), Decimal("0.00")) == self.amount


class Allocation(BaseModel):
    """Splits a single transaction's amount across reporting periods and/or
    categories without inventing extra cash movements. Powers both advance
    payments (spread across months) and multi-purpose payments (split across
    categories) — the same mechanism serves both, see docs/FINANCE.md."""

    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name="allocations")
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="allocations")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    period = models.DateField(help_text="First day of the month/period this slice reports against.")
    description = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["period"]

    def __str__(self):
        return f"{self.amount} → {self.period:%b %Y}"


class Transfer(BaseModel):
    """A movement of money between two of the user's own accounts, funds, or
    both. Never materialized as expense+income Transaction rows (see spec
    §30) — a single row here is atomic by construction, and stays that way
    now that a Transfer can move a Fund instead of (or in addition to) an
    Account (Finance V2 spec §58/§59-61: physical, logical, and combined
    transfers, one engine, one history table). `from_fund`/`to_fund` are
    both optional — an ordinary bank↔cash transfer leaves them null and
    behaves exactly as before this change; a project→personal profit
    withdrawal sets from_fund/to_fund and can leave from_account/to_account
    identical (spec §60/§95: physical money doesn't have to move at all)."""

    from_account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="transfers_out")
    to_account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="transfers_in")
    from_fund = models.ForeignKey(Fund, null=True, blank=True, on_delete=models.SET_NULL, related_name="fund_transfers_out")
    to_fund = models.ForeignKey(Fund, null=True, blank=True, on_delete=models.SET_NULL, related_name="fund_transfers_in")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="MAD")
    date = models.DateField()
    description = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.from_account} → {self.to_account}: {self.amount}"

    def clean(self):
        from django.core.exceptions import ValidationError

        accounts_differ = bool(self.from_account_id) and bool(self.to_account_id) and self.from_account_id != self.to_account_id
        funds_differ = self.from_fund_id != self.to_fund_id
        if not accounts_differ and not funds_differ:
            raise ValidationError("A transfer needs to actually move something — a different account, a different fund, or both.")

    @property
    def transfer_kind(self):
        """Which of the three kinds this is (spec §58) — purely descriptive,
        used by templates so the user always knows what actually moved."""
        accounts_differ = self.from_account_id != self.to_account_id
        funds_differ = self.from_fund_id != self.to_fund_id
        if accounts_differ and funds_differ:
            return "combined"
        if funds_differ:
            return "logical"
        return "physical"


class RecurringCommitment(BaseModel):
    FREQUENCY_CHOICES = [("weekly", "Weekly"), ("monthly", "Monthly"), ("yearly", "Yearly"), ("custom", "Custom")]

    name = models.CharField(max_length=150)
    account = models.ForeignKey(Account, null=True, blank=True, on_delete=models.SET_NULL, related_name="recurring_commitments")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="MAD")
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="recurring_commitments")
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default="monthly")
    custom_interval_days = models.PositiveIntegerField(null=True, blank=True)
    next_due_date = models.DateField()
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL, related_name="recurring_commitments")
    fund = models.ForeignKey(Fund, null=True, blank=True, on_delete=models.SET_NULL, related_name="recurring_commitments")
    person = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL, related_name="recurring_commitments")
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL, related_name="recurring_commitments")
    context = models.CharField(max_length=10, choices=ACCOUNT_CONTEXT_CHOICES, default="personal")
    is_income = models.BooleanField(default=False, help_text="Recurring revenue (e.g. a retainer) instead of an outgoing commitment.")
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["next_due_date"]

    def __str__(self):
        return self.name

    @property
    def counterparty(self):
        return self.person or self.organization

    def advance_due_date(self):
        from datetime import timedelta

        from dateutil.relativedelta import relativedelta

        if self.frequency == "weekly":
            self.next_due_date += timedelta(weeks=1)
        elif self.frequency == "monthly":
            self.next_due_date += relativedelta(months=1)
        elif self.frequency == "yearly":
            self.next_due_date += relativedelta(years=1)
        else:
            self.next_due_date += timedelta(days=self.custom_interval_days or 30)
        self.save(update_fields=["next_due_date"])


class Budget(BaseModel):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="budgets")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    month = models.DateField(help_text="First day of the budgeted month.")
    context = models.CharField(max_length=10, choices=ACCOUNT_CONTEXT_CHOICES, default="personal")

    class Meta:
        ordering = ["-month"]
        unique_together = ["category", "month", "context"]

    def __str__(self):
        return f"{self.category} — {self.month:%b %Y}"


class Card(BaseModel):
    """Deliberately safe metadata only. No CVV, PIN, password, OTP, or full
    card number is ever stored — see docs/SECURITY.md "Cards"."""

    CARD_TYPE_CHOICES = [("debit", "Debit"), ("credit", "Credit"), ("prepaid", "Prepaid"), ("other", "Other")]

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="cards")
    nickname = models.CharField(max_length=100)
    last_four = models.CharField(max_length=4, blank=True, default="")
    card_type = models.CharField(max_length=10, choices=CARD_TYPE_CHOICES, default="debit")
    expiry_month = models.PositiveSmallIntegerField(null=True, blank=True)
    expiry_year = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.nickname} •••• {self.last_four}"
