from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.finance.services import reconcile


def _q(amount):
    """Cosmetic only — Sum() aggregates and plain Decimal addition don't
    always agree on trailing-zero scale, so the same correct value can print
    as "5623.0000000000000" in one place and "5623.00" in another. Rounding
    for display never touches the actual reconciliation math above."""
    return amount.quantize(Decimal("0.01"))


class Command(BaseCommand):
    """Finance V2 spec §69/§100 — a safe, read-only diagnostic. It never
    writes anything (there is deliberately no `--fix` flag: the spec is
    explicit that one "should NOT exist initially unless fixes are
    extremely safe", and nothing here has been judged that safe yet) and
    never prints a transaction's notes or description, only identifiers,
    amounts, and counts.

    Usage:
        python manage.py finance_reconcile
    """

    help = "Read-only finance integrity check: total money, fund allocation, orphan transfers, unclassified transactions. Never mutates anything."

    def handle(self, *args, **options):
        report = reconcile()

        self.stdout.write(self.style.MIGRATE_HEADING("LIFEOS Finance Reconciliation"))
        self.stdout.write(f"  Total money (active accounts): {_q(report['total_money'])} across {report['active_account_count']} account(s)")
        self.stdout.write(f"  Allocated to funds:            {_q(report['total_allocated_to_funds'])} across {report['fund_count']} fund(s)")
        self.stdout.write(f"  Unallocated:                   {_q(report['total_unallocated'])}")

        if report["allocation_reconciles"]:
            self.stdout.write(self.style.SUCCESS("  ✓ Allocated + Unallocated == Total money"))
        else:
            self.stdout.write(self.style.ERROR(f"  ✗ Allocation gap of {_q(report['allocation_gap'])} — allocated + unallocated does not equal total money"))

        self.stdout.write("")
        if report["orphan_transfer_ids"]:
            self.stdout.write(self.style.WARNING(f"  {len(report['orphan_transfer_ids'])} transfer(s) reference a deleted account:"))
            for transfer_id in report["orphan_transfer_ids"]:
                self.stdout.write(f"    - {transfer_id}")
        else:
            self.stdout.write(self.style.SUCCESS("  ✓ No orphan transfers"))

        self.stdout.write("")
        self.stdout.write(f"  Transactions with no Fund (Unallocated):        {report['unclassified_transaction_count']}")
        self.stdout.write(f"  Transactions with no counterparty (Person/Org): {report['unclassified_counterparty_transaction_count']}")
        self.stdout.write("")
        self.stdout.write(self.style.NOTICE("  This command never modifies data. Run it any time — as often as you like."))
