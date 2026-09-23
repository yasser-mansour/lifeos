package com.lifeos.app.ui.people

import androidx.compose.foundation.layout.Column
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
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import com.lifeos.app.data.local.entities.NoteEntity
import com.lifeos.app.data.local.entities.TaskEntity
import com.lifeos.app.ui.components.CheckToggle
import com.lifeos.app.ui.components.LifeOSListRow
import com.lifeos.app.ui.components.ScreenHeader
import com.lifeos.app.ui.components.SectionLabel
import com.lifeos.app.ui.components.StatRow
import com.lifeos.app.ui.finance.TransactionRow
import com.lifeos.app.ui.format.formatMoneySigned
import com.lifeos.app.ui.format.relationshipLabels
import com.lifeos.app.ui.format.taskSubtitle
import com.lifeos.app.ui.haptics.rememberLifeOsHaptics
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.Spacing
import java.math.BigDecimal

/**
 * Contact / Tasks / Finance / Notes — the same sectioned-scroll shape as
 * ProjectDetailScreen, minus a Projects section (spec's own mockup wants
 * one; see PeopleViewModel.detailState for why that's not built yet).
 */
@Composable
fun PersonDetailScreen(viewModel: PeopleViewModel, personId: String) {
    val colors = LocalLifeOSColors.current
    val state by remember(personId) { viewModel.detailState(personId) }.collectAsState()
    val person = state.person ?: return

    LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = Spacing.xl)) {
        item {
            ScreenHeader(person.name)
            val labels = relationshipLabels(person.relationshipTypesJson)
            if (labels.isNotEmpty() || person.organization.isNotBlank()) {
                Text(
                    (labels + listOfNotNull(person.organization.ifBlank { null })).joinToString(" · "),
                    style = MaterialTheme.typography.bodyMedium, color = colors.textSecondary, modifier = Modifier.padding(bottom = Spacing.md),
                )
            }
        }

        item {
            SectionLabel("Contact", modifier = Modifier.padding(bottom = Spacing.xs))
            if (person.email.isBlank() && person.phone.isBlank()) {
                Text("No contact details yet.", color = colors.textMuted, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(bottom = Spacing.lg))
            } else {
                Column(modifier = Modifier.padding(bottom = Spacing.lg)) {
                    if (person.email.isNotBlank()) StatRow("Email", person.email)
                    if (person.phone.isNotBlank()) StatRow("Phone", person.phone)
                }
            }
        }

        item {
            SectionLabel(
                if (state.openTasks.isEmpty()) "Tasks" else "Tasks (${state.openTasks.size} open)",
                modifier = Modifier.padding(bottom = Spacing.xs),
            )
        }
        if (state.openTasks.isEmpty()) {
            item { Text("No open tasks.", color = colors.textMuted, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(bottom = Spacing.lg)) }
        } else {
            items(state.openTasks, key = { it.id }) { task -> PersonTaskRow(task = task, onToggle = { viewModel.toggleTaskComplete(task) }) }
            item { androidx.compose.foundation.layout.Spacer(modifier = Modifier.padding(bottom = Spacing.md)) }
        }

        item {
            SectionLabel(
                if (state.transactions.isEmpty()) "Finance" else "Finance (${state.transactions.size})",
                modifier = Modifier.padding(bottom = Spacing.xs),
            )
        }
        if (state.transactions.isEmpty()) {
            item { Text("No transactions tagged to this person.", color = colors.textMuted, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(bottom = Spacing.lg)) }
        } else {
            item {
                val net = state.transactions.fold(BigDecimal.ZERO) { acc, txn -> acc + txn.signedAmountDecimal() }
                StatRow("Net", formatMoneySigned(net, state.transactions.first().currency), modifier = Modifier.padding(bottom = Spacing.sm))
            }
            items(state.transactions, key = { it.id }) { txn -> TransactionRow(txn) }
            item { androidx.compose.foundation.layout.Spacer(modifier = Modifier.padding(bottom = Spacing.lg)) }
        }

        item { SectionLabel(if (state.notes.isEmpty()) "Notes" else "Notes (${state.notes.size})", modifier = Modifier.padding(bottom = Spacing.xs)) }
        if (state.notes.isEmpty()) {
            item { Text("No notes yet.", color = colors.textMuted, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(bottom = Spacing.xl3)) }
        } else {
            items(state.notes, key = { it.id }) { note -> LifeOSListRow(title = note.title.ifBlank { "Untitled note" }, subtitle = note.content.take(80).ifBlank { null }) }
            item { androidx.compose.foundation.layout.Spacer(modifier = Modifier.padding(bottom = Spacing.xl3)) }
        }
    }
}

@Composable
private fun PersonTaskRow(task: TaskEntity, onToggle: () -> Unit) {
    val haptics = rememberLifeOsHaptics()
    LifeOSListRow(
        title = task.title,
        subtitle = taskSubtitle(task.projectName ?: task.courseName, task.dueDateEpochDay),
        leading = { CheckToggle(checked = task.status == "done", onToggle = { if (task.status != "done") haptics.tick(); onToggle() }) },
    )
}

