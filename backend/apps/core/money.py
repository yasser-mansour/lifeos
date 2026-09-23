"""Centralized money handling. Never use float for currency amounts anywhere
in LIFEOS — always Decimal, always paired with an explicit currency code."""

from decimal import ROUND_HALF_UP, Decimal

CURRENCY_SYMBOLS = {
    "MAD": "MAD",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
}

ZERO = Decimal("0.00")


def to_decimal(value) -> Decimal:
    """Coerce input (str, float, int, Decimal, None) to a 2dp Decimal.

    Only used at system boundaries (form input, JSON bodies) — everywhere
    else in the codebase a value is already a Decimal.
    """
    if value in (None, ""):
        return ZERO
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def format_money(amount, currency="MAD") -> str:
    amount = to_decimal(amount)
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    whole, _, frac = f"{amount:.2f}".partition(".")
    groups = []
    while len(whole) > 3:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    groups.insert(0, whole)
    formatted = ",".join(groups) + "." + frac
    symbol = CURRENCY_SYMBOLS.get(currency, currency)
    if currency == "MAD":
        return f"{sign}{formatted} {symbol}"
    return f"{sign}{symbol}{formatted}"
