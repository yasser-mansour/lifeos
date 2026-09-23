package com.lifeos.app.ui.people

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import com.lifeos.app.ui.components.ScreenHeader
import com.lifeos.app.ui.components.SectionLabel
import com.lifeos.app.ui.components.StatRow
import com.lifeos.app.ui.finance.TransactionRow
import com.lifeos.app.ui.format.formatMoneySigned
import com.lifeos.app.ui.format.relationshipLabels
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.Spacing
import java.math.BigDecimal
import java.util.Locale

/**
 * Contact / Finance — the Organization-side equivalent of
 * PersonDetailScreen, minus a Tasks section (nothing on Android links a
 * Task to an Organization, matching the backend's identical gap).
 */
@Composable
fun OrganizationDetailScreen(viewModel: PeopleViewModel, organizationId: String) {
    val colors = LocalLifeOSColors.current
    val state by remember(organizationId) { viewModel.organizationDetailState(organizationId) }.collectAsState()
    val org = state.organization ?: return

    LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = Spacing.xl)) {
        item {
            ScreenHeader(org.name)
            val labels = relationshipLabels(org.relationshipTypesJson)
            Text(
                (listOf(org.category.replaceFirstChar { it.uppercase(Locale.getDefault()) }) + labels).joinToString(" · "),
                style = MaterialTheme.typography.bodyMedium, color = colors.textSecondary, modifier = Modifier.padding(bottom = Spacing.md),
            )
        }

        item {
            SectionLabel("Contact", modifier = Modifier.padding(bottom = Spacing.xs))
            if (org.email.isBlank() && org.phone.isBlank() && org.website.isBlank()) {
                Text("No contact details yet.", color = colors.textMuted, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(bottom = Spacing.lg))
            } else {
                Column(modifier = Modifier.padding(bottom = Spacing.lg)) {
                    if (org.website.isNotBlank()) StatRow("Website", org.website)
                    if (org.email.isNotBlank()) StatRow("Email", org.email)
                    if (org.phone.isNotBlank()) StatRow("Phone", org.phone)
                }
            }
        }

        item {
            SectionLabel(
                if (state.transactions.isEmpty()) "Finance" else "Finance (${state.transactions.size})",
                modifier = Modifier.padding(bottom = Spacing.xs),
            )
        }
        if (state.transactions.isEmpty()) {
            item { Text("No transactions tagged to this organization.", color = colors.textMuted, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(bottom = Spacing.xl3)) }
        } else {
            item {
                val net = state.transactions.fold(BigDecimal.ZERO) { acc, txn -> acc + txn.signedAmountDecimal() }
                StatRow("Net", formatMoneySigned(net, state.transactions.first().currency), modifier = Modifier.padding(bottom = Spacing.sm))
            }
            items(state.transactions, key = { it.id }) { txn -> TransactionRow(txn) }
            item { androidx.compose.foundation.layout.Spacer(modifier = Modifier.padding(bottom = Spacing.xl3)) }
        }

        if (org.notes.isNotBlank()) {
            item {
                SectionLabel("Notes", modifier = Modifier.padding(bottom = Spacing.xs))
                Text(org.notes, color = colors.textSecondary, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(bottom = Spacing.xl3))
            }
        }
    }
}
