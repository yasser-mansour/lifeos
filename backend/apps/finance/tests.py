from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from apps.core.models import Profile
from apps.finance.models import Account, Allocation, Card, Category, Fund, RecurringCommitment, Transaction, Transfer
from apps.finance.services import (
    account_activity,
    account_balance,
    account_fund_breakdown,
    account_type_breakdown,
    all_activity,
    context_activity,
    counterparty_summary,
    create_transfer,
    equal_allocation_plan,
    fund_account_breakdown,
    fund_balance,
    reconcile,
    safe_to_spend,
    unallocated_balance,
)
from apps.people.models import Organization, Person
from apps.projects.models import Project

TODAY = timezone.localdate()


class FinanceScenarioTests(TestCase):
    """One test per scenario explicitly enumerated in the spec (§125)."""

    def setUp(self):
        self.personal_bank = Account.objects.create(name="CIH Personal", context="personal", account_type="bank", opening_balance=Decimal("10000.00"))
        self.cash = Account.objects.create(name="Cash", context="personal", account_type="cash", opening_balance=Decimal("500.00"))
        self.business_bank = Account.objects.create(name="CIH Business", context="business", account_type="bank", opening_balance=Decimal("20000.00"))
        self.housing = Category.objects.create(name="Housing")

    def test_1_personal_expense(self):
        Transaction.objects.create(account=self.personal_bank, amount=Decimal("100.00"), type="expense", direction="out", date=TODAY)
        self.assertEqual(account_balance(self.personal_bank), Decimal("9900.00"))

    def test_2_business_expense_linked_to_project(self):
        project = Project.objects.create(name="Northstar", area="business")
        Transaction.objects.create(account=self.business_bank, amount=Decimal("100.00"), type="expense", direction="out", date=TODAY, project=project)
        self.assertEqual(account_balance(self.business_bank), Decimal("19900.00"))
        self.assertEqual(project.transactions.count(), 1)

    def test_3_personal_income(self):
        Transaction.objects.create(account=self.personal_bank, amount=Decimal("1000.00"), type="income", direction="in", date=TODAY)
        self.assertEqual(account_balance(self.personal_bank), Decimal("11000.00"))

    def test_4_business_revenue_linked_to_client(self):
        client = Person.objects.create(name="Acme", relationship_types=["client"])
        Transaction.objects.create(account=self.business_bank, amount=Decimal("2000.00"), type="income", direction="in", date=TODAY, person=client)
        self.assertEqual(account_balance(self.business_bank), Decimal("22000.00"))

    def test_5_business_to_personal_transfer_is_not_income_or_expense(self):
        create_transfer(from_account=self.business_bank, to_account=self.personal_bank, amount=Decimal("2000.00"), currency="MAD", date=TODAY)
        self.assertEqual(account_balance(self.business_bank), Decimal("18000.00"))
        self.assertEqual(account_balance(self.personal_bank), Decimal("12000.00"))
        # Critically: no Transaction rows were created for either side.
        self.assertEqual(Transaction.objects.filter(type="income").count(), 0)
        self.assertEqual(Transaction.objects.filter(type="expense").count(), 0)
        self.assertEqual(Transfer.objects.count(), 1)

    def test_6_personal_bank_to_cash_transfer(self):
        create_transfer(from_account=self.personal_bank, to_account=self.cash, amount=Decimal("300.00"), currency="MAD", date=TODAY)
        self.assertEqual(account_balance(self.personal_bank), Decimal("9700.00"))
        self.assertEqual(account_balance(self.cash), Decimal("800.00"))

    def test_7_four_month_advance_payment_equal_allocation(self):
        txn = Transaction.objects.create(account=self.personal_bank, amount=Decimal("4000.00"), type="expense", direction="out", date=TODAY, category=self.housing, description="4 months rent advance")
        plan = equal_allocation_plan(Decimal("4000.00"), TODAY.replace(day=1), 4)
        for slice_ in plan:
            Allocation.objects.create(transaction=txn, category=self.housing, **slice_)
        # Cash impact today is the full 4000, immediately:
        self.assertEqual(account_balance(self.personal_bank), Decimal("6000.00"))
        # But it reports as 1000/month across 4 allocation rows:
        self.assertEqual(txn.allocations.count(), 4)
        for alloc in txn.allocations.all():
            self.assertEqual(alloc.amount, Decimal("1000.00"))
        self.assertEqual(sum((a.amount for a in txn.allocations.all()), Decimal("0")), txn.amount)
        self.assertTrue(txn.is_fully_allocated)

    def test_8_unequal_allocation_across_categories(self):
        utilities = Category.objects.create(name="Utilities")
        other = Category.objects.create(name="Other")
        txn = Transaction.objects.create(account=self.personal_bank, amount=Decimal("5000.00"), type="expense", direction="out", date=TODAY)
        Allocation.objects.create(transaction=txn, category=self.housing, amount=Decimal("2000.00"), period=TODAY)
        Allocation.objects.create(transaction=txn, category=utilities, amount=Decimal("1500.00"), period=TODAY)
        Allocation.objects.create(transaction=txn, category=other, amount=Decimal("1500.00"), period=TODAY)
        self.assertEqual(txn.allocated_total, Decimal("5000.00"))
        self.assertTrue(txn.is_fully_allocated)

    def test_9_refund(self):
        expense = Transaction.objects.create(account=self.personal_bank, amount=Decimal("800.00"), type="expense", direction="out", date=TODAY)
        Transaction.objects.create(account=self.personal_bank, amount=Decimal("800.00"), type="refund", direction="in", date=TODAY, refund_of=expense)
        self.assertEqual(account_balance(self.personal_bank), Decimal("10000.00"))

    def test_10_loan_given_not_counted_as_expense(self):
        Transaction.objects.create(account=self.personal_bank, amount=Decimal("500.00"), type="loan_given", direction="out", date=TODAY)
        self.assertEqual(account_balance(self.personal_bank), Decimal("9500.00"))
        from apps.finance.services import period_expense_totals

        totals = period_expense_totals(start_date=TODAY, end_date=TODAY)
        self.assertEqual(sum(totals.values(), Decimal("0")), Decimal("0.00"))

    def test_11_refundable_security_deposit(self):
        Transaction.objects.create(account=self.personal_bank, amount=Decimal("3000.00"), type="deposit_paid", direction="out", date=TODAY, category=self.housing)
        self.assertEqual(account_balance(self.personal_bank), Decimal("7000.00"))
        from apps.finance.services import period_expense_totals

        totals = period_expense_totals(start_date=TODAY, end_date=TODAY)
        # Not classified as a consumed housing expense:
        self.assertEqual(totals.get(self.housing, Decimal("0")), Decimal("0.00"))

    def test_12_recurring_rent_expectation_is_not_actual_money_movement(self):
        RecurringCommitment.objects.create(name="Rent", account=self.personal_bank, amount=Decimal("3000.00"), frequency="monthly", next_due_date=TODAY, category=self.housing)
        self.assertEqual(account_balance(self.personal_bank), Decimal("10000.00"))
        self.assertEqual(Transaction.objects.count(), 0)

    def test_13_multiple_personal_bank_accounts(self):
        second = Account.objects.create(name="Attijari Personal", context="personal", account_type="bank", opening_balance=Decimal("2000.00"))
        Transaction.objects.create(account=second, amount=Decimal("50.00"), type="expense", direction="out", date=TODAY)
        self.assertEqual(account_balance(self.personal_bank), Decimal("10000.00"))
        self.assertEqual(account_balance(second), Decimal("1950.00"))

    def test_14_multiple_business_bank_accounts(self):
        second = Account.objects.create(name="Attijari Business", context="business", account_type="bank", opening_balance=Decimal("5000.00"))
        self.assertEqual(Account.objects.filter(context="business").count(), 2)
        self.assertEqual(account_balance(second), Decimal("5000.00"))

    def test_15_project_profitability_from_transactions(self):
        from apps.projects.services import project_summary

        project = Project.objects.create(name="Harbor Supply", area="business")
        Transaction.objects.create(account=self.business_bank, amount=Decimal("3000.00"), type="income", direction="in", date=TODAY, project=project)
        Transaction.objects.create(account=self.business_bank, amount=Decimal("1200.00"), type="expense", direction="out", date=TODAY, project=project)
        summary = project_summary(project)
        self.assertEqual(summary["revenue"], Decimal("3000.00"))
        self.assertEqual(summary["expenses"], Decimal("1200.00"))
        self.assertEqual(summary["profit"], Decimal("1800.00"))

    def test_16_safe_to_spend(self):
        user = User.objects.create_user(username="owner", password="x")
        profile = Profile.objects.create(user=user, display_name="Owner", safe_to_spend_horizon_days=30, safe_to_spend_reserve=Decimal("500.00"))
        RecurringCommitment.objects.create(name="Rent", amount=Decimal("3000.00"), frequency="monthly", next_due_date=TODAY, context="personal")
        result = safe_to_spend(profile, context="personal")
        expected_liquid = Decimal("10500.00")  # personal_bank 10000 + cash 500
        self.assertEqual(result["liquid_balance"], expected_liquid)
        self.assertEqual(result["expected_commitments"], Decimal("3000.00"))
        self.assertEqual(result["safe_to_spend"], expected_liquid - Decimal("3000.00") - Decimal("500.00"))


class TransferIntegrityTests(TestCase):
    def test_cannot_transfer_to_same_account(self):
        # create_transfer now runs the model's own full_clean() (Finance V2
        # spec §58 needs the richer "did anything actually move" check,
        # which also covers same-account/same-fund transfers) rather than
        # its own narrower manual check, so this is a ValidationError now,
        # not the plain ValueError the old, account-only check raised.
        from django.core.exceptions import ValidationError

        account = Account.objects.create(name="Solo", opening_balance=Decimal("100.00"))
        with self.assertRaises(ValidationError):
            create_transfer(from_account=account, to_account=account, amount=Decimal("10.00"), currency="MAD", date=TODAY)

    def test_transaction_amount_cannot_be_negative(self):
        account = Account.objects.create(name="Solo", opening_balance=Decimal("100.00"))
        txn = Transaction(account=account, amount=Decimal("-5.00"), type="expense", direction="out", date=TODAY)
        with self.assertRaises(Exception):
            txn.full_clean()


class FinanceViewTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_overview_renders_with_no_accounts(self):
        response = self.client.get(reverse("finance:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No personal accounts yet")

    def test_create_account_and_view_detail(self):
        response = self.client.post(reverse("finance:account_create"), {
            "name": "CIH Personal", "account_type": "bank", "context": "personal", "currency": "MAD", "opening_balance": "1000.00",
        })
        self.assertEqual(response.status_code, 302)
        account = Account.objects.get(name="CIH Personal")
        detail = self.client.get(account.get_absolute_url())
        self.assertContains(detail, "1,000.00")

    def test_transfer_view_creates_transfer_not_transaction(self):
        a = Account.objects.create(name="A", opening_balance=Decimal("1000"))
        b = Account.objects.create(name="B", opening_balance=Decimal("0"))
        response = self.client.post(reverse("finance:transfer_new"), {
            "from_account": a.pk, "to_account": b.pk, "amount": "200.00", "currency": "MAD", "date": TODAY.isoformat(), "description": "",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Transfer.objects.count(), 1)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_account_detail_renders_with_transaction_present(self):
        """Smoke test for the per-row transaction markup — the empty-state
        test above never exercises this code path."""
        account = Account.objects.create(name="CIH Personal", opening_balance=Decimal("1000"))
        Transaction.objects.create(account=account, amount=Decimal("50"), type="expense", direction="out", date=TODAY, description="Coffee")
        response = self.client.get(account.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Coffee")

    def test_update_account(self):
        account = Account.objects.create(name="Old Name", opening_balance=Decimal("100"))
        response = self.client.post(reverse("finance:account_update", args=[account.pk]), {
            "name": "New Name", "institution": "CIH", "account_type": "bank", "context": "personal", "currency": "MAD", "opening_balance": "100.00", "notes": "",
        })
        self.assertRedirects(response, account.get_absolute_url())
        account.refresh_from_db()
        self.assertEqual(account.name, "New Name")

    def test_add_account_button_still_present_after_first_account_exists(self):
        """Regression: the overview template only rendered the "Add Account"
        button inside the empty-state branch, so it vanished the moment a
        context had its first account — making a second personal or business
        account unreachable from the UI even though the model/view always
        supported any number of them (see test_13/test_14 in
        FinanceScenarioTests, which prove the balance math already did)."""
        Account.objects.create(name="CIH Personal", context="personal", opening_balance=Decimal("100"))
        Account.objects.create(name="CIH Business", context="business", opening_balance=Decimal("100"))
        response = self.client.get(reverse("finance:overview"))
        self.assertContains(response, "new-account-personal")
        self.assertContains(response, "new-account-business")

    def test_overview_shows_combined_personal_plus_business_total(self):
        Account.objects.create(name="CIH Personal", context="personal", opening_balance=Decimal("1000"))
        Account.objects.create(name="CIH Business", context="business", opening_balance=Decimal("500"))
        response = self.client.get(reverse("finance:overview"))
        self.assertContains(response, "1,500.00")


class AccountDeletionTests(TestCase):
    """Account deletion didn't exist at all before — edit did, delete
    didn't. Soft-delete is a real CASCADE stand-in here: an account's FKs
    use on_delete=CASCADE, but BaseModel.soft_delete() never actually
    removes the row, so nothing fires it automatically. Deleting an account
    must also soft-delete its transactions/cards/transfers itself, or they'd
    keep counting toward totals and showing up in feeds under an account
    that's supposedly gone."""

    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_delete_account_removes_it_from_overview(self):
        account = Account.objects.create(name="Old Wallet", context="personal", opening_balance=Decimal("100"))
        self.client.post(reverse("finance:account_delete", args=[account.pk]))
        account.refresh_from_db()
        self.assertIsNotNone(account.deleted_at)
        self.assertFalse(Account.objects.filter(pk=account.pk).exists())  # excluded by ActiveManager
        self.assertNotContains(self.client.get(reverse("finance:overview")), "Old Wallet")

    def test_deleted_account_page_is_gone(self):
        account = Account.objects.create(name="Old Wallet", opening_balance=Decimal("100"))
        self.client.post(reverse("finance:account_delete", args=[account.pk]))
        response = self.client.get(account.get_absolute_url())
        self.assertEqual(response.status_code, 404)

    def test_delete_account_soft_deletes_its_transactions_too(self):
        account = Account.objects.create(name="Old Wallet", context="business", opening_balance=Decimal("500"))
        txn = Transaction.objects.create(account=account, amount=Decimal("50"), type="expense", direction="out", date=TODAY, description="Coffee")

        self.client.post(reverse("finance:account_delete", args=[account.pk]))

        txn.refresh_from_db()
        self.assertIsNotNone(txn.deleted_at)
        self.assertFalse(Transaction.objects.filter(pk=txn.pk).exists())
        # Regression: without cascading the soft-delete, this orphaned
        # transaction would keep counting toward the business context total.
        response = self.client.get(reverse("finance:context_detail", args=["business"]))
        self.assertNotContains(response, "Coffee")
        self.assertContains(response, "0.00 MAD")

    def test_delete_account_soft_deletes_its_cards(self):
        account = Account.objects.create(name="Old Wallet", opening_balance=Decimal("0"))
        card = Card.objects.create(account=account, nickname="Old Visa", last_four="1234")
        self.client.post(reverse("finance:account_delete", args=[account.pk]))
        card.refresh_from_db()
        self.assertIsNotNone(card.deleted_at)

    def test_delete_account_soft_deletes_related_transfers(self):
        a = Account.objects.create(name="A", opening_balance=Decimal("1000"))
        b = Account.objects.create(name="B", opening_balance=Decimal("0"))
        transfer = create_transfer(from_account=a, to_account=b, amount=Decimal("100"), currency="MAD", date=TODAY)

        self.client.post(reverse("finance:account_delete", args=[a.pk]))

        transfer.refresh_from_db()
        self.assertIsNotNone(transfer.deleted_at)

    def test_other_account_and_its_transactions_survive_deletion(self):
        keep = Account.objects.create(name="Keep Me", context="personal", opening_balance=Decimal("200"))
        gone = Account.objects.create(name="Delete Me", context="personal", opening_balance=Decimal("100"))
        Transaction.objects.create(account=keep, amount=Decimal("20"), type="expense", direction="out", date=TODAY, description="Groceries")

        self.client.post(reverse("finance:account_delete", args=[gone.pk]))

        self.assertTrue(Account.objects.filter(pk=keep.pk).exists())
        response = self.client.get(reverse("finance:overview"))
        self.assertContains(response, "Keep Me")
        self.assertContains(response, "Groceries")

    def test_delete_requires_post(self):
        account = Account.objects.create(name="Old Wallet", opening_balance=Decimal("0"))
        self.client.get(reverse("finance:account_delete", args=[account.pk]))
        self.assertTrue(Account.objects.filter(pk=account.pk).exists())

    def test_archive_button_present_on_account_page(self):
        account = Account.objects.create(name="Old Wallet", opening_balance=Decimal("0"))
        response = self.client.get(account.get_absolute_url())
        self.assertContains(response, "Archive Account")


class FinanceContextDetailViewTests(TestCase):
    """Settings/Sync/Conflicts-style grouped view for finance: all accounts
    and all transactions within one context (personal or business), scoped
    independently from the other context and from the combined overview."""

    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_unknown_context_is_404(self):
        response = self.client.get(reverse("finance:context_detail", args=["not-a-real-context"]))
        self.assertEqual(response.status_code, 404)

    def test_lists_every_account_in_that_context_only(self):
        Account.objects.create(name="CIH Business", context="business", opening_balance=Decimal("1000"))
        Account.objects.create(name="Business Cash", context="business", opening_balance=Decimal("200"))
        Account.objects.create(name="CIH Personal", context="personal", opening_balance=Decimal("50"))

        response = self.client.get(reverse("finance:context_detail", args=["business"]))
        self.assertContains(response, "CIH Business")
        self.assertContains(response, "Business Cash")
        self.assertNotContains(response, "CIH Personal")
        self.assertContains(response, "1,200.00")  # combined business balance

    def test_transactions_from_every_account_in_the_context_are_merged(self):
        a = Account.objects.create(name="Business A", context="business", opening_balance=Decimal("0"))
        b = Account.objects.create(name="Business B", context="business", opening_balance=Decimal("0"))
        Transaction.objects.create(account=a, amount=Decimal("50"), type="expense", direction="out", date=TODAY, description="From A")
        Transaction.objects.create(account=b, amount=Decimal("30"), type="expense", direction="out", date=TODAY, description="From B")

        response = self.client.get(reverse("finance:context_detail", args=["business"]))
        self.assertContains(response, "From A")
        self.assertContains(response, "From B")

    def test_add_account_available_even_with_existing_accounts(self):
        Account.objects.create(name="CIH Business", context="business", opening_balance=Decimal("100"))
        response = self.client.get(reverse("finance:context_detail", args=["business"]))
        self.assertContains(response, "new-account")

    def test_add_account_from_context_page_preselects_that_context(self):
        response = self.client.get(reverse("finance:context_detail", args=["business"]))
        self.assertContains(response, '<option value="business" selected>Business</option>')


class TransactionContextAndEditTests(TestCase):
    """Regression coverage: no Transaction edit/delete UI existed at all,
    and Project/Person/Account context was silently dropped by the "More
    options" collapsed section never being pre-filled or reachable."""

    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")
        self.account = Account.objects.create(name="CIH Personal", opening_balance=Decimal("1000"))

    def test_add_expense_from_project_prefills_project(self):
        project = Project.objects.create(name="Northstar")
        response = self.client.get(reverse("finance:transaction_new"), {"project": project.pk})
        self.assertContains(response, f'<option value="{project.pk}" selected>')

    def test_add_payment_from_person_prefills_person(self):
        person = Person.objects.create(name="Sara Bennani")
        response = self.client.get(reverse("finance:transaction_new"), {"person": person.pk})
        self.assertContains(response, f'<option value="{person.pk}" selected>')

    def test_add_transaction_from_account_prefills_account(self):
        response = self.client.get(reverse("finance:transaction_new"), {"account": self.account.pk})
        self.assertContains(response, f'<option value="{self.account.pk}" selected>')

    def test_edit_transaction_changes_project_link(self):
        project_a = Project.objects.create(name="Project A")
        project_b = Project.objects.create(name="Project B")
        txn = Transaction.objects.create(account=self.account, amount=Decimal("50"), type="expense", direction="out", date=TODAY, project=project_a)
        response = self.client.post(reverse("finance:transaction_edit", args=[txn.pk]), {
            "amount": "50.00", "type": "expense", "direction": "out", "account": self.account.pk, "date": TODAY.isoformat(),
            "description": "", "notes": "", "project": project_b.pk,
            "allocations-TOTAL_FORMS": "0", "allocations-INITIAL_FORMS": "0", "allocations-MIN_NUM_FORMS": "0", "allocations-MAX_NUM_FORMS": "1000",
        })
        self.assertRedirects(response, reverse("finance:account_detail", args=[self.account.pk]))
        txn.refresh_from_db()
        self.assertEqual(txn.project_id, project_b.pk)

    def test_edit_transaction_can_remove_project_link(self):
        project = Project.objects.create(name="Northstar")
        txn = Transaction.objects.create(account=self.account, amount=Decimal("50"), type="expense", direction="out", date=TODAY, project=project)
        response = self.client.post(reverse("finance:transaction_edit", args=[txn.pk]), {
            "amount": "50.00", "type": "expense", "direction": "out", "account": self.account.pk, "date": TODAY.isoformat(),
            "description": "", "notes": "", "project": "",
            "allocations-TOTAL_FORMS": "0", "allocations-INITIAL_FORMS": "0", "allocations-MIN_NUM_FORMS": "0", "allocations-MAX_NUM_FORMS": "1000",
        })
        self.assertRedirects(response, reverse("finance:account_detail", args=[self.account.pk]))
        txn.refresh_from_db()
        self.assertIsNone(txn.project)
        self.assertTrue(Project.objects.filter(pk=project.pk).exists())  # unlink, not delete

    def test_delete_transaction_soft_deletes(self):
        txn = Transaction.objects.create(account=self.account, amount=Decimal("50"), type="expense", direction="out", date=TODAY)
        response = self.client.post(reverse("finance:transaction_delete", args=[txn.pk]))
        self.assertRedirects(response, reverse("finance:account_detail", args=[self.account.pk]))
        self.assertFalse(Transaction.objects.filter(pk=txn.pk).exists())

    def test_delete_confirmation_modal_shows_transaction_details(self):
        """Regression: deletion used a bare browser confirm() with no detail
        — a misclick risked deleting the wrong row with only a generic
        "Delete this transaction?" prompt to catch it (spec §59)."""
        txn = Transaction.objects.create(account=self.account, amount=Decimal("85.00"), type="expense", direction="out", date=TODAY, description="Restaurant")
        response = self.client.get(reverse("finance:transaction_edit", args=[txn.pk]))
        self.assertContains(response, "Restaurant")
        self.assertContains(response, "85.00")
        self.assertContains(response, "This may change")
        self.assertTrue(Transaction.all_objects.filter(pk=txn.pk).exists())


class CardsRemovedFromUserFacingUITests(TestCase):
    """The Cards feature was removed from LIFEOS end-to-end (no add/edit/
    delete UI, no API) — the Card model/table stays defined and any
    existing row is untouched, it's just no longer reachable. See
    AccountDeletionTests.test_delete_account_soft_deletes_its_cards for
    confirmation the model-level cascade still works correctly."""

    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_no_cards_link_on_finance_overview(self):
        response = self.client.get(reverse("finance:overview"))
        self.assertNotContains(response, ">Cards<")

    def test_no_cards_url_registered(self):
        with self.assertRaises(NoReverseMatch):
            reverse("finance:cards")


class TransferVisibilityTests(TestCase):
    """Transfers are already first-class rows (never materialized as
    expense+income Transaction pairs — see Transfer's docstring), but
    account_detail/context_detail/overview used to query only Transaction,
    so a transfer in or out of the account/context being viewed was
    invisible there even though it was correctly recorded (spec §55/§56)."""

    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")
        self.manostock = Account.objects.create(name="Harbor Supply", context="business", opening_balance=Decimal("1000"))
        self.northstar = Account.objects.create(name="Northstar", context="business", opening_balance=Decimal("0"))
        self.personal_acc = Account.objects.create(name="Cash", context="personal", opening_balance=Decimal("500"))
        self.transfer = create_transfer(from_account=self.manostock, to_account=self.northstar, amount=Decimal("19.80"), currency="MAD", date=TODAY)

    def test_account_activity_shows_outgoing_transfer(self):
        events = account_activity(self.manostock)
        self.assertEqual(events[0]["kind"], "transfer_out")
        self.assertEqual(events[0]["transfer"], self.transfer)

    def test_account_activity_shows_incoming_transfer(self):
        events = account_activity(self.northstar)
        self.assertEqual(events[0]["kind"], "transfer_in")

    def test_account_detail_page_shows_the_transfer(self):
        response = self.client.get(self.manostock.get_absolute_url())
        self.assertContains(response, "Transfer")
        self.assertContains(response, "Northstar")

    def test_context_activity_shows_internal_transfer_exactly_once(self):
        """Both ends of this transfer (Harbor Supply, Northstar) are business
        accounts — showing it once as an outflow AND once as an inflow
        within the same "all business activity" feed would be exactly the
        confusing duplicate spec §55 warns against, just at the context
        level instead of the account level."""
        events = context_activity("business")
        transfer_events = [e for e in events if e.get("transfer") == self.transfer]
        self.assertEqual(len(transfer_events), 1)
        self.assertEqual(transfer_events[0]["kind"], "transfer")

    def test_context_activity_splits_in_out_for_cross_context_transfer(self):
        cash = Account.objects.create(name="Cash", context="personal", opening_balance=Decimal("0"))
        cross_transfer = create_transfer(from_account=self.manostock, to_account=cash, amount=Decimal("50"), currency="MAD", date=TODAY)

        business_events = context_activity("business")
        business_kind = next(e["kind"] for e in business_events if e.get("transfer") == cross_transfer)
        self.assertEqual(business_kind, "transfer_out")

        personal_events = context_activity("personal")
        personal_kind = next(e["kind"] for e in personal_events if e.get("transfer") == cross_transfer)
        self.assertEqual(personal_kind, "transfer_in")

    def test_context_detail_page_shows_the_transfer(self):
        response = self.client.get(reverse("finance:context_detail", args=["business"]))
        self.assertContains(response, "Harbor Supply")
        self.assertContains(response, "Northstar")

    def test_personal_context_does_not_show_business_transfer(self):
        response = self.client.get(reverse("finance:context_detail", args=["personal"]))
        self.assertNotContains(response, "Transfer")

    def test_all_activity_shows_transfer_exactly_once(self):
        """The transfer touches two accounts, but a global timeline must
        show it as ONE event, not one row per side (spec §55)."""
        events = all_activity()
        transfer_events = [e for e in events if e["kind"] == "transfer"]
        self.assertEqual(len(transfer_events), 1)
        self.assertEqual(transfer_events[0]["transfer"], self.transfer)

    def test_all_activity_page_renders(self):
        response = self.client.get(reverse("finance:all_activity"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Harbor Supply")
        self.assertContains(response, "Northstar")

    def test_all_activity_combined_total_matches_overview(self):
        """Opening balances: 1000 (Harbor Supply) + 0 (Northstar) + 500 (Cash) =
        1500 total. The 19.80 transfer moves money between accounts but must
        not change that combined figure (spec §52) — confirmed on both pages."""
        response = self.client.get(reverse("finance:all_activity"))
        overview_response = self.client.get(reverse("finance:overview"))
        self.assertContains(response, "1,500.00")
        self.assertContains(overview_response, "1,500.00")


class TransferDeleteTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")
        self.a = Account.objects.create(name="A", opening_balance=Decimal("1000"))
        self.b = Account.objects.create(name="B", opening_balance=Decimal("0"))
        self.transfer = create_transfer(from_account=self.a, to_account=self.b, amount=Decimal("200"), currency="MAD", date=TODAY)

    def test_delete_requires_post(self):
        self.client.get(reverse("finance:transfer_delete", args=[self.transfer.pk]))
        self.assertTrue(Transfer.objects.filter(pk=self.transfer.pk).exists())

    def test_delete_soft_deletes_the_transfer(self):
        self.client.post(reverse("finance:transfer_delete", args=[self.transfer.pk]))
        self.assertFalse(Transfer.objects.filter(pk=self.transfer.pk).exists())
        self.assertTrue(Transfer.all_objects.filter(pk=self.transfer.pk).exists())

    def test_deleted_transfer_no_longer_affects_balance(self):
        self.assertEqual(account_balance(self.b), Decimal("200.00"))
        self.client.post(reverse("finance:transfer_delete", args=[self.transfer.pk]))
        self.assertEqual(account_balance(self.b), Decimal("0.00"))

    def test_delete_confirmation_button_present_on_account_page(self):
        response = self.client.get(self.a.get_absolute_url())
        self.assertContains(response, f'action="/finance/transfer/{self.transfer.pk}/delete/"')


class DeletionAwareSyncApiTests(TestCase):
    """The Android API needs to tell a device "this record was deleted on
    the Mac" apart from "here's an update" during an incremental pull — see
    apps.devices.sync.DeletionAwareSyncMixin and spec §39/§41."""

    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")
        self.account = Account.objects.create(name="Checking", opening_balance=Decimal("100"))
        self.txn = Transaction.objects.create(account=self.account, amount=Decimal("20"), type="expense", direction="out", date=timezone.now().date(), description="Coffee")

    def test_default_list_excludes_deleted_rows_exactly_as_before(self):
        self.txn.soft_delete()
        response = self.client.get("/api/transactions/")
        ids = [row["id"] for row in response.json()["results"]]
        self.assertNotIn(str(self.txn.pk), ids)

    def test_modified_since_includes_a_deleted_row_flagged_as_deleted(self):
        cutoff = (timezone.now() - timezone.timedelta(minutes=5)).isoformat()
        self.txn.soft_delete()
        response = self.client.get("/api/transactions/", {"modified_since": cutoff})
        rows = {row["id"]: row for row in response.json()["results"]}
        self.assertIn(str(self.txn.pk), rows)
        self.assertTrue(rows[str(self.txn.pk)]["deleted"])

    def test_modified_since_excludes_rows_untouched_before_the_cutoff(self):
        cutoff = (timezone.now() + timezone.timedelta(minutes=5)).isoformat()
        response = self.client.get("/api/transactions/", {"modified_since": cutoff})
        ids = [row["id"] for row in response.json()["results"]]
        self.assertNotIn(str(self.txn.pk), ids)

    def test_untouched_row_is_not_flagged_deleted(self):
        cutoff = (timezone.now() - timezone.timedelta(minutes=5)).isoformat()
        response = self.client.get("/api/transactions/", {"modified_since": cutoff})
        rows = {row["id"]: row for row in response.json()["results"]}
        self.assertFalse(rows[str(self.txn.pk)]["deleted"])


class TotalBalanceCardTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_total_replaces_safe_to_spend_as_a_top_card(self):
        Account.objects.create(name="Personal Acc", context="personal", opening_balance=Decimal("9070"))
        Account.objects.create(name="Business Acc", context="business", opening_balance=Decimal("14730"))
        response = self.client.get(reverse("finance:overview"))
        self.assertContains(response, "23,800.00")
        content = response.content.decode()
        # "Total" must appear before "Safe to spend" in document order — it
        # now occupies the prominent top-row position Safe to Spend used to.
        self.assertLess(content.index(">Total<"), content.index("Safe to spend"))


class AccountTypeBreakdownTests(TestCase):
    """'Where it is' (Bank/Cash/Wallet...) — spec §27, added after a
    real-life request to separate total cash from total bank. Sibling to
    Personal/Business (whose it is) and Fund (what it's for): a third,
    independent way to slice the exact same accounts, computed live from
    account_balance() so it can never drift from them."""

    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_groups_and_sums_by_account_type(self):
        Account.objects.create(name="Life-Bank", account_type="bank", context="personal", opening_balance=Decimal("2000"))
        Account.objects.create(name="Northstar", account_type="bank", context="business", opening_balance=Decimal("500"))
        Account.objects.create(name="Life-Cash", account_type="cash", context="personal", opening_balance=Decimal("300"))

        breakdown = {row["type"]: row["total"] for row in account_type_breakdown()}
        self.assertEqual(breakdown["bank"], Decimal("2500"))
        self.assertEqual(breakdown["cash"], Decimal("300"))
        # No wallet/savings/investment account exists — those types must not
        # appear as stray zero rows.
        self.assertNotIn("wallet", breakdown)
        self.assertNotIn("investment", breakdown)

    def test_respects_context_filter(self):
        Account.objects.create(name="Life-Bank", account_type="bank", context="personal", opening_balance=Decimal("2000"))
        Account.objects.create(name="Northstar", account_type="bank", context="business", opening_balance=Decimal("500"))

        personal_only = {row["type"]: row["total"] for row in account_type_breakdown(context="personal")}
        self.assertEqual(personal_only["bank"], Decimal("2000"))

    def test_archived_and_inactive_accounts_excluded(self):
        Account.objects.create(name="Closed", account_type="bank", context="personal", opening_balance=Decimal("999"), active=False)
        self.assertEqual(account_type_breakdown(), [])

    def test_overview_page_splits_the_total_card_itself_into_bank_and_cash(self):
        """Spec follow-up: the user asked to split the Total *itself* into
        Bank/Cash, not add a separate grouped section elsewhere on the page
        — so this breakdown must render inside the same Total card, right
        under the combined figure, before the Personal/Business cards."""
        Account.objects.create(name="Life-Bank", account_type="bank", context="personal", opening_balance=Decimal("2000"))
        Account.objects.create(name="Life-Cash", account_type="cash", context="personal", opening_balance=Decimal("300"))

        response = self.client.get(reverse("finance:overview"))
        self.assertContains(response, "Bank")
        self.assertContains(response, "Cash")
        self.assertContains(response, "2,000.00")
        self.assertContains(response, "300.00")
        content = response.content.decode()
        # Must sit between the Total figure and the Personal *card* — i.e.
        # inside the Total card, not a separate section further down. The
        # persistent sidebar also has its own unrelated "Personal" section
        # label earlier on every page, so search for the account-card link
        # specifically (and start from i_total to stay unambiguous either way).
        i_total = content.index(">Total<")
        i_bank = content.index(">Bank<")
        i_personal_card = content.index('>Personal</a>', i_total)
        self.assertLess(i_total, i_bank)
        self.assertLess(i_bank, i_personal_card)

    def test_context_detail_page_shows_its_own_type_breakdown(self):
        Account.objects.create(name="Life-Bank", account_type="bank", context="personal", opening_balance=Decimal("2000"))
        Account.objects.create(name="Life-Cash", account_type="cash", context="personal", opening_balance=Decimal("300"))
        Account.objects.create(name="Northstar", account_type="bank", context="business", opening_balance=Decimal("500"))

        response = self.client.get(reverse("finance:context_detail", args=["personal"]))
        self.assertContains(response, "Bank")
        self.assertContains(response, "Cash")
        self.assertContains(response, "2,000.00")
        # The business-only "Northstar" bank money must not leak into the
        # personal context's Bank total.
        self.assertNotContains(response, "2,500.00")


def total_money():
    return sum((account_balance(a) for a in Account.objects.filter(active=True)), Decimal("0.00"))


class FundInvariantTests(TestCase):
    """Finance V2 spec §68 — ten numbered invariants, one test each. Fund is
    a pure tag on the same Transaction/Transfer rows account_balance()
    already reads, so most of these hold *by construction*; the tests exist
    to prove that, not to patch around a special case."""

    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")
        self.bank = Account.objects.create(name="Personal Bank", context="personal", account_type="bank", opening_balance=Decimal("10000.00"))
        self.cash = Account.objects.create(name="Cash", context="personal", account_type="cash", opening_balance=Decimal("0.00"))
        self.business_bank = Account.objects.create(name="Business Bank", context="business", account_type="bank", opening_balance=Decimal("5000.00"))
        self.living = Fund.objects.create(name="Living", context="personal")
        self.profits = Fund.objects.create(name="Project Profits", context="personal")
        self.suivedu = Fund.objects.create(name="Atlas Tracker", context="business")

    def test_1_sum_of_account_balances_equals_total_money(self):
        Transaction.objects.create(account=self.bank, amount=Decimal("500"), type="expense", direction="out", date=TODAY, fund=self.living)
        expected = account_balance(self.bank) + account_balance(self.cash) + account_balance(self.business_bank)
        self.assertEqual(total_money(), expected)

    def test_2_internal_account_transfer_does_not_change_total(self):
        before = total_money()
        create_transfer(from_account=self.bank, to_account=self.cash, amount=Decimal("500"), currency="MAD", date=TODAY)
        self.assertEqual(total_money(), before)

    def test_3_fund_transfer_alone_does_not_change_total(self):
        """Same account on both sides, only the fund changes (spec §60's
        project→personal profit move) — physical money never left the bank."""
        before = total_money()
        create_transfer(from_account=self.bank, to_account=self.bank, amount=Decimal("1000"), currency="MAD", date=TODAY, from_fund=self.profits, to_fund=self.living)
        self.assertEqual(total_money(), before)

    def test_4_combined_account_and_fund_transfer_does_not_change_total(self):
        before = total_money()
        create_transfer(from_account=self.business_bank, to_account=self.bank, amount=Decimal("2000"), currency="MAD", date=TODAY, from_fund=self.suivedu, to_fund=self.profits)
        self.assertEqual(total_money(), before)

    def test_5_external_income_increases_total(self):
        before = total_money()
        Transaction.objects.create(account=self.bank, amount=Decimal("3000"), type="income", direction="in", date=TODAY, fund=self.living)
        self.assertEqual(total_money(), before + Decimal("3000"))

    def test_6_external_expense_decreases_total(self):
        before = total_money()
        Transaction.objects.create(account=self.bank, amount=Decimal("120"), type="expense", direction="out", date=TODAY, fund=self.living)
        self.assertEqual(total_money(), before - Decimal("120"))

    def test_7_project_to_personal_transfer_does_not_increase_total(self):
        """The revenue was already counted when it first hit the business
        account (spec §22/§60) — taking it out as "profit" must not create
        new money on top of that."""
        Transaction.objects.create(account=self.business_bank, amount=Decimal("5000"), type="income", direction="in", date=TODAY, fund=self.suivedu)
        after_revenue = total_money()
        create_transfer(from_account=self.business_bank, to_account=self.bank, amount=Decimal("2000"), currency="MAD", date=TODAY, from_fund=self.suivedu, to_fund=self.profits)
        self.assertEqual(total_money(), after_revenue)
        self.assertEqual(fund_balance(self.suivedu), Decimal("3000"))
        self.assertEqual(fund_balance(self.profits), Decimal("2000"))

    def test_8_counterparty_received_and_sent_are_correct(self):
        heroku = Organization.objects.create(name="Heroku", relationship_types=["service_provider"])
        Transaction.objects.create(account=self.business_bank, amount=Decimal("120"), type="expense", direction="out", date=TODAY, organization=heroku)
        Transaction.objects.create(account=self.business_bank, amount=Decimal("30"), type="refund", direction="in", date=TODAY, organization=heroku)
        summary = counterparty_summary(organization=heroku)
        self.assertEqual(summary["total_sent"], Decimal("120"))
        self.assertEqual(summary["total_received"], Decimal("30"))
        self.assertEqual(summary["net"], Decimal("-90"))
        self.assertEqual(summary["transaction_count"], 2)

    def test_9_account_deletion_does_not_orphan_transaction_history(self):
        txn = Transaction.objects.create(account=self.bank, amount=Decimal("50"), type="expense", direction="out", date=TODAY)
        self.bank.soft_delete()
        txn.refresh_from_db()
        # Soft-deleted, not gone — the row and its account_id both survive.
        self.assertIsNotNone(Transaction.all_objects.get(pk=txn.pk).account_id)
        self.assertTrue(Account.all_objects.get(pk=self.bank.pk))

    def test_10_fund_deletion_does_not_lose_allocation_it_becomes_unallocated(self):
        txn = Transaction.objects.create(account=self.bank, amount=Decimal("500"), type="expense", direction="out", date=TODAY, fund=self.living)
        before = total_money()
        self.client.post(reverse("finance:fund_delete", args=[self.living.pk]))
        txn.refresh_from_db()
        self.assertIsNone(txn.fund_id)
        self.assertEqual(total_money(), before)  # deleting a Fund never touches Account balances


class TransferKindTests(TestCase):
    """Physical / logical / combined — spec §58/§59-61."""

    def setUp(self):
        self.bank = Account.objects.create(name="Bank", context="personal", opening_balance=Decimal("1000"))
        self.cash = Account.objects.create(name="Cash", context="personal", opening_balance=Decimal("0"))
        self.living = Fund.objects.create(name="Living", context="personal")
        self.profits = Fund.objects.create(name="Profits", context="personal")

    def test_physical_transfer_kind(self):
        t = create_transfer(from_account=self.bank, to_account=self.cash, amount=Decimal("100"), currency="MAD", date=TODAY)
        self.assertEqual(t.transfer_kind, "physical")

    def test_logical_transfer_kind(self):
        t = create_transfer(from_account=self.bank, to_account=self.bank, amount=Decimal("100"), currency="MAD", date=TODAY, from_fund=self.profits, to_fund=self.living)
        self.assertEqual(t.transfer_kind, "logical")

    def test_combined_transfer_kind(self):
        t = create_transfer(from_account=self.bank, to_account=self.cash, amount=Decimal("100"), currency="MAD", date=TODAY, from_fund=self.profits, to_fund=self.living)
        self.assertEqual(t.transfer_kind, "combined")

    def test_true_no_op_transfer_is_rejected(self):
        with self.assertRaises(Exception):
            create_transfer(from_account=self.bank, to_account=self.bank, amount=Decimal("100"), currency="MAD", date=TODAY)

    def test_account_fund_breakdown_sums_to_account_balance(self):
        Transaction.objects.create(account=self.bank, amount=Decimal("200"), type="expense", direction="out", date=TODAY, fund=self.living)
        Transaction.objects.create(account=self.bank, amount=Decimal("100"), type="expense", direction="out", date=TODAY)  # unallocated
        breakdown_total = sum(account_fund_breakdown(self.bank).values(), Decimal("0.00"))
        self.assertEqual(breakdown_total, account_balance(self.bank))

    def test_fund_account_breakdown_sums_to_fund_balance(self):
        Transaction.objects.create(account=self.bank, amount=Decimal("200"), type="expense", direction="out", date=TODAY, fund=self.living)
        Transaction.objects.create(account=self.cash, amount=Decimal("50"), type="income", direction="in", date=TODAY, fund=self.living)
        breakdown_total = sum(fund_account_breakdown(self.living).values(), Decimal("0.00"))
        self.assertEqual(breakdown_total, fund_balance(self.living))

    def test_unallocated_balance_plus_allocated_equals_total(self):
        Transaction.objects.create(account=self.bank, amount=Decimal("200"), type="expense", direction="out", date=TODAY, fund=self.living)
        Transaction.objects.create(account=self.bank, amount=Decimal("50"), type="expense", direction="out", date=TODAY)
        allocated = fund_balance(self.living) + fund_balance(self.profits)
        self.assertEqual(unallocated_balance(context="personal") + allocated, account_balance(self.bank) + account_balance(self.cash))


class RealLifeWorkflowTests(TestCase):
    """Finance V2 spec §92-96 — named end-to-end scenarios, run against a
    test database only (never production)."""

    def setUp(self):
        self.personal_bank = Account.objects.create(name="Personal Bank", context="personal", account_type="bank", opening_balance=Decimal("0"))
        self.business_bank = Account.objects.create(name="Business Bank", context="business", account_type="bank", opening_balance=Decimal("0"))
        self.cash = Account.objects.create(name="Cash", context="personal", account_type="cash", opening_balance=Decimal("0"))
        self.living = Fund.objects.create(name="Living", context="personal")

    def test_92_family_support_workflow(self):
        family = Person.objects.create(name="Family Support Person", relationship_types=["family"])
        before = total_money()
        Transaction.objects.create(account=self.personal_bank, amount=Decimal("3000"), type="income", direction="in", date=TODAY, person=family, fund=self.living)
        self.assertEqual(total_money(), before + Decimal("3000"))
        self.assertEqual(account_balance(self.personal_bank), Decimal("3000"))
        self.assertEqual(fund_balance(self.living), Decimal("3000"))
        summary = counterparty_summary(person=family)
        self.assertEqual(summary["total_received"], Decimal("3000"))
        self.assertEqual(summary["transaction_count"], 1)

    def test_93_heroku_workflow(self):
        heroku = Organization.objects.create(name="Heroku", relationship_types=["service_provider"])
        northstar = Project.objects.create(name="Northstar", area="business")
        northstar_fund = Fund.objects.create(name="Northstar", context="business", project=northstar)
        before = total_money()
        Transaction.objects.create(
            account=self.business_bank, amount=Decimal("120"), type="expense", direction="out", date=TODAY,
            fund=northstar_fund, project=northstar, organization=heroku,
        )
        self.assertEqual(total_money(), before - Decimal("120"))
        self.assertEqual(account_balance(self.business_bank), Decimal("-120"))
        self.assertEqual(fund_balance(northstar_fund), Decimal("-120"))
        self.assertEqual(northstar.transactions.count(), 1)
        summary = counterparty_summary(organization=heroku)
        self.assertEqual(summary["total_sent"], Decimal("120"))

    def test_94_monthly_living_workflow(self):
        Transaction.objects.create(account=self.personal_bank, amount=Decimal("4000"), type="income", direction="in", date=TODAY, fund=self.living)
        Transaction.objects.create(account=self.personal_bank, amount=Decimal("1800"), type="expense", direction="out", date=TODAY, fund=self.living, description="Rent")
        Transaction.objects.create(account=self.personal_bank, amount=Decimal("250"), type="expense", direction="out", date=TODAY, fund=self.living, description="Internet")
        Transaction.objects.create(account=self.personal_bank, amount=Decimal("500"), type="expense", direction="out", date=TODAY, fund=self.living, description="Groceries")
        self.assertEqual(fund_balance(self.living), Decimal("1450"))

    def test_95_project_profit_transfer_workflow(self):
        suivedu = Fund.objects.create(name="Atlas Tracker", context="business")
        profits = Fund.objects.create(name="Project Profits", context="personal")
        Transaction.objects.create(account=self.business_bank, amount=Decimal("3000"), type="income", direction="in", date=TODAY, fund=suivedu)
        before = total_money()
        create_transfer(from_account=self.business_bank, to_account=self.business_bank, amount=Decimal("1000"), currency="MAD", date=TODAY, from_fund=suivedu, to_fund=profits)
        self.assertEqual(total_money(), before)
        self.assertEqual(fund_balance(suivedu), Decimal("2000"))
        self.assertEqual(fund_balance(profits), Decimal("1000"))
        # Not counted as new external income anywhere:
        self.assertEqual(Transaction.objects.filter(type="income").count(), 1)

    def test_96_cash_withdrawal_workflow(self):
        self.personal_bank.opening_balance = Decimal("5000")
        self.personal_bank.save(update_fields=["opening_balance"])
        create_transfer(from_account=self.personal_bank, to_account=self.cash, amount=Decimal("500"), currency="MAD", date=TODAY)
        self.assertEqual(account_balance(self.personal_bank), Decimal("4500"))
        self.assertEqual(account_balance(self.cash), Decimal("500"))
        self.assertEqual(total_money(), Decimal("5000"))


class ReconcileDiagnosticTests(TestCase):
    """Finance V2 spec §100 — the finance_reconcile diagnostic never mutates."""

    def test_reconcile_never_mutates_and_reports_clean_state(self):
        bank = Account.objects.create(name="Bank", context="personal", opening_balance=Decimal("1000"))
        living = Fund.objects.create(name="Living", context="personal")
        Transaction.objects.create(account=bank, amount=Decimal("100"), type="expense", direction="out", date=TODAY, fund=living)
        before_txn_count = Transaction.objects.count()
        before_fund_count = Fund.objects.count()

        report = reconcile()

        self.assertEqual(Transaction.objects.count(), before_txn_count)
        self.assertEqual(Fund.objects.count(), before_fund_count)
        self.assertTrue(report["allocation_reconciles"])
        self.assertEqual(report["allocation_gap"], Decimal("0.00"))
        self.assertEqual(report["total_money"], Decimal("900.00"))

    def test_reconcile_output_has_no_notes_or_descriptions(self):
        bank = Account.objects.create(name="Bank", context="personal", opening_balance=Decimal("0"))
        Transaction.objects.create(account=bank, amount=Decimal("10"), type="expense", direction="out", date=TODAY, notes="a very private note", description="secret description")
        report = reconcile()
        serialized = str(report)
        self.assertNotIn("a very private note", serialized)
        self.assertNotIn("secret description", serialized)


class TransactionCounterpartyTests(TestCase):
    def test_transaction_cannot_have_both_person_and_organization(self):
        from django.core.exceptions import ValidationError

        bank = Account.objects.create(name="Bank", context="personal", opening_balance=Decimal("0"))
        person = Person.objects.create(name="Sara")
        org = Organization.objects.create(name="Heroku")
        txn = Transaction(account=bank, amount=Decimal("10"), type="expense", direction="out", date=TODAY, person=person, organization=org)
        with self.assertRaises(ValidationError):
            txn.full_clean()

    def test_counterparty_property_reads_whichever_is_set(self):
        bank = Account.objects.create(name="Bank", context="personal", opening_balance=Decimal("0"))
        org = Organization.objects.create(name="Heroku")
        txn = Transaction.objects.create(account=bank, amount=Decimal("10"), type="expense", direction="out", date=TODAY, organization=org)
        self.assertEqual(txn.counterparty, org)


class FundApiTests(TestCase):
    """Android parity (spec §86) — Fund needs to actually be reachable
    through the sync API, not just the desktop templates."""

    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_create_fund_via_api(self):
        response = self.client.post("/api/funds/", {"name": "Living", "context": "personal"})
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Fund.objects.filter(name="Living").exists())

    def test_fund_balance_field_reflects_tagged_transactions(self):
        fund = Fund.objects.create(name="Living", context="personal")
        account = Account.objects.create(name="Bank", context="personal", opening_balance=Decimal("0"))
        Transaction.objects.create(account=account, amount=Decimal("500"), type="income", direction="in", date=TODAY, fund=fund)
        response = self.client.get(f"/api/funds/{fund.pk}/")
        self.assertEqual(response.json()["balance"], "500.00")

    def test_deleted_fund_is_flagged_on_incremental_pull(self):
        fund = Fund.objects.create(name="Old Fund", context="personal")
        cutoff = (timezone.now() - timezone.timedelta(minutes=5)).isoformat()
        fund.soft_delete()
        response = self.client.get("/api/funds/", {"modified_since": cutoff})
        rows = {row["id"]: row for row in response.json()["results"]}
        self.assertTrue(rows[str(fund.pk)]["deleted"])

    def test_transaction_api_accepts_fund_and_organization(self):
        account = Account.objects.create(name="Business Bank", context="business", opening_balance=Decimal("0"))
        fund = Fund.objects.create(name="Northstar", context="business")
        org = Organization.objects.create(name="Heroku")
        response = self.client.post("/api/transactions/", {
            "account": str(account.pk), "fund": str(fund.pk), "organization": str(org.pk),
            "amount": "120.00", "type": "expense", "direction": "out", "date": str(TODAY),
        })
        self.assertEqual(response.status_code, 201, response.content)
        txn = Transaction.objects.get(pk=response.json()["id"])
        self.assertEqual(txn.fund_id, fund.pk)
        self.assertEqual(txn.organization_id, org.pk)

    def test_transfer_api_accepts_fund_only_logical_transfer(self):
        account = Account.objects.create(name="Business Bank", context="business", opening_balance=Decimal("5000"))
        suivedu = Fund.objects.create(name="Atlas Tracker", context="business")
        profits = Fund.objects.create(name="Project Profits", context="personal")
        response = self.client.post("/api/transfers/", {
            "from_account": str(account.pk), "to_account": str(account.pk),
            "from_fund": str(suivedu.pk), "to_fund": str(profits.pk),
            "amount": "1000.00", "currency": "MAD", "date": str(TODAY),
        })
        self.assertEqual(response.status_code, 201, response.content)
