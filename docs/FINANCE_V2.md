# Finance V2 — People & Organizations, Funds, and Real-Life Money

This extends `docs/FINANCE.md` (still accurate for everything it covers —
Transaction types, signed amounts, Transfers, Allocations, recurring
commitments, safe-to-spend) rather than replacing it. This document covers
what Finance V2 added: **Funds**, **Organizations**, and the transfer engine
that moves money between them.

## The core distinction: Account vs Fund

An **Account** (`apps.finance.models.Account`, unchanged since v1) answers
*where* money physically is: Cash, a specific bank, a wallet.

A **Fund** (`apps.finance.models.Fund`, new) answers *what the money is
for*: Living, Family Support, Project Profits, or a per-project fund like
"Northstar". The same bank account can hold money for three different Funds
at once; the same Fund can have money sitting in two different accounts.

```
CIH Bank (an Account) holds:
  Living            3,000 MAD
  Family Support    2,000 MAD
  Unallocated       5,000 MAD   ← not yet tagged with any Fund
  ─────────────────────────
  Account balance  10,000 MAD
```

**Why there's no `AccountFundBalance` cache table.** The obvious design
(store a running balance per account-fund pair) risks drifting from the
real transaction history — exactly the failure mode `docs/FINANCE.md`
already rejected for `Account.balance` itself. Instead, `Fund` is just
another optional tag living directly on `Transaction` (`Transaction.fund`)
and `Transfer` (`Transfer.from_fund` / `Transfer.to_fund`), the same way
`Transaction.account` already is. Every number — a Fund's balance, an
Account's breakdown by Fund, a Fund's breakdown by Account — is
reconstructed live from those two tables:

- `apps.finance.services.fund_balance(fund)` — mirrors `account_balance()`.
- `apps.finance.services.account_fund_breakdown(account)` — one Account's
  balance split by Fund (including `None` = Unallocated). Values always sum
  to `account_balance(account)`.
- `apps.finance.services.fund_account_breakdown(fund)` — one Fund's balance
  split by Account it's actually sitting in.
- `apps.finance.services.unallocated_balance(context=...)` — defined as
  `total account balance − total fund balance`, i.e. the remainder, so
  "allocated + unallocated = total" is true *by construction*, not by a
  separate calculation that could disagree.

**Adding Fund never changes `account_balance()` or global total money.**
Fund is a read dimension on the same events, not a second ledger — this is
why every "total money doesn't change" invariant in this document holds
without special-case code.

## Unallocated (spec's backward-compatibility requirement)

There is no `Fund` row named "Unallocated". `Transaction.fund` and
`Transfer.from_fund`/`to_fund` are simply nullable, and every existing
transaction from before this feature existed has `fund = NULL`. Every
report and template treats `None` as "Unallocated" — a label, not a
database row. This means:

- The app works identically the moment this migration lands — nothing
  requires the user to classify anything before continuing to use Finance.
- Nothing needs a special "protect the Unallocated fund from deletion"
  rule, because it isn't a row that could be deleted.

## The "Review Finance Structure" tool

`finance:reclassify` (linked from the Finance overview page) is the bridge
between the old world (an Account whose *name* really describes a purpose —
this real user's "Life", "Location", and "Projects" accounts, or a
business account named after its project, e.g. "Northstar") and the new one.

For each active Account it shows the transaction count, a few sample
descriptions, and a **"Map to Fund"** button. Clicking it:

1. Creates a Fund with the same name and context (linking it to a
   same-named Project if one exists — e.g. the "Northstar" account maps to
   the existing "Northstar" project automatically).
2. Tags every transaction on that Account that doesn't already have a Fund
   with the new one — one row at a time via `.save()`, never a bulk
   `.update()`, so each row's `updated_at`/`version` bump normally and
   Android sync still picks up the change.
3. **Leaves the Account itself completely untouched.** An account can be
   both a physical location and (once mapped) fully represent one Fund —
   the tool never asks the user to choose one interpretation over the
   other, and no balance, name, or transaction amount is altered.

Nothing runs automatically. A user who never visits this page keeps working
exactly as before, with everything Unallocated.

## Organizations: the other half of "People & Organizations"

`apps.people.models.Organization` is a new model, not a flag on `Person`.
Heroku, a bank, a landlord company, a school — anything you deal with
financially that isn't a person — gets its own record with fields that
actually fit it (website, category) instead of a fake first/last name.

`Person` is **completely unchanged** as a model — every existing row and
every existing FK (`Transaction.person`, `Task.person`, etc.) keeps working
exactly as before. `Transaction.organization` and
`RecurringCommitment.organization` are new, separate, nullable FKs sitting
alongside the untouched `person` field. A `.counterparty` property on both
models reads whichever one is actually set:

```python
txn.counterparty  # -> the Person, or the Organization, or None
```

A transaction can't have both (`Transaction.clean()` rejects it) — a
payment moved with exactly one real-world counterparty, never two.

**Relationships are multi-valued, not a single label.** Both `Person` and
`Organization` share the same `relationship_types` JSON list and the same
expanded vocabulary (Client, Prospect, Service Provider, Supplier,
Employer/Payer, Family, Friend, Teacher, School, Bank, Landlord, Platform,
Partner, Collaborator, Contact, Other). There's no separate
`CUSTOMER_DIRECTION` field: whether "they pay me" or "I pay them" is
answered by which tags are present plus the real transaction history
(`counterparty_summary`, below) — a school can carry both "Client" (you
tutor for them) and be someone you separately pay tuition to, and the
numbers tell the true story either way.

**People & Organizations is one list**, not two pages — filterable by type
(Person/Organization) and by relationship, per `people:list`.

## Financial interaction summary (every Person and every Organization)

`apps.finance.services.counterparty_summary(person=... )` /
`(organization=...)` computes, from every linked `Transaction`'s own
`signed_amount` (not a cached total):

- **Total received** / **Total sent** / **Net**
- **Transaction count**
- **They owe me** / **I owe them** — `loan_given`/`loan_received` amounts
  are pulled out and shown separately rather than netted in, so a loan
  never quietly changes what "received" or "sent" means. (Refundable
  deposits are *not* special-cased here — a deposit paid is still real
  money that left your hand, so it counts as ordinary "sent"; only loans
  got the explicit carve-out the spec named.)

This is shown on **every** Person and Organization detail page
unconditionally — not gated on `relationship_types` containing "client".
Someone tagged only "Family" who sent you money still shows a full
Received/Sent/Net breakdown.

Transfers never appear in a counterparty summary, by construction: `Transfer`
has no `person`/`organization` field at all.

## Transfers: physical, logical, and combined

One model, one form, one creation path (`apps.finance.services.
create_transfer`) for all three:

| Kind | What changes | Example |
|---|---|---|
| Physical | `from_account` ≠ `to_account`, funds equal (usually both null) | Withdraw cash: Bank → Cash |
| Logical | Same account both sides, `from_fund` ≠ `to_fund` | Take profit: Atlas Tracker fund → Personal Project Profits fund, same bank account |
| Combined | Both differ | Pay a supplier from the business bank's Northstar fund into a personal fund somewhere else |

`Transfer.transfer_kind` (a computed property) reports which one a given
row is, purely for display. `Transfer.clean()` rejects a transfer that
would move nothing at all (same account *and* same fund on both sides).

**A transfer never changes total money**, regardless of kind — proven by
`FundInvariantTests` (tests 2–4) in `apps/finance/tests.py`. A logical
transfer moving business profit into a personal fund does **not** create
new income: the revenue was already counted when it first arrived (test 7,
mirroring spec §22/§60's "do not count it again").

Editing a Transfer (`finance:transfer_edit`) updates both sides atomically
because it's one row — there's no "half-updated" state a two-row model
could have.

## Project funds and profitability vs. cash available

A Fund can optionally link to a `Project` (`Fund.project`). This gives a
project two related but distinct numbers, both already computed by
existing/extended services:

- **Profit** (`apps.projects.services.project_summary` — revenue minus
  expenses from `Transaction.project`, unchanged from v1).
- **Currently available Fund balance** (`fund_balance(project.funds...)`) —
  can be *lower* than lifetime profit once money has been transferred out
  as an owner withdrawal, or *higher* if money was advanced into it. The
  two are never conflated.

## Categories

`Category` gained `context` (personal/business/both) and `archived` — it
stays on its original integer primary key rather than being moved onto
`BaseModel`'s UUID scheme, since there were zero `Category` rows in
production when this changed and migrating every FK that points at it
(`Transaction`, `Allocation`, `RecurringCommitment`, `Budget`) for no
functional gain would have been unnecessary structural churn.

## Reconciliation

`python manage.py finance_reconcile` — read-only, no `--fix` flag (spec
§100 is explicit that one shouldn't exist yet). Reports total money, total
allocated to Funds, total unallocated, whether those reconcile, any
transfer referencing a deleted account, and counts of unclassified
transactions (no Fund / no counterparty). Prints no transaction notes or
descriptions.

`apps/finance/tests.py::FundInvariantTests` encodes the ten invariants spec
§68 asks for as one test each; `RealLifeWorkflowTests` encodes the five
named scenarios (family support, Heroku, monthly living, project profit
transfer, cash withdrawal) end to end.
