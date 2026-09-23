package com.lifeos.app.ui.finance

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import com.lifeos.app.ui.components.FilterChipRow
import com.lifeos.app.ui.components.LifeOsAmountInput
import com.lifeos.app.ui.components.PrimaryButton
import com.lifeos.app.ui.components.RelationOptionRow
import com.lifeos.app.ui.components.ScreenHeader
import com.lifeos.app.ui.components.SectionLabel
import com.lifeos.app.ui.haptics.rememberLifeOsHaptics
import com.lifeos.app.ui.theme.Spacing

private val TYPES = listOf("expense" to "Expense", "income" to "Income")

/**
 * Amount-first (spec §26): the keyboard is already up before anything else
 * is decided. Account, Fund, and category come right after — Fund is kept
 * as visible as Account rather than buried in "More details" (Finance V2
 * spec §63's own mockup shows "From: CIH / Fund: Living" as primary
 * fields) — project/counterparty/date sit behind "More details" so the
 * common case still stays a fast flow: amount, type, account, fund,
 * category, save.
 */
@Composable
fun AddTransactionScreen(
    viewModel: FinanceViewModel, onSaved: () -> Unit,
    initialAccountId: String? = null, initialProjectId: String? = null, initialPersonId: String? = null,
    initialFundId: String? = null, initialOrganizationId: String? = null,
) {
    val accounts by viewModel.accounts.collectAsState()
    val categories by viewModel.categories.collectAsState()
    val projects by viewModel.projects.collectAsState()
    val people by viewModel.people.collectAsState()
    val organizations by viewModel.organizations.collectAsState()
    val funds by viewModel.funds.collectAsState()
    val haptics = rememberLifeOsHaptics()

    var amountText by remember { mutableStateOf("") }
    var type by remember { mutableStateOf("expense") }
    var description by remember { mutableStateOf("") }
    var selectedAccountId by remember { mutableStateOf(initialAccountId ?: accounts.firstOrNull()?.id) }
    var selectedFundId by remember { mutableStateOf(initialFundId) }
    var selectedCategoryId by remember { mutableStateOf<String?>(null) }
    var selectedProjectId by remember { mutableStateOf(initialProjectId) }
    var selectedPersonId by remember { mutableStateOf(initialPersonId) }
    var selectedOrganizationId by remember { mutableStateOf(initialOrganizationId) }
    var showMore by remember { mutableStateOf(initialProjectId != null || initialPersonId != null || initialOrganizationId != null) }

    Column(modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = Spacing.xl)) {
        ScreenHeader("Add Transaction")

        LifeOsAmountInput(value = amountText, onValueChange = { amountText = it }, currency = "MAD")

        FilterChipRow(
            options = TYPES, selected = type, onSelect = { type = it ?: "expense" }, allLabel = null,
            modifier = Modifier.padding(top = Spacing.xl, bottom = Spacing.lg),
        )

        SectionLabel("Account")
        Column {
            accounts.forEach { account ->
                RelationOptionRow(label = account.name, selected = selectedAccountId == account.id, onSelect = { selectedAccountId = account.id })
            }
        }

        if (funds.isNotEmpty()) {
            SectionLabel("Fund", modifier = Modifier.padding(top = Spacing.lg))
            FilterChipRow(
                options = funds.map { it.fund.id to it.fund.name }, selected = selectedFundId,
                onSelect = { selectedFundId = it }, allLabel = "Unallocated",
            )
        }

        if (type == "expense" && categories.isNotEmpty()) {
            SectionLabel("Category", modifier = Modifier.padding(top = Spacing.lg))
            FilterChipRow(
                options = categories.map { it.id to it.name }, selected = selectedCategoryId,
                onSelect = { selectedCategoryId = it }, allLabel = null,
            )
        }

        OutlinedTextField(
            value = description, onValueChange = { description = it }, label = { Text("Description (optional)") },
            singleLine = true, modifier = Modifier.fillMaxWidth().padding(top = Spacing.lg),
        )

        Text(
            if (showMore) "Hide details" else "More details (project, counterparty)",
            color = androidx.compose.material3.MaterialTheme.colorScheme.primary,
            style = androidx.compose.material3.MaterialTheme.typography.bodyMedium,
            modifier = Modifier.padding(top = Spacing.lg).clickable { showMore = !showMore },
        )

        if (showMore) {
            SectionLabel("Project (optional)", modifier = Modifier.padding(top = Spacing.lg))
            Column {
                RelationOptionRow(label = "None", selected = selectedProjectId == null, onSelect = { selectedProjectId = null })
                projects.forEach { project -> RelationOptionRow(label = project.name, selected = selectedProjectId == project.id, onSelect = { selectedProjectId = project.id }) }
            }

            // Counterparty: exactly one of Person/Organization, mirroring
            // Transaction.person/.organization on the backend — selecting
            // one clears the other rather than allowing both.
            SectionLabel("Counterparty — person (optional)", modifier = Modifier.padding(top = Spacing.lg))
            Column {
                RelationOptionRow(label = "None", selected = selectedPersonId == null, onSelect = { selectedPersonId = null })
                people.forEach { person ->
                    RelationOptionRow(
                        label = person.name, selected = selectedPersonId == person.id,
                        onSelect = { selectedPersonId = person.id; selectedOrganizationId = null },
                    )
                }
            }

            SectionLabel("Counterparty — organization (optional)", modifier = Modifier.padding(top = Spacing.lg))
            Column {
                RelationOptionRow(label = "None", selected = selectedOrganizationId == null, onSelect = { selectedOrganizationId = null })
                organizations.forEach { org ->
                    RelationOptionRow(
                        label = org.name, selected = selectedOrganizationId == org.id,
                        onSelect = { selectedOrganizationId = org.id; selectedPersonId = null },
                    )
                }
            }
        }

        PrimaryButton(
            text = "Save",
            onClick = {
                val amount = amountText.toBigDecimalOrNull()
                val accountId = selectedAccountId
                if (accountId != null && amount != null && amount.signum() > 0) {
                    haptics.tick()
                    viewModel.addTransaction(
                        accountId, amount, type, selectedCategoryId, description, selectedProjectId, selectedPersonId,
                        selectedFundId, selectedOrganizationId,
                    )
                    onSaved()
                }
            },
            enabled = amountText.toBigDecimalOrNull()?.let { it.signum() > 0 } == true && selectedAccountId != null,
            modifier = Modifier.fillMaxWidth().padding(top = Spacing.xl3, bottom = Spacing.xl2),
        )
    }
}
