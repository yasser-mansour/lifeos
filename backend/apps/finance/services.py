"""Finance correctness lives here — see docs/FINANCE.md. The guiding rule
(spec §23): record what actually happened first, interpret it second. Every
function below derives its answer from Transaction/Transfer rows rather than
trusting a cached field, so the numbers are always reconstructible."""

from decimal import Decimal

from django.db import models
from django.db import transaction as db_transaction
from django.utils import timezone

from apps.finance.models import (
    ACCOUNT_TYPE_CHOICES,
    EXPENSE_LIKE_TYPES,
    INCOME_LIKE_TYPES,
    Account,
    Allocation,
    Budget,
    Fund,
    RecurringCommitment,
    Transaction,
    Transfer,
)

ZERO = Decimal("0.00")


def account_balance(account: Account) -> Decimal:
    balance = account.opening_balance
    for txn in Transaction.objects.filter(account=account).only("amount", "type", "direction"):
        balance += txn.signed_amount
    transfers_out = Transfer.objects.filter(from_account=account).aggregate(total=_sum("amount"))["total"] or ZERO
    transfers_in = Transfer.objects.filter(to_account=account).aggregate(total=_sum("amount"))["total"] or ZERO
    balance += transfers_in - transfers_out
    return balance


def _sum(field):
    from django.db.models import Sum

    return Sum(field)


def create_transfer(*, from_account, to_account, amount, currency, date, description="", notes="", from_fund=None, to_fund=None):
    """The one engine behind every transfer kind (Finance V2 spec §58): pass
    only account args for a physical transfer (bank↔cash), only fund args
    with the same account on both sides for a logical one (project profit →
    personal, spec §60/§95 — physical money never has to move), or both for
    a combined transfer. Validation lives on Transfer.clean() itself
    (full_clean below) so there's exactly one place that decides whether a
    transfer "actually moves something" — see Transfer.clean()."""
    with db_transaction.atomic():
        transfer = Transfer(
            from_account=from_account, to_account=to_account, from_fund=from_fund, to_fund=to_fund,
            amount=amount, currency=currency, date=date, description=description, notes=notes,
        )
        transfer.full_clean()
        transfer.save()
        return transfer


# ---------------------------------------------------------------------------
# Funds — "what the money is for", as distinct from account_balance's "where
# the money is" (spec §14-16). Every function below reconstructs its answer
# from Transaction/Transfer rows exactly the way account_balance() does, so a
# Fund's number can never drift from the ledger and total money is
# preserved by construction: a Fund is just an extra tag on the same events
# that already determine account_balance(), never a second place money is
# recorded (see docs/FINANCE_V2.md "Why no AccountFundBalance table").
# ---------------------------------------------------------------------------


def fund_balance(fund: Fund) -> Decimal:
    balance = ZERO
    for txn in Transaction.objects.filter(fund=fund).only("amount", "type", "direction"):
        balance += txn.signed_amount
    transfers_in = Transfer.objects.filter(to_fund=fund).aggregate(total=_sum("amount"))["total"] or ZERO
    transfers_out = Transfer.objects.filter(from_fund=fund).aggregate(total=_sum("amount"))["total"] or ZERO
    balance += transfers_in - transfers_out
    return balance


def unallocated_balance(*, context=None) -> Decimal:
    """What's left in (optionally, one context's) active accounts once every
    Fund's own balance is subtracted out (spec §71-73's "Unallocated", never
    a materialized Fund row). Defined as the remainder rather than computed
    independently, so "total = allocated + unallocated" (spec §67) is true
    by construction rather than something that could quietly drift."""
    accounts = Account.objects.filter(active=True)
    funds = Fund.objects.filter(archived=False)
    if context:
        accounts = accounts.filter(context=context)
        funds = funds.filter(context=context)
    total = sum((account_balance(a) for a in accounts), ZERO)
    allocated = sum((fund_balance(f) for f in funds), ZERO)
    return total - allocated


def account_fund_breakdown(account: Account) -> dict:
    """Per spec §54 — how one physical Account's balance splits across the
    Funds that have touched it. Keys are Fund instances or None
    (Unallocated, which absorbs the account's opening_balance since that
    predates any Fund tagging); values always sum to account_balance(account)."""
    totals = {None: account.opening_balance}
    for txn in Transaction.objects.filter(account=account).select_related("fund"):
        totals[txn.fund] = totals.get(txn.fund, ZERO) + txn.signed_amount
    for t in Transfer.objects.filter(to_account=account).select_related("to_fund"):
        totals[t.to_fund] = totals.get(t.to_fund, ZERO) + t.amount
    for t in Transfer.objects.filter(from_account=account).select_related("from_fund"):
        totals[t.from_fund] = totals.get(t.from_fund, ZERO) - t.amount
    return {fund: amount for fund, amount in totals.items() if amount != ZERO or fund is None}


def fund_account_breakdown(fund: Fund) -> dict:
    """Per spec §55 — one Fund's balance split across the physical Accounts
    it's actually sitting in ("Stored in: CIH Bank 2,500, Cash 500"). Keys
    are Account instances; values always sum to fund_balance(fund)."""
    totals = {}
    for txn in Transaction.objects.filter(fund=fund).select_related("account"):
        totals[txn.account] = totals.get(txn.account, ZERO) + txn.signed_amount
    for t in Transfer.objects.filter(to_fund=fund).select_related("to_account"):
        totals[t.to_account] = totals.get(t.to_account, ZERO) + t.amount
    for t in Transfer.objects.filter(from_fund=fund).select_related("from_account"):
        totals[t.from_account] = totals.get(t.from_account, ZERO) - t.amount
    return {account: amount for account, amount in totals.items() if amount != ZERO}


def fund_activity(fund, limit=100):
    """Every transaction and transfer touching this Fund, newest first —
    same _merge_activity shape as account_activity, so a Fund detail page
    reads exactly like an Account detail page (spec §55)."""
    transactions = Transaction.objects.filter(fund=fund).select_related("account", "category", "project", "person", "organization")
    transfers_out = Transfer.objects.filter(from_fund=fund).select_related("to_fund", "from_account", "to_account")
    transfers_in = Transfer.objects.filter(to_fund=fund).select_related("from_fund", "from_account", "to_account")
    return _merge_activity(
        _transaction_events(transactions),
        _transfer_events(transfers_out, "transfer_out"),
        _transfer_events(transfers_in, "transfer_in"),
        limit=limit,
    )


def create_transaction_with_allocations(*, transaction_data, allocations_data=None):
    """Creates one Transaction and, optionally, its Allocation rows in a
    single atomic unit — either the whole advance payment records or none of
    it does (spec §31/§32)."""
    with db_transaction.atomic():
        txn = Transaction.objects.create(**transaction_data)
        for alloc in allocations_data or []:
            Allocation.objects.create(transaction=txn, **alloc)
        return txn


def equal_allocation_plan(total: Decimal, start_period, months: int):
    """Splits `total` into `months` equal slices (remainder absorbed by the
    last slice so the sum always matches exactly), one per month starting at
    start_period."""
    from dateutil.relativedelta import relativedelta

    if months < 1:
        raise ValueError("months must be >= 1")
    base = (total / months).quantize(Decimal("0.01"))
    plan = []
    running = ZERO
    for i in range(months):
        period = start_period + relativedelta(months=i)
        amount = base
        if i == months - 1:
            amount = total - running
        running += amount
        plan.append({"period": period, "amount": amount})
    return plan


def period_expense_totals(*, start_date, end_date, context=None):
    """Category → net expense (expense - refund) between two dates."""
    qs = Transaction.objects.filter(date__gte=start_date, date__lte=end_date, type__in=EXPENSE_LIKE_TYPES)
    if context:
        qs = qs.filter(account__context=context)
    totals = {}
    for txn in qs.select_related("category"):
        key = txn.category
        totals.setdefault(key, ZERO)
        totals[key] += txn.signed_amount  # expense negative, refund positive → nets correctly
    return {cat: -amount for cat, amount in totals.items()}  # flip to positive "amount spent"


def budget_progress(budget: Budget):
    from calendar import monthrange

    start = budget.month.replace(day=1)
    end = budget.month.replace(day=monthrange(budget.month.year, budget.month.month)[1])
    qs = Transaction.objects.filter(category=budget.category, date__gte=start, date__lte=end, type__in=EXPENSE_LIKE_TYPES, account__context=budget.context)
    actual = -sum((t.signed_amount for t in qs), ZERO)
    remaining = budget.amount - actual
    percent = int(min(100, max(0, (actual / budget.amount) * 100))) if budget.amount else 0
    return {"planned": budget.amount, "actual": actual, "remaining": remaining, "percent": percent}


def upcoming_recurring(*, within_days=30, context=None):
    horizon = timezone.localdate() + timezone.timedelta(days=within_days)
    qs = RecurringCommitment.objects.filter(active=True, next_due_date__lte=horizon).order_by("next_due_date")
    if context:
        qs = qs.filter(context=context)
    return qs


def safe_to_spend(profile, *, context="personal"):
    accounts = Account.objects.filter(context=context, active=True)
    liquid_balance = sum((account_balance(a) for a in accounts), ZERO)
    horizon = profile.safe_to_spend_horizon_days
    expected = upcoming_recurring(within_days=horizon, context=context)
    expected_total = sum((r.amount for r in expected if not r.is_income), ZERO)
    return {
        "liquid_balance": liquid_balance,
        "expected_commitments": expected_total,
        "reserved": profile.safe_to_spend_reserve,
        "safe_to_spend": liquid_balance - expected_total - profile.safe_to_spend_reserve,
        "horizon_days": horizon,
    }


def _merge_activity(*grouped_events, limit=None):
    """Transactions and transfers are different models with different
    shapes — a transfer has no signed_amount/category/etc. Rather than
    force them into one queryset, each caller wraps its rows into uniform
    event dicts (kind + date + created_at + the row itself); this just
    merges and sorts them so a transfer shows as ONE event (spec §55: never
    two confusing expense/income rows standing in for it)."""
    events = [event for group in grouped_events for event in group]
    events.sort(key=lambda e: (e["date"], e["created_at"]), reverse=True)
    return events[:limit] if limit else events


def _transaction_events(qs):
    return [{"kind": "transaction", "date": t.date, "created_at": t.created_at, "transaction": t} for t in qs]


def _transfer_events(qs, kind):
    return [{"kind": kind, "date": t.date, "created_at": t.created_at, "transfer": t} for t in qs]


def account_activity(account, limit=100):
    """Every transaction and transfer touching this one account, newest
    first — account_detail used to only show its Transactions, so a
    transfer in or out of the account it was viewing was invisible there."""
    transactions = account.transactions.select_related("category", "project", "person", "organization", "fund")
    transfers_out = Transfer.objects.filter(from_account=account).select_related("to_account")
    transfers_in = Transfer.objects.filter(to_account=account).select_related("from_account")
    return _merge_activity(
        _transaction_events(transactions),
        _transfer_events(transfers_out, "transfer_out"),
        _transfer_events(transfers_in, "transfer_in"),
        limit=limit,
    )


def context_activity(context, limit=100):
    """Every transaction and transfer touching any account in this context
    (personal or business). A transfer entirely within this context (both
    ends here, e.g. two business accounts) shows once, neutrally — showing
    it as both an outflow from one account and an inflow to the other would
    be the exact "confusing duplicate" spec §55 warns against, just at the
    context level instead of the account level. A transfer that crosses
    into the other context shows once, from this context's side."""
    transactions = Transaction.objects.filter(account__context=context).select_related("account", "category", "project", "person", "organization", "fund")
    internal_transfers = Transfer.objects.filter(from_account__context=context, to_account__context=context).select_related("from_account", "to_account")
    transfers_out = Transfer.objects.filter(from_account__context=context).exclude(to_account__context=context).select_related("from_account", "to_account")
    transfers_in = Transfer.objects.filter(to_account__context=context).exclude(from_account__context=context).select_related("from_account", "to_account")
    return _merge_activity(
        _transaction_events(transactions),
        _transfer_events(internal_transfers, "transfer"),
        _transfer_events(transfers_out, "transfer_out"),
        _transfer_events(transfers_in, "transfer_in"),
        limit=limit,
    )


def all_activity(limit=200):
    """The full cross-account, cross-context financial timeline (spec §53
    "All Money"/"All Activity") — every transaction and every transfer,
    regardless of which account or context it belongs to. Each transfer
    appears exactly once here (kind="transfer", no in/out side — there's no
    single account's perspective in a global view)."""
    transactions = Transaction.objects.select_related("account", "category", "project", "person", "organization", "fund")
    transfers = Transfer.objects.select_related("from_account", "to_account", "from_fund", "to_fund")
    return _merge_activity(
        _transaction_events(transactions),
        _transfer_events(transfers, "transfer"),
        limit=limit,
    )


def finance_overview(*, context=None):
    accounts = Account.objects.filter(active=True)
    if context:
        accounts = accounts.filter(context=context)
    today = timezone.localdate()
    month_start = today.replace(day=1)

    month_txns = Transaction.objects.filter(date__gte=month_start, date__lte=today)
    if context:
        month_txns = month_txns.filter(account__context=context)

    income = sum((t.amount for t in month_txns if t.type in INCOME_LIKE_TYPES), ZERO)
    expenses = sum((t.amount for t in month_txns if t.type == "expense"), ZERO) - sum(
        (t.amount for t in month_txns if t.type == "refund"), ZERO
    )

    return {
        "accounts": [{"account": a, "balance": account_balance(a)} for a in accounts],
        "total_balance": sum((account_balance(a) for a in accounts), ZERO),
        "month_income": income,
        "month_expenses": expenses,
        "month_net": income - expenses,
    }


def account_type_breakdown(*, context=None):
    """WHERE the money physically is — Bank vs Cash vs Wallet, etc. (spec
    §27) — as opposed to what it's for (Fund) or whose it is (Personal/
    Business). Computed live from account_balance() exactly like every other
    figure here, so it can never drift from the accounts themselves. Only
    types with at least one active account are returned, so a type nobody
    uses (e.g. Investment) never shows up as a stray zero row."""
    accounts = Account.objects.filter(active=True)
    if context:
        accounts = accounts.filter(context=context)

    totals = {}
    for account in accounts:
        totals[account.account_type] = totals.get(account.account_type, ZERO) + account_balance(account)

    labels = dict(ACCOUNT_TYPE_CHOICES)
    return [
        {"type": code, "label": labels[code], "total": totals[code]}
        for code, _ in ACCOUNT_TYPE_CHOICES
        if code in totals
    ]


def fund_month_summary(fund: Fund, *, today=None):
    """A Fund's current-month view (spec §29/§30/§55/§65) — spent so far,
    upcoming commitments tagged to it, and a category breakdown. There is
    deliberately no separate "Living dashboard" or "Family Support view" as
    its own code path: this same function IS that dashboard the moment the
    user names a Fund "Living" and tags rent/food/utilities to it — see
    docs/FINANCE_V2.md "One Fund Detail page, not one page per fund name"."""
    today = today or timezone.localdate()
    month_start = today.replace(day=1)
    month_txns = Transaction.objects.filter(fund=fund, date__gte=month_start, date__lte=today).select_related("category")

    spent = -sum((t.signed_amount for t in month_txns if t.signed_amount < 0), ZERO)
    added = sum((t.signed_amount for t in month_txns if t.signed_amount > 0), ZERO)

    upcoming = RecurringCommitment.objects.filter(fund=fund, active=True, next_due_date__gte=today).order_by("next_due_date")
    upcoming_total = sum((r.amount for r in upcoming if not r.is_income), ZERO)

    by_category = {}
    for t in month_txns:
        if t.signed_amount >= 0:
            continue
        by_category.setdefault(t.category, ZERO)
        by_category[t.category] += -t.signed_amount

    return {
        "spent_this_month": spent,
        "added_this_month": added,
        "upcoming": upcoming,
        "upcoming_total": upcoming_total,
        "by_category": by_category,
        "current_balance": fund_balance(fund),
    }


def counterparty_summary(*, person=None, organization=None, limit=20):
    """Person/Organization detail's Financial Summary (spec §6/§7/§74):
    total sent, total received, net, transaction count — computed from
    every Transaction's own signed_amount (not just income/expense, so a
    refund or a returned deposit counts too), never a manually-editable
    cached total (spec §7). Loans are pulled out and shown separately
    (spec §75: "Owes me / I owe them... do NOT mix into simple sent/
    received net") rather than folded into the same net an ordinary payment
    would be; deposits are treated as ordinary sent/received money here
    (a security deposit paid is real money that left your hand) — only
    loans get the receivable-style carve-out the spec names explicitly.

    Transfers never appear here by construction: Transfer has no person/
    organization field at all, so an internal transfer can never
    accidentally count as counterparty flow (spec §7)."""
    if bool(person) == bool(organization):
        raise ValueError("Pass exactly one of person or organization.")

    filter_kwargs = {"person": person} if person else {"organization": organization}
    transactions = Transaction.objects.filter(**filter_kwargs).select_related("account", "category", "project")

    received = ZERO
    sent = ZERO
    they_owe_me = ZERO
    i_owe_them = ZERO
    for t in transactions:
        if t.type == "loan_given":
            they_owe_me += t.amount
        elif t.type == "loan_received":
            i_owe_them += t.amount
        elif t.signed_amount >= 0:
            received += t.signed_amount
        else:
            sent += -t.signed_amount

    return {
        "total_received": received,
        "total_sent": sent,
        "net": received - sent,
        "transaction_count": transactions.count(),
        "they_owe_me": they_owe_me,
        "i_owe_them": i_owe_them,
        "recent_transactions": transactions.order_by("-date")[:limit],
    }


def reconcile():
    """Safe, read-only diagnostic (spec §69/§100 — the `finance_reconcile`
    management command). Never mutates anything; returns a plain dict of
    numbers and counts so a caller (management command or future admin
    view) can print or assert on it. No transaction notes/descriptions are
    included in the output — only identifiers, amounts, and counts (spec
    §100: "Output only safe identifiers/summary, not sensitive notes")."""
    accounts = Account.objects.filter(active=True)
    total_from_accounts = sum((account_balance(a) for a in accounts), ZERO)

    funds = Fund.objects.filter(archived=False)
    total_allocated = sum((fund_balance(f) for f in funds), ZERO)
    total_unallocated = unallocated_balance()

    fund_vs_unallocated_gap = total_from_accounts - (total_allocated + total_unallocated)

    # A transfer whose from/to account are both soft-deleted or inactive
    # would silently vanish from every account_balance() sum on both ends —
    # this can't happen via the app's own delete path (account_delete
    # soft-deletes its transfers too), but is worth surfacing if it ever
    # happens by another route (admin, a future bulk import).
    orphan_transfers = list(
        Transfer.objects.filter(models.Q(from_account__deleted_at__isnull=False) | models.Q(to_account__deleted_at__isnull=False)).values_list("id", flat=True)
    )
    unclassified_transaction_count = Transaction.objects.filter(fund__isnull=True).count()
    unclassified_counterparty_count = Transaction.objects.filter(person__isnull=True, organization__isnull=True).count()

    return {
        "total_money": total_from_accounts,
        "active_account_count": accounts.count(),
        "total_allocated_to_funds": total_allocated,
        "total_unallocated": total_unallocated,
        "allocation_reconciles": fund_vs_unallocated_gap == ZERO,
        "allocation_gap": fund_vs_unallocated_gap,
        "fund_count": funds.count(),
        "orphan_transfer_ids": [str(pk) for pk in orphan_transfers],
        "unclassified_transaction_count": unclassified_transaction_count,
        "unclassified_counterparty_transaction_count": unclassified_counterparty_count,
    }
