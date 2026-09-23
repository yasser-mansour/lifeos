package com.lifeos.app.ui.finance

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AccountBalanceWallet
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
import com.lifeos.app.data.local.entities.TransactionEntity
import com.lifeos.app.data.local.entities.TransferEntity
import com.lifeos.app.ui.components.EmptyState
import com.lifeos.app.ui.components.ScreenHeader
import com.lifeos.app.ui.components.SectionLabel
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.Spacing
import com.lifeos.app.ui.theme.monoFamily
import com.lifeos.app.ui.format.formatMoney
import com.lifeos.app.ui.format.formatMoneySigned
import java.math.BigDecimal

/** One row in the merged Recent feed — a transaction and a transfer render
 * differently but share one reverse-chronological list (spec §25). */
private sealed class ActivityRow(val dateEpochDay: Long, val updatedAtEpochMs: Long) {
    class Txn(val entity: TransactionEntity) : ActivityRow(entity.dateEpochDay, entity.updatedAtEpochMs)
    class Xfer(val entity: TransferEntity) : ActivityRow(entity.dateEpochDay, entity.updatedAtEpochMs)
}

@Composable
fun FinanceScreen(viewModel: FinanceViewModel, onAddTransaction: () -> Unit, onAddTransfer: () -> Unit, onOpenAccount: (String) -> Unit, onFunds: () -> Unit) {
    val state by viewModel.homeState.collectAsState()
    val colors = LocalLifeOSColors.current

    Scaffold(
        containerColor = colors.bgPrimary,
        floatingActionButton = {
            FloatingActionButton(onClick = onAddTransaction, containerColor = colors.accent) {
                Icon(Icons.Filled.Add, contentDescription = "Add Transaction", tint = Color.White)
            }
        },
    ) { padding ->
        LazyColumn(modifier = Modifier.fillMaxSize().padding(padding).padding(horizontal = Spacing.xl)) {
            item {
                ScreenHeader(
                    "Finance",
                    action = { Text("Funds", color = colors.accent, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.clickable(onClick = onFunds)) },
                )
            }

            if (state.accounts.isEmpty()) {
                item { EmptyState(icon = Icons.Filled.AccountBalanceWallet, title = "No accounts yet", body = "Add an account on your Mac to get started.") }
            } else {
                val currencies = state.accounts.map { it.account.currency }.distinct()
                val personal = state.accounts.filter { it.account.context == "personal" }
                val business = state.accounts.filter { it.account.context == "business" }

                item {
                    Column(modifier = Modifier.padding(bottom = Spacing.xl2)) {
                        if (currencies.size == 1) {
                            SectionLabel("Total")
                            Text(
                                formatMoney(state.accounts.fold(BigDecimal.ZERO) { acc, a -> acc + a.liveBalance }, currencies.first()),
                                style = MaterialTheme.typography.displayMedium.copy(fontFamily = monoFamily, fontWeight = FontWeight.SemiBold),
                                color = colors.textPrimary,
                            )
                            if (personal.isNotEmpty() && business.isNotEmpty()) {
                                Row(modifier = Modifier.fillMaxWidth().padding(top = Spacing.md), horizontalArrangement = Arrangement.spacedBy(Spacing.xl2)) {
                                    Column {
                                        Text("Personal", style = MaterialTheme.typography.bodySmall, color = colors.textMuted)
                                        Text(
                                            formatMoney(personal.fold(BigDecimal.ZERO) { acc, a -> acc + a.liveBalance }, currencies.first()),
                                            style = MaterialTheme.typography.titleMedium.copy(fontFamily = monoFamily), color = colors.textSecondary,
                                        )
                                    }
                                    Column {
                                        Text("Business", style = MaterialTheme.typography.bodySmall, color = colors.textMuted)
                                        Text(
                                            formatMoney(business.fold(BigDecimal.ZERO) { acc, a -> acc + a.liveBalance }, currencies.first()),
                                            style = MaterialTheme.typography.titleMedium.copy(fontFamily = monoFamily), color = colors.textSecondary,
                                        )
                                    }
                                }
                            }
                            // "Where it is" (Bank/Cash/Wallet...) as opposed to whose it
                            // is (Personal/Business, above) or what it's for (Fund) —
                            // spec §27. Grouped client-side from already-synced accounts,
                            // the same way Personal/Business is, rather than a new sync field.
                            val byType = state.accounts.groupBy { it.account.accountType }
                            if (byType.size > 1) {
                                Row(
                                    modifier = Modifier.fillMaxWidth().padding(top = Spacing.md),
                                    horizontalArrangement = Arrangement.spacedBy(Spacing.xl2),
                                ) {
                                    byType.forEach { (type, entries) ->
                                        Column {
                                            Text(
                                                type.replaceFirstChar { it.uppercase() }, style = MaterialTheme.typography.bodySmall, color = colors.textMuted,
                                            )
                                            Text(
                                                formatMoney(entries.fold(BigDecimal.ZERO) { acc, a -> acc + a.liveBalance }, currencies.first()),
                                                style = MaterialTheme.typography.titleMedium.copy(fontFamily = monoFamily), color = colors.textSecondary,
                                            )
                                        }
                                    }
                                }
                            }
                        }
                        androidx.compose.material3.TextButton(onClick = onAddTransfer, modifier = Modifier.padding(top = Spacing.sm)) {
                            Text("Transfer between accounts")
                        }
                    }
                }

                item { SectionLabel("Accounts") }
                items(state.accounts, key = { it.account.id }) { entry ->
                    Row(
                        modifier = Modifier.fillMaxWidth().clickable { onOpenAccount(entry.account.id) }.padding(vertical = Spacing.sm),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Text(entry.account.name, color = colors.textPrimary, style = MaterialTheme.typography.titleMedium)
                        Text(
                            formatMoney(entry.liveBalance, entry.account.currency),
                            color = colors.textPrimary, style = MaterialTheme.typography.titleMedium.copy(fontFamily = monoFamily),
                        )
                    }
                }

                item { SectionLabel("Recent", modifier = Modifier.padding(top = Spacing.xl)) }
                val merged: List<ActivityRow> = (state.recentTransactions.map { ActivityRow.Txn(it) } + state.recentTransfers.map { ActivityRow.Xfer(it) })
                    .sortedWith(compareByDescending<ActivityRow> { it.dateEpochDay }.thenByDescending { it.updatedAtEpochMs })
                    .take(20)
                if (merged.isEmpty()) {
                    item { Text("No activity yet.", color = colors.textMuted, style = MaterialTheme.typography.bodyMedium) }
                } else {
                    items(
                        merged,
                        key = { row -> when (row) { is ActivityRow.Txn -> "txn_${row.entity.id}"; is ActivityRow.Xfer -> "xfer_${row.entity.id}" } },
                    ) { row ->
                        when (row) {
                            is ActivityRow.Txn -> {
                                val txn = row.entity
                                Row(modifier = Modifier.fillMaxWidth().padding(vertical = Spacing.sm), horizontalArrangement = Arrangement.SpaceBetween) {
                                    Column {
                                        Text(txn.description.ifBlank { txn.type.replaceFirstChar { it.uppercase() } }, color = colors.textPrimary)
                                        Text(txn.categoryName ?: txn.type, color = colors.textMuted, style = MaterialTheme.typography.bodySmall)
                                    }
                                    Text(
                                        formatMoneySigned(txn.signedAmountDecimal(), txn.currency),
                                        style = MaterialTheme.typography.bodyLarge.copy(fontFamily = monoFamily),
                                        color = if (txn.direction == "in") colors.success else colors.textPrimary,
                                    )
                                }
                            }
                            is ActivityRow.Xfer -> {
                                val transfer = row.entity
                                val fromName = state.accounts.firstOrNull { it.account.id == transfer.fromAccountId }?.account?.name ?: "Account"
                                val toName = state.accounts.firstOrNull { it.account.id == transfer.toAccountId }?.account?.name ?: "Account"
                                Row(modifier = Modifier.fillMaxWidth().padding(vertical = Spacing.sm), horizontalArrangement = Arrangement.SpaceBetween) {
                                    Column {
                                        Text("Transfer", color = colors.textPrimary)
                                        Text("$fromName → $toName", color = colors.textMuted, style = MaterialTheme.typography.bodySmall)
                                    }
                                    Text(
                                        formatMoney(transfer.amountDecimal(), transfer.currency),
                                        style = MaterialTheme.typography.bodyLarge.copy(fontFamily = monoFamily), color = colors.textSecondary,
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
