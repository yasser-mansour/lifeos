from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Profile, log_activity
from apps.finance.forms import AccountForm, AllocationFormSet, CategoryForm, FundForm, RecurringCommitmentForm, TransactionForm, TransferForm
from apps.finance.models import ACCOUNT_CONTEXT_CHOICES, FIXED_SIGN_BY_TYPE, Account, Category, Fund, RecurringCommitment, Transaction, Transfer
from apps.finance.services import (
    account_activity,
    account_balance,
    account_fund_breakdown,
    account_type_breakdown,
    all_activity,
    context_activity,
    finance_overview,
    fund_account_breakdown,
    fund_activity,
    fund_balance,
    fund_month_summary,
    safe_to_spend,
    unallocated_balance,
    upcoming_recurring,
)


@login_required
def overview(request):
    profile = Profile.objects.get(user=request.user)
    personal = finance_overview(context="personal")
    business = finance_overview(context="business")
    context = {
        "active_nav": "finance",
        "personal": personal,
        "business": business,
        "combined_total": personal["total_balance"] + business["total_balance"],
        "account_count": len(personal["accounts"]) + len(business["accounts"]),
        "by_type": account_type_breakdown(),
        "safe_to_spend": safe_to_spend(profile, context="personal"),
        "upcoming": upcoming_recurring(within_days=30),
        "recent_events": all_activity(limit=10),
        "show_new_account": request.GET.get("new_account"),
        "personal_business_forms": [
            ("personal", "Personal", AccountForm(initial={"currency": profile.default_currency, "context": "personal"})),
            ("business", "Business", AccountForm(initial={"currency": profile.default_currency, "context": "business"})),
        ],
    }
    return render(request, "finance/overview.html", context)


@login_required
def context_detail(request, context):
    context_labels = dict(ACCOUNT_CONTEXT_CHOICES)
    if context not in context_labels:
        raise Http404("Not a recognized account context.")

    profile = Profile.objects.get(user=request.user)
    overview_data = finance_overview(context=context)
    view_context = {
        "active_nav": "finance",
        "context": context,
        "context_label": context_labels[context],
        "overview": overview_data,
        "by_type": account_type_breakdown(context=context),
        "events": context_activity(context, limit=100),
        "show_new_account": request.GET.get("new_account") == "1",
        "account_form": AccountForm(initial={"currency": profile.default_currency, "context": context}),
    }
    return render(request, "finance/context_detail.html", view_context)


@login_required
def account_create(request):
    if request.method == "POST":
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save()
            log_activity(f"Added account {account.name}", category="finance", obj=account)
            return redirect("finance:account_detail", pk=account.pk)
    return redirect("finance:overview")


@login_required
def account_detail(request, pk):
    account = get_object_or_404(Account, pk=pk)
    context = {
        "active_nav": "finance",
        "account": account,
        "balance": account_balance(account),
        "fund_breakdown": sorted(account_fund_breakdown(account).items(), key=lambda kv: (kv[0] is None, str(kv[0]))),
        "events": account_activity(account, limit=100),
        "edit_form": AccountForm(instance=account),
        "back_url": reverse("finance:context_detail", args=[account.context]),
        "back_label": account.get_context_display(),
    }
    return render(request, "finance/account_detail.html", context)


@login_required
def account_update(request, pk):
    account = get_object_or_404(Account, pk=pk)
    if request.method == "POST":
        form = AccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            log_activity(f"Updated account {account.name}", category="finance", obj=account)
    return redirect("finance:account_detail", pk=pk)


@login_required
def all_activity_view(request):
    personal_total = finance_overview(context="personal")["total_balance"]
    business_total = finance_overview(context="business")["total_balance"]
    context = {
        "active_nav": "finance",
        "events": all_activity(limit=300),
        "combined_total": personal_total + business_total,
    }
    return render(request, "finance/all_activity.html", context)


@login_required
def account_delete(request, pk):
    account = get_object_or_404(Account, pk=pk)
    if request.method == "POST":
        # A soft-deleted account still physically exists (BaseModel never
        # hard-deletes), so its FKs' on_delete=CASCADE never fires — without
        # this, its transactions/cards/transfers would keep counting toward
        # totals and showing up in feeds under an account that's supposedly
        # gone. Soft-delete them alongside it so "delete" behaves the same
        # as the CASCADE it stands in for, just reversibly.
        for txn in account.transactions.all():
            txn.soft_delete()
        for card in account.cards.all():
            card.soft_delete()
        for transfer in Transfer.objects.filter(Q(from_account=account) | Q(to_account=account)):
            transfer.soft_delete()
        name = account.name
        account.soft_delete()
        log_activity(f"Deleted account {name}", category="finance")
    return redirect("finance:overview")


@login_required
def transaction_new(request):
    return _transaction_form(request, txn=None)


@login_required
def transaction_edit(request, pk):
    txn = get_object_or_404(Transaction, pk=pk)
    return _transaction_form(request, txn=txn)


def _transaction_form(request, txn):
    if request.method == "POST":
        form = TransactionForm(request.POST, instance=txn)
        if form.is_valid():
            saved = form.save(commit=False)
            fixed_sign = FIXED_SIGN_BY_TYPE.get(saved.type)
            if fixed_sign is not None:
                saved.direction = "in" if fixed_sign > 0 else "out"
            # else: 'adjustment' / 'other' keep whatever direction the user picked
            saved.save()
            form.save_m2m()

            formset = AllocationFormSet(request.POST, instance=saved)
            if formset.is_valid():
                formset.save()

            verb = "Updated" if txn else "Added"
            log_activity(f"{verb} {saved.get_type_display().lower()} of {saved.amount} {saved.currency}", category="finance", obj=saved)
            return redirect("finance:account_detail", pk=saved.account_id)
    else:
        # Create-in-context: "Add Expense" from a Project, "Add Payment" from
        # a Person, or "Add Transaction" from an Account all pass their id so
        # the new transaction actually starts linked to where it was opened
        # from, instead of a blank form the user has to remember to fill in.
        initial = {}
        if txn is None:
            initial["date"] = timezone.localdate()
            project_id = request.GET.get("project")
            person_id = request.GET.get("person")
            organization_id = request.GET.get("organization")
            account_id = request.GET.get("account")
            fund_id = request.GET.get("fund")
            if project_id:
                initial["project"] = project_id
            if person_id:
                initial["person"] = person_id
            if organization_id:
                initial["organization"] = organization_id
            if account_id:
                initial["account"] = account_id
            if fund_id:
                initial["fund"] = fund_id
        form = TransactionForm(instance=txn, initial=initial)

    formset = AllocationFormSet(instance=txn)
    # Back always resolves to a real account page rather than a generic
    # "Finance" landing — matches how the transaction was actually reached
    # (an account's own page, or ?account= from a create-in-context link).
    back_account_id = txn.account_id if txn else request.GET.get("account")
    if back_account_id:
        back_url = reverse("finance:account_detail", args=[back_account_id])
        back_label = Account.objects.filter(pk=back_account_id).values_list("name", flat=True).first() or "Account"
    else:
        back_url = reverse("finance:overview")
        back_label = "Finance"
    context = {
        "active_nav": "finance", "form": form, "formset": formset, "txn": txn,
        "prefill_context": bool(txn is None and (request.GET.get("project") or request.GET.get("person") or request.GET.get("organization") or request.GET.get("fund"))),
        "back_url": back_url, "back_label": back_label,
    }
    return render(request, "finance/transaction_new.html", context)


@login_required
def transaction_delete(request, pk):
    txn = get_object_or_404(Transaction, pk=pk)
    account_id = txn.account_id
    if request.method == "POST":
        txn.soft_delete()
        log_activity(f"Removed {txn.get_type_display().lower()} of {txn.amount} {txn.currency}", category="finance")
    return redirect("finance:account_detail", pk=account_id)


@login_required
def transfer_new(request):
    if request.method == "POST":
        form = TransferForm(request.POST)
        if form.is_valid():
            transfer = form.save()
            log_activity(f"Transferred {transfer.amount} {transfer.currency}", category="finance", obj=transfer)
            return redirect("finance:overview")
    else:
        form = TransferForm(initial={"date": timezone.localdate()})
    return render(request, "finance/transfer_new.html", {"active_nav": "finance", "form": form})


@login_required
def transfer_edit(request, pk):
    """Correcting a transfer (spec §44) updates both sides atomically — it's
    one row, so there's no "leave a mismatch" failure mode a two-row model
    could have; ModelForm.save() on a single instance is already atomic at
    the database-row level."""
    transfer = get_object_or_404(Transfer, pk=pk)
    if request.method == "POST":
        form = TransferForm(request.POST, instance=transfer)
        if form.is_valid():
            form.save()
            log_activity(f"Updated transfer of {transfer.amount} {transfer.currency}", category="finance", obj=transfer)
            return redirect(request.POST.get("next") or "finance:overview")
    else:
        form = TransferForm(instance=transfer)
    return render(request, "finance/transfer_new.html", {"active_nav": "finance", "form": form, "transfer": transfer, "next": request.GET.get("next", "")})


@login_required
def transfer_delete(request, pk):
    transfer = get_object_or_404(Transfer, pk=pk)
    if request.method == "POST":
        # A Transfer is already one row representing both sides atomically
        # (see apps.finance.models.Transfer's docstring — never
        # materialized as two Transaction rows), so soft-deleting it can't
        # leave an orphaned half-transfer the way a two-row model could.
        transfer.soft_delete()
        log_activity(f"Deleted transfer of {transfer.amount} {transfer.currency}", category="finance")
    return redirect(request.POST.get("next") or "finance:overview")


@login_required
def recurring_list(request):
    items = RecurringCommitment.objects.filter(active=True)
    if request.method == "POST":
        form = RecurringCommitmentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("finance:recurring_list")
    context = {
        "active_nav": "finance", "items": items,
        "form": RecurringCommitmentForm(initial={"frequency": "monthly", "context": "personal"}),
        "show_new": request.GET.get("new") == "1",
    }
    return render(request, "finance/recurring_list.html", context)


@login_required
def recurring_edit(request, pk):
    commitment = get_object_or_404(RecurringCommitment, pk=pk)
    if request.method == "POST":
        form = RecurringCommitmentForm(request.POST, instance=commitment)
        if form.is_valid():
            form.save()
            log_activity(f"Updated {commitment.name}", category="finance", obj=commitment)
    return redirect("finance:recurring_list")


@login_required
def recurring_delete(request, pk):
    commitment = get_object_or_404(RecurringCommitment, pk=pk)
    if request.method == "POST":
        commitment.soft_delete()
        log_activity(f"Removed recurring commitment {commitment.name}", category="finance")
    return redirect("finance:recurring_list")


@login_required
def recurring_record_actual(request, pk):
    commitment = get_object_or_404(RecurringCommitment, pk=pk)
    if request.method == "POST" and commitment.account:
        txn = Transaction.objects.create(
            account=commitment.account,
            amount=commitment.amount,
            currency=commitment.currency,
            type="income" if commitment.is_income else "expense",
            direction="in" if commitment.is_income else "out",
            date=timezone.localdate(),
            category=commitment.category,
            description=commitment.name,
            project=commitment.project,
            fund=commitment.fund,
            person=commitment.person,
            organization=commitment.organization,
            recurring_commitment=commitment,
        )
        commitment.advance_due_date()
        log_activity(f"Recorded {commitment.name}", category="finance", obj=txn)
    return redirect("finance:recurring_list")


# ---------------------------------------------------------------------------
# Funds — "what the money is for" (spec §14-16, §29/§30/§55/§65). One
# generic list/detail pair serves every fund name the user creates — Living,
# Family Support, Project Profits, or a per-project fund like Northstar —
# there's no separate "Living dashboard" code path (see fund_month_summary).
# ---------------------------------------------------------------------------


@login_required
def fund_list(request):
    funds = Fund.objects.filter(archived=False)
    profile = Profile.objects.get(user=request.user)
    context = {
        "active_nav": "finance",
        "personal_funds": [{"fund": f, "balance": fund_balance(f)} for f in funds.filter(context="personal")],
        "business_funds": [{"fund": f, "balance": fund_balance(f)} for f in funds.filter(context="business")],
        "unallocated_personal": unallocated_balance(context="personal"),
        "unallocated_business": unallocated_balance(context="business"),
        "show_new": request.GET.get("new") == "1",
        "form": FundForm(initial={"context": "personal"}),
    }
    return render(request, "finance/fund_list.html", context)


@login_required
def fund_create(request):
    if request.method == "POST":
        form = FundForm(request.POST)
        if form.is_valid():
            fund = form.save()
            log_activity(f"Added fund {fund.name}", category="finance", obj=fund)
            return redirect("finance:fund_detail", pk=fund.pk)
    return redirect("finance:fund_list")


@login_required
def fund_detail(request, pk):
    fund = get_object_or_404(Fund, pk=pk)
    context = {
        "active_nav": "finance",
        "fund": fund,
        "balance": fund_balance(fund),
        "account_breakdown": sorted(fund_account_breakdown(fund).items(), key=lambda kv: str(kv[0])),
        "month": fund_month_summary(fund),
        "events": fund_activity(fund, limit=100),
        "edit_form": FundForm(instance=fund),
    }
    return render(request, "finance/fund_detail.html", context)


@login_required
def fund_update(request, pk):
    fund = get_object_or_404(Fund, pk=pk)
    if request.method == "POST":
        form = FundForm(request.POST, instance=fund)
        if form.is_valid():
            form.save()
            log_activity(f"Updated fund {fund.name}", category="finance", obj=fund)
    return redirect("finance:fund_detail", pk=pk)


@login_required
def fund_archive_toggle(request, pk):
    fund = get_object_or_404(Fund, pk=pk)
    if request.method == "POST":
        fund.archived = not fund.archived
        fund.save(update_fields=["archived"])
        log_activity(f"{'Archived' if fund.archived else 'Restored'} fund {fund.name}", category="finance")
        if fund.archived:
            return redirect("finance:fund_list")
    return redirect("finance:fund_detail", pk=pk)


@login_required
def fund_delete(request, pk):
    """Deletes the Fund without deleting a single Transaction/Transfer it
    touched (spec §46/§48: "Do not silently cascade-delete financial
    history") — they become Unallocated instead. This has to be done
    explicitly, one row at a time (not left to on_delete=SET_NULL): a
    soft-delete only sets deleted_at, it never runs Django's real DELETE, so
    the SET_NULL cascade — which only fires on a genuine row deletion —
    would never trigger and every linked row would keep silently pointing
    at a fund that no longer shows up anywhere (exactly the "silently lose
    allocation" spec §68 test 10 guards against). account_delete uses this
    same explicit-cascade pattern for the same reason."""
    fund = get_object_or_404(Fund, pk=pk)
    if request.method == "POST":
        for txn in Transaction.objects.filter(fund=fund):
            txn.fund = None
            txn.save(update_fields=["fund"])
        for transfer in Transfer.objects.filter(Q(from_fund=fund) | Q(to_fund=fund)):
            if transfer.from_fund_id == fund.pk:
                transfer.from_fund = None
            if transfer.to_fund_id == fund.pk:
                transfer.to_fund = None
            transfer.save(update_fields=["from_fund", "to_fund"])
        fund.soft_delete()
        log_activity(f"Deleted fund {fund.name}", category="finance")
    return redirect("finance:fund_list")


# ---------------------------------------------------------------------------
# Categories (spec §50) — create/rename/archive; existing categories (and
# any already-classified transactions) are untouched by any of this.
# ---------------------------------------------------------------------------


@login_required
def category_list(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("finance:category_list")
    context = {
        "active_nav": "finance",
        "categories": Category.objects.filter(archived=False),
        "form": CategoryForm(initial={"context": "both"}),
        "show_new": request.GET.get("new") == "1",
    }
    return render(request, "finance/category_list.html", context)


@login_required
def category_update(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
    return redirect("finance:category_list")


@login_required
def category_archive_toggle(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        category.archived = not category.archived
        category.save(update_fields=["archived"])
    return redirect("finance:category_list")


# ---------------------------------------------------------------------------
# Finance structure review (spec §17/§18) — the safe, opt-in bridge from
# "this Account's name actually describes a purpose" to a real Fund.
# Nothing here runs unless the user explicitly clicks the button for one
# specific account; no account is ever renamed, archived, or reinterpreted
# automatically, and no existing balance or transaction amount changes.
# ---------------------------------------------------------------------------


@login_required
def reclassify(request):
    from apps.projects.models import Project

    rows = []
    for account in Account.objects.filter(active=True):
        rows.append(
            {
                "account": account,
                "balance": account_balance(account),
                "transaction_count": account.transactions.count(),
                "sample_descriptions": list(account.transactions.exclude(description="").values_list("description", flat=True)[:5]),
                "matching_fund": Fund.objects.filter(name__iexact=account.name, context=account.context).first(),
                "matching_project": Project.objects.filter(name__iexact=account.name).first(),
            }
        )
    return render(request, "finance/reclassify.html", {"active_nav": "finance", "rows": rows})


@login_required
def reclassify_map_to_fund(request, pk):
    """"Convert/Map to Fund" (spec §18's mockup) — creates a Fund with the
    same name/context (linking it to a same-named Project if one exists,
    e.g. the "Northstar" account ↔ the "Northstar" project) and tags every
    not-yet-classified Transaction on this account with it. The Account
    itself is untouched — spec §13 is explicit that money can be BOTH
    "physically in this account" AND "for this purpose" at once; nothing
    here requires choosing one over the other. Saved one row at a time
    (never a bulk .update()) so each Transaction's own updated_at/version
    bumps normally — a bulk update would silently skip Android sync, which
    watches those fields to know what changed."""
    account = get_object_or_404(Account, pk=pk)
    if request.method == "POST":
        from apps.projects.models import Project

        matching_project = Project.objects.filter(name__iexact=account.name).first()
        fund, created = Fund.objects.get_or_create(
            name=account.name,
            context=account.context,
            defaults={"project": matching_project, "notes": f'Created from the "{account.name}" account via Finance → Review structure.'},
        )
        count = 0
        for txn in Transaction.objects.filter(account=account, fund__isnull=True):
            txn.fund = fund
            txn.save(update_fields=["fund"])
            count += 1
        log_activity(f'Mapped "{account.name}" to fund "{fund.name}" ({count} transactions tagged)', category="finance", obj=fund)
    return redirect("finance:reclassify")


