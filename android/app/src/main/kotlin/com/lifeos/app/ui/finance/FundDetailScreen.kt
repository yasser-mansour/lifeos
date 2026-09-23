package com.lifeos.app.ui.finance

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import com.lifeos.app.ui.components.EmptyState
import com.lifeos.app.ui.components.ScreenHeader
import com.lifeos.app.ui.format.formatMoney
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.Spacing
import com.lifeos.app.ui.theme.monoFamily
import java.util.Locale

/**
 * One Fund's own view — balance plus everything tagged with it, filtered
 * client-side from the already-loaded transaction list the same way
 * Project/Person detail filter their own sections (docs/FINANCE_V2.md: no
 * separate "Living dashboard" code path, Fund detail generically serves
 * whatever fund the user is looking at).
 */
@Composable
fun FundDetailScreen(viewModel: FinanceViewModel, fundId: String, onAddTransaction: (String) -> Unit) {
    val funds by viewModel.funds.collectAsState()
    val allTransactions by viewModel.allTransactions.collectAsState()
    val colors = LocalLifeOSColors.current

    val entry = funds.firstOrNull { it.fund.id == fundId } ?: return
    val transactions = allTransactions.filter { it.fundId == fundId }.sortedByDescending { it.dateEpochDay }

    Scaffold(
        containerColor = colors.bgPrimary,
        floatingActionButton = {
            FloatingActionButton(onClick = { onAddTransaction(fundId) }, containerColor = colors.accent) {
                Icon(Icons.Filled.Add, contentDescription = "Add Transaction", tint = Color.White)
            }
        },
    ) { padding ->
        LazyColumn(modifier = Modifier.fillMaxSize().padding(padding).padding(horizontal = Spacing.xl)) {
            item {
                ScreenHeader(entry.fund.name)
                Text(
                    entry.fund.context.replaceFirstChar { it.uppercase(Locale.getDefault()) } + " fund",
                    style = MaterialTheme.typography.bodyMedium, color = colors.textSecondary, modifier = Modifier.padding(bottom = Spacing.md),
                )
                Text(
                    formatMoney(entry.liveBalance), style = MaterialTheme.typography.displayMedium.copy(fontFamily = monoFamily, fontWeight = FontWeight.SemiBold),
                    color = colors.textPrimary, modifier = Modifier.padding(bottom = Spacing.xl),
                )
            }

            if (transactions.isEmpty()) {
                item {
                    EmptyState(
                        icon = Icons.Filled.Add, title = "No activity yet",
                        body = "Tag a transaction with ${entry.fund.name} and it'll show up here.",
                    )
                }
            } else {
                items(transactions, key = { it.id }) { txn -> TransactionRow(txn) }
            }
        }
    }
}
