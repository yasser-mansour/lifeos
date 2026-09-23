# Finance

## Core principle

Record what actually happened first, interpret it second (spec §23). A `Transaction` row always represents a real cash movement. Anything that *isn't* a real cash movement — a recurring rent expectation before it's paid, a category budget — lives in a separate model and is never faked as a Transaction.

## What counts as spending

`Transaction.type` has twelve values (`apps/finance/models.py`): `expense`, `income`, `refund`, `loan_given`, `loan_received`, `deposit_paid`, `deposit_returned`, `withdrawal`, `investment`, `reimbursement`, `adjustment`, `other`.

Only `expense` and `refund` feed expense statistics and budgets (`EXPENSE_LIKE_TYPES`); only `income` feeds income statistics (`INCOME_LIKE_TYPES`). Loans, deposits, investments, and withdrawals change what you *own*, not what you *spent* — spec §33/§34 are explicit that a security deposit or a loan given must not be counted as consumed expense, so they're excluded from those aggregates by construction, not by a filter someone could forget to apply.

Every type except `adjustment` and `other` has a **fixed sign** (`FIXED_SIGN_BY_TYPE`) — `expense` is always -1, `income` always +1, and so on. `adjustment`/`other` are the only two where the sign is ambiguous by nature, so they carry an explicit `direction` field (`in`/`out`) instead.

## Transfers are not Transactions

`Transfer` is its own model (`from_account`, `to_account`, `amount`, `date`) — never two Transaction rows (spec §30: "This must NOT become: business expense = 2,000 and personal income = 2,000. It is a TRANSFER."). Because it's one row referencing both accounts, it's atomic by construction; there's no window where one side exists and the other doesn't. `apps/finance/services.py::create_transfer` is the only way to create one, and it rejects `from_account == to_account`.

`account_balance()` adds a Transfer's amount to `to_account` and subtracts it from `from_account` when computing either account's balance — Transfers are invisible to income/expense statistics entirely, which is the whole point.

## Advance payments and multi-purpose payments (spec §31/§32)

Both are the same mechanism: a single `Transaction` (the real cash movement — e.g. -12,000 MAD today for four months of rent) can have any number of `Allocation` rows attached, each with its own `category`, `amount`, and `period` (the month it reports against). The transaction's cash impact is exactly its own amount, on its own date — allocations never create new Transaction rows or move money a second time. `apps/finance/services.py::equal_allocation_plan()` computes an even split across N periods (remainder absorbed into the last period so the sum always matches exactly); custom/unequal splits are just Allocation rows entered directly.

## Refundable deposits and loans

`deposit_paid` decreases the paying account's balance but is excluded from expense statistics (it's a receivable, not consumption) — `deposit_returned` is its counterpart. `loan_given`/`loan_received` work the same way. There's no separate "receivable" ledger; the exclusion from expense/income statistics *is* the receivable-style interpretation, kept intentionally simple rather than building enterprise double-entry accounting (spec §33: "Keep implementation understandable rather than building enterprise accounting").

## Recurring commitments: expected vs. actual

`RecurringCommitment` represents an expectation (rent is due monthly, ~3000 MAD) — it never creates a Transaction by itself. "Record actual" (`finance:recurring_record` view) is a separate, explicit action that creates a real Transaction linked back via `Transaction.recurring_commitment`, and advances `next_due_date`. The Finance overview's "Upcoming" section reads `RecurringCommitment` rows directly — it is never confused with real transaction history (spec §36: "Do NOT pretend money moved before the real transaction exists").

## Safe to spend

`apps/finance/services.py::safe_to_spend()`:

```
liquid_balance (personal, active accounts)
  - expected commitments due within profile.safe_to_spend_horizon_days
  - profile.safe_to_spend_reserve
= safe_to_spend
```

Both the horizon and the reserve are user-configurable (`Profile` fields); the Finance overview labels the result "estimate" per spec §38.

## Cards

`Card` stores nickname, linked account, last 4 digits, card type, and expiry — nothing else. No CVV, PIN, password, OTP, or full card number field exists anywhere in the schema. This is a deliberate scope decision, not an oversight: spec §41 explicitly permits omitting full-card-number storage rather than implementing it insecurely, and building a correct encrypt-at-rest-with-Keychain-backed-keys path for one field, end to end, verified, was judged not to fit this build's time budget alongside everything else. `apps/security/crypto.py` implements the actual Keychain-backed encryption primitive (real, working, tested) so the pattern exists if a future field genuinely needs it — see `docs/SECURITY.md`.

## Tests

`apps/finance/tests.py::FinanceScenarioTests` has one test per scenario spec §125 enumerates by name (personal expense, business expense linked to a project, business→personal transfer *not* counting as income/expense, four-month advance payment, unequal allocation, refund, loan, deposit, recurring commitment, multiple accounts per context, project profitability, safe-to-spend) — 16 tests, all passing as of this build.
