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
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import com.lifeos.app.data.local.entities.TransactionEntity
import com.lifeos.app.data.local.entities.TransferEntity
import com.lifeos.app.ui.components.ConfirmationDialog
import com.lifeos.app.ui.components.PrimaryButton
import com.lifeos.app.ui.components.ScreenHeader
import com.lifeos.app.ui.components.SectionLabel
import com.lifeos.app.ui.format.formatMoney
import com.lifeos.app.ui.format.formatMoneySigned
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.Spacing
import com.lifeos.app.ui.theme.monoFamily
import java.math.BigDecimal
import java.time.LocalDate

private sealed class AccountRow(val dateEpochDay: Long, val updatedAtEpochMs: Long) {
    class Txn(val entity: TransactionEntity) : AccountRow(entity.dateEpochDay, entity.updatedAtEpochMs)
    class Xfer(val entity: TransferEntity, val outgoing: Boolean) : AccountRow(entity.dateEpochDay, entity.updatedAtEpochMs)
}

@Composable
fun AccountDetailScreen(viewModel: FinanceViewModel, accountId: String, onAddTransaction: () -> Unit, onAddTransfer: () -> Unit) {
    val homeState by viewModel.homeState.collectAsState()
    val account = homeState.accounts.firstOrNull { it.account.id == accountId } ?: return
    val transactions by viewModel.transactionsForAccount(accountId).collectAsState(initial = emptyList())
    val transfers by viewModel.transfersForAccount(accountId).collectAsState(initial = emptyList())
    val colors = LocalLifeOSColors.current
    var pendingDelete by remember { mutableStateOf<AccountRow?>(null) }

    val thisMonth = LocalDate.now().let { it.year * 100 + it.monthValue }
    val monthTxns = transactions.filter { LocalDate.ofEpochDay(it.dateEpochDay).let { d -> d.year * 100 + d.monthValue } == thisMonth }
    val monthIn = monthTxns.filter { it.direction == "in" }.fold(BigDecimal.ZERO) { acc, t -> acc + t.amountDecimal() }
    val monthOut = monthTxns.filter { it.direction == "out" }.fold(BigDecimal.ZERO) { acc, t -> acc + t.amountDecimal() }

    LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = Spacing.xl)) {
        item {
            ScreenHeader(account.account.name)
            Text(
                formatMoney(account.liveBalance, account.account.currency),
                style = MaterialTheme.typography.displayMedium.copy(fontFamily = monoFamily, fontWeight = FontWeight.SemiBold),
                color = colors.textPrimary,
            )
            Row(modifier = Modifier.fillMaxWidth().padding(top = Spacing.md, bottom = Spacing.lg), horizontalArrangement = Arrangement.spacedBy(Spacing.xl2)) {
                Column {
                    Text("In this month", style = MaterialTheme.typography.bodySmall, color = colors.textMuted)
                    Text(formatMoney(monthIn, account.account.currency), style = MaterialTheme.typography.titleMedium.copy(fontFamily = monoFamily), color = colors.success)
                }
                Column {
                    Text("Out this month", style = MaterialTheme.typography.bodySmall, color = colors.textMuted)
                    Text(formatMoney(monthOut, account.account.currency), style = MaterialTheme.typography.titleMedium.copy(fontFamily = monoFamily), color = colors.textSecondary)
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.md), modifier = Modifier.padding(bottom = Spacing.xl2)) {
                PrimaryButton(text = "Add Transaction", onClick = onAddTransaction)
                androidx.compose.material3.OutlinedButton(onClick = onAddTransfer) { Text("Transfer") }
            }
            SectionLabel("Activity")
        }

        val merged: List<AccountRow> = (
            transactions.map { AccountRow.Txn(it) } +
                transfers.map { AccountRow.Xfer(it, outgoing = it.fromAccountId == accountId) }
            ).sortedWith(compareByDescending<AccountRow> { it.dateEpochDay }.thenByDescending { it.updatedAtEpochMs })

        if (merged.isEmpty()) {
            item { Text("No activity yet.", color = colors.textMuted, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(vertical = Spacing.lg)) }
        } else {
            items(
                merged,
                key = { row -> when (row) { is AccountRow.Txn -> "txn_${row.entity.id}"; is AccountRow.Xfer -> "xfer_${row.entity.id}" } },
            ) { row ->
                Row(
                    modifier = Modifier.fillMaxWidth().clickable { pendingDelete = row }.padding(vertical = Spacing.sm),
                    horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically,
                ) {
                    when (row) {
                        is AccountRow.Txn -> {
                            val txn = row.entity
                            Column(modifier = Modifier.weight(1f)) {
                                Text(txn.description.ifBlank { txn.type.replaceFirstChar { it.uppercase() } }, color = colors.textPrimary)
                                Text(txn.categoryName ?: txn.type, color = colors.textMuted, style = MaterialTheme.typography.bodySmall)
                            }
                            Text(
                                formatMoneySigned(txn.signedAmountDecimal(), txn.currency),
                                style = MaterialTheme.typography.bodyLarge.copy(fontFamily = monoFamily),
                                color = if (txn.direction == "in") colors.success else colors.textPrimary,
                            )
                        }
                        is AccountRow.Xfer -> {
                            val transfer = row.entity
                            Column(modifier = Modifier.weight(1f)) {
                                Text(if (row.outgoing) "Transfer out" else "Transfer in", color = colors.textPrimary)
                                Text(transfer.description.ifBlank { "Transfer" }, color = colors.textMuted, style = MaterialTheme.typography.bodySmall)
                            }
                            Text(
                                (if (row.outgoing) "−" else "+") + formatMoney(transfer.amountDecimal(), transfer.currency),
                                style = MaterialTheme.typography.bodyLarge.copy(fontFamily = monoFamily),
                                color = if (row.outgoing) colors.textPrimary else colors.success,
                            )
                        }
                    }
                }
            }
            item {
                Text(
                    "Tap an entry to delete it.", style = MaterialTheme.typography.bodySmall, color = colors.textMuted,
                    modifier = Modifier.padding(top = Spacing.sm, bottom = Spacing.xl),
                )
            }
        }
    }

    val toDelete = pendingDelete
    if (toDelete != null) {
        when (toDelete) {
            is AccountRow.Txn -> ConfirmationDialog(
                title = "Delete transaction?",
                message = "This removes it from your records. This can't be undone from your phone.",
                confirmLabel = "Delete",
                onConfirm = { viewModel.deleteTransaction(toDelete.entity.id); pendingDelete = null },
                onDismiss = { pendingDelete = null },
            )
            is AccountRow.Xfer -> ConfirmationDialog(
                title = "Delete transfer?",
                message = "This affects both accounts — the money moves back on both sides.",
                confirmLabel = "Delete",
                onConfirm = { viewModel.deleteTransfer(toDelete.entity.id); pendingDelete = null },
                onDismiss = { pendingDelete = null },
            )
        }
    }
}
