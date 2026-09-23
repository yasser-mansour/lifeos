package com.lifeos.app.ui.finance

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import com.lifeos.app.ui.components.LifeOsAmountInput
import com.lifeos.app.ui.components.PrimaryButton
import com.lifeos.app.ui.components.RelationOptionRow
import com.lifeos.app.ui.components.ScreenHeader
import com.lifeos.app.ui.components.SectionLabel
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.Spacing

/**
 * Transfers are first-class, not a special case of Add Transaction (spec
 * §29) — two account pickers, one amount, and copy that says outright that
 * this never touches income/expense totals.
 */
@Composable
fun AddTransferScreen(viewModel: FinanceViewModel, onSaved: () -> Unit, initialFromAccountId: String? = null) {
    val accounts by viewModel.accounts.collectAsState()
    val colors = LocalLifeOSColors.current

    var amountText by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var fromAccountId by remember { mutableStateOf(initialFromAccountId) }
    var toAccountId by remember { mutableStateOf<String?>(null) }

    Column(modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = Spacing.xl)) {
        ScreenHeader("Transfer")

        LifeOsAmountInput(value = amountText, onValueChange = { amountText = it }, currency = "MAD")

        SectionLabel("From", modifier = Modifier.padding(top = Spacing.xl))
        accounts.forEach { account ->
            RelationOptionRow(label = account.name, selected = fromAccountId == account.id, onSelect = { fromAccountId = account.id })
        }

        SectionLabel("To", modifier = Modifier.padding(top = Spacing.lg))
        accounts.filter { it.id != fromAccountId }.forEach { account ->
            RelationOptionRow(label = account.name, selected = toAccountId == account.id, onSelect = { toAccountId = account.id })
        }

        OutlinedTextField(
            value = description, onValueChange = { description = it }, label = { Text("Description (optional)") },
            singleLine = true, modifier = Modifier.fillMaxWidth().padding(top = Spacing.lg),
        )

        Text(
            "Transfers don't count as income or expense.",
            style = MaterialTheme.typography.bodySmall, color = colors.textMuted,
            modifier = Modifier.padding(top = Spacing.md),
        )

        PrimaryButton(
            text = "Transfer",
            onClick = {
                val amount = amountText.toBigDecimalOrNull()
                val from = fromAccountId
                val to = toAccountId
                if (amount != null && amount.signum() > 0 && from != null && to != null && from != to) {
                    viewModel.addTransfer(from, to, amount, description)
                    onSaved()
                }
            },
            enabled = amountText.toBigDecimalOrNull()?.let { it.signum() > 0 } == true && fromAccountId != null && toAccountId != null,
            modifier = Modifier.fillMaxWidth().padding(top = Spacing.xl2, bottom = Spacing.xl2),
        )
    }
}
