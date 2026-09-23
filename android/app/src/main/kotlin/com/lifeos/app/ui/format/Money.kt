package com.lifeos.app.ui.format

import java.math.BigDecimal
import java.text.NumberFormat
import java.util.Locale

private val formatter: NumberFormat = NumberFormat.getNumberInstance(Locale.US).apply {
    minimumFractionDigits = 2
    maximumFractionDigits = 2
}

/** The one place every screen formats an amount — was duplicated three
 * times (Home, Finance, AddTransaction) with the currency hardcoded to
 * "MAD" in two of them even for a non-MAD account. */
fun formatMoney(amount: BigDecimal, currency: String = "MAD"): String = "${formatter.format(amount)} $currency"

/** Same, with an explicit +/− sign — for activity rows where the direction
 * of money matters more than in a balance display. */
fun formatMoneySigned(amount: BigDecimal, currency: String = "MAD"): String {
    val sign = if (amount.signum() < 0) "−" else "+"
    return "$sign${formatter.format(amount.abs())} $currency"
}
