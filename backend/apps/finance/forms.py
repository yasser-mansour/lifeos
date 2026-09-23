from django import forms
from django.forms import inlineformset_factory

from apps.core.base_forms import StyledModelForm
from apps.finance.models import Account, Allocation, Budget, Category, Fund, RecurringCommitment, Transaction, Transfer
from apps.people.models import Organization, Person


class AccountForm(StyledModelForm):
    class Meta:
        model = Account
        fields = ["name", "institution", "account_type", "context", "currency", "opening_balance", "notes"]


class TransactionForm(StyledModelForm):
    # Both kept as separate, optional pickers (spec §9: Counterparty is one
    # concept but Person/Organization stay two real FKs — see
    # Transaction.counterparty) rather than one combined field, since a
    # single <select> spanning two querysets needs a custom widget for
    # limited payoff at this form's size.
    person = forms.ModelChoiceField(queryset=Person.objects.all(), required=False, label="Counterparty (person)")
    organization = forms.ModelChoiceField(queryset=Organization.objects.filter(archived=False), required=False, label="Counterparty (organization)")

    class Meta:
        model = Transaction
        fields = ["amount", "type", "direction", "account", "fund", "category", "description", "date", "project", "person", "organization", "tags", "notes"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"}), "notes": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].required = False
        self.fields["category"].queryset = Category.objects.filter(archived=False)
        self.fields["fund"].required = False
        self.fields["fund"].queryset = Fund.objects.filter(archived=False)
        self.fields["direction"].label = "Direction (adjustment / other only)"

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("person") and cleaned.get("organization"):
            raise forms.ValidationError("Choose either a person or an organization as the counterparty, not both.")
        return cleaned


AllocationFormSet = inlineformset_factory(
    Transaction,
    Allocation,
    fields=["amount", "category", "period", "description"],
    extra=0,
    can_delete=True,
    widgets={"period": forms.DateInput(attrs={"type": "date", "class": "input"}), "amount": forms.NumberInput(attrs={"class": "input", "step": "0.01"}), "description": forms.TextInput(attrs={"class": "input"})},
)


class TransferForm(StyledModelForm):
    """One form for all three transfer kinds (spec §58) — from_fund/to_fund
    are optional, so leaving both blank is an ordinary account-to-account
    transfer exactly as before this field existed."""

    class Meta:
        model = Transfer
        fields = ["from_account", "to_account", "from_fund", "to_fund", "amount", "currency", "date", "description", "notes"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ("from_fund", "to_fund"):
            self.fields[field].required = False
            self.fields[field].queryset = Fund.objects.filter(archived=False)

    def clean(self):
        cleaned = super().clean()
        from_account, to_account = cleaned.get("from_account"), cleaned.get("to_account")
        from_fund, to_fund = cleaned.get("from_fund"), cleaned.get("to_fund")
        accounts_differ = bool(from_account) and bool(to_account) and from_account.pk != to_account.pk
        funds_differ = from_fund != to_fund
        if not accounts_differ and not funds_differ:
            raise forms.ValidationError("A transfer needs to actually move something — a different account, a different fund, or both.")
        return cleaned


class RecurringCommitmentForm(StyledModelForm):
    person = forms.ModelChoiceField(queryset=Person.objects.all(), required=False, label="Counterparty (person)")
    organization = forms.ModelChoiceField(queryset=Organization.objects.filter(archived=False), required=False, label="Counterparty (organization)")

    class Meta:
        model = RecurringCommitment
        fields = ["name", "account", "fund", "amount", "category", "frequency", "next_due_date", "context", "is_income", "project", "person", "organization", "notes"]
        widgets = {"next_due_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fund"].required = False
        self.fields["fund"].queryset = Fund.objects.filter(archived=False)
        self.fields["category"].queryset = Category.objects.filter(archived=False)


class BudgetForm(StyledModelForm):
    class Meta:
        model = Budget
        fields = ["category", "amount", "month", "context"]
        widgets = {"month": forms.DateInput(attrs={"type": "date"})}


class CategoryForm(StyledModelForm):
    class Meta:
        model = Category
        fields = ["name", "color", "context"]
        widgets = {"color": forms.TextInput(attrs={"type": "color"})}


class FundForm(StyledModelForm):
    class Meta:
        model = Fund
        fields = ["name", "context", "project", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.projects.models import Project

        self.fields["project"].required = False
        self.fields["project"].queryset = Project.objects.filter(archived=False)
