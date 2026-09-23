package com.lifeos.app.ui.finance

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Wallet
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import com.lifeos.app.ui.components.EmptyState
import com.lifeos.app.ui.components.LifeOSListRow
import com.lifeos.app.ui.components.ScreenHeader
import com.lifeos.app.ui.components.SectionLabel
import com.lifeos.app.ui.format.formatMoney
import com.lifeos.app.ui.theme.Spacing

/**
 * "What the money is for" (docs/FINANCE_V2.md), separate from Accounts'
 * "where it is" — Living, Family Support, a per-project fund like
 * Northstar. Grouped Personal/Business the same way the Finance overview
 * already groups Accounts, for a consistent mental model between the two.
 */
@Composable
fun FundsScreen(viewModel: FinanceViewModel, onOpenFund: (String) -> Unit) {
    val funds by viewModel.funds.collectAsState()

    Column(modifier = Modifier.fillMaxSize().padding(horizontal = Spacing.xl)) {
        ScreenHeader("Funds")

        if (funds.isEmpty()) {
            EmptyState(
                icon = Icons.Filled.Wallet, title = "No funds yet",
                body = "Create one on your Mac (Finance → Funds) for things like Living, Family Support, or a project's own money.",
            )
        } else {
            LazyColumn(modifier = Modifier.fillMaxSize()) {
                val personal = funds.filter { it.fund.context == "personal" }
                val business = funds.filter { it.fund.context == "business" }
                if (personal.isNotEmpty()) {
                    item { SectionLabel("Personal") }
                    items(personal, key = { it.fund.id }) { entry -> FundRow(entry, onOpenFund) }
                }
                if (business.isNotEmpty()) {
                    item { SectionLabel("Business", modifier = Modifier.padding(top = Spacing.lg)) }
                    items(business, key = { it.fund.id }) { entry -> FundRow(entry, onOpenFund) }
                }
                val other = funds.filterNot { it.fund.context == "personal" || it.fund.context == "business" }
                if (other.isNotEmpty()) {
                    item { SectionLabel("Other", modifier = Modifier.padding(top = Spacing.lg)) }
                    items(other, key = { it.fund.id }) { entry -> FundRow(entry, onOpenFund) }
                }
            }
        }
    }
}

@Composable
private fun FundRow(entry: FundWithLiveBalance, onOpenFund: (String) -> Unit) {
    LifeOSListRow(
        title = entry.fund.name,
        trailing = { androidx.compose.material3.Text(formatMoney(entry.liveBalance), style = androidx.compose.material3.MaterialTheme.typography.titleMedium.copy(fontFamily = com.lifeos.app.ui.theme.monoFamily)) },
        onClick = { onOpenFund(entry.fund.id) },
    )
}
