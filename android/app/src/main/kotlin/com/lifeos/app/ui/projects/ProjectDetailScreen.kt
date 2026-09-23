package com.lifeos.app.ui.projects

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import com.lifeos.app.ui.format.formatDurationCompact
import com.lifeos.app.ui.format.formatMoneySigned
import com.lifeos.app.ui.format.taskSubtitle
import com.lifeos.app.ui.haptics.rememberLifeOsHaptics
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.Spacing
import java.math.BigDecimal

/**
 * One scrollable screen with labeled sections rather than a TabRow (spec
 * §17's overview/tasks/finance/focus/notes tabs) — the same sectioned-scroll
 * shape AccountDetailScreen already uses for its own multi-part detail, kept
 * consistent rather than introducing a second detail pattern. People is
 * intentionally not a section here: Project<->Person is a many-to-many on
 * the backend that nothing in this Android build syncs yet (a real, disclosed
 * gap — see the rebuild report — not an oversight).
 */
@Composable
fun ProjectDetailScreen(viewModel: ProjectsViewModel, projectId: String, onOpenTasks: () -> Unit) {
    val colors = LocalLifeOSColors.current
    val state by remember(projectId) { viewModel.detailState(projectId) }.collectAsState()
    val project = state.project ?: return

    LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = Spacing.xl)) {
        item {
            ScreenHeader(project.name)
            Text(
                listOfNotNull(project.status.replaceFirstChar { it.uppercase() }, project.area.replaceFirstChar { it.uppercase() })
                    .joinToString(" · "),
                style = MaterialTheme.typography.bodyMedium, color = colors.textSecondary, modifier = Modifier.padding(bottom = Spacing.md),
            )
            if (project.description.isNotBlank()) {
                Text(
                    project.description, style = MaterialTheme.typography.bodyMedium, color = colors.textSecondary,
                    modifier = Modifier.padding(bottom = Spacing.lg),
                )
            }
        }

        item {
            SectionLabel("Focus", modifier = Modifier.padding(top = Spacing.md, bottom = Spacing.sm))
            StatRow("This week", formatDurationCompact(state.thisWeekFocusSeconds), modifier = Modifier.padding(bottom = Spacing.lg))
        }

        item {
            SectionLabel(
                if (state.openTasks.isEmpty()) "Tasks" else "Tasks (${state.openTasks.size} open)",
                modifier = Modifier.padding(bottom = Spacing.xs),
            )
        }
        if (state.openTasks.isEmpty()) {
            item { Text("No open tasks.", color = colors.textMuted, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(bottom = Spacing.md)) }
        } else {
            items(state.openTasks, key = { it.id }) { task ->
                TaskPreviewRow(task = task, onToggle = { viewModel.toggleTaskComplete(task) })
            }
        }
        item { TextButton(onClick = onOpenTasks, modifier = Modifier.padding(bottom = Spacing.lg)) { Text("Open Tasks →", color = colors.accent) } }

        item {
            SectionLabel(
                if (state.transactions.isEmpty()) "Finance" else "Finance (${state.transactions.size})",
                modifier = Modifier.padding(bottom = Spacing.xs),
            )
        }
        if (state.transactions.isEmpty()) {
            item { Text("No transactions tagged to this project.", color = colors.textMuted, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(bottom = Spacing.md)) }
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
            items(state.notes, key = { it.id }) { note -> NotePreviewRow(note) }
            item { androidx.compose.foundation.layout.Spacer(modifier = Modifier.padding(bottom = Spacing.xl3)) }
        }
    }
}

@Composable
private fun TaskPreviewRow(task: TaskEntity, onToggle: () -> Unit) {
    val haptics = rememberLifeOsHaptics()
    LifeOSListRow(
        title = task.title,
        subtitle = taskSubtitle(task.courseName, task.dueDateEpochDay),
        leading = {
            CheckToggle(
                checked = task.status == "done",
                onToggle = { if (task.status != "done") haptics.tick(); onToggle() },
            )
        },
    )
}

@Composable
private fun NotePreviewRow(note: NoteEntity) {
    LifeOSListRow(
        title = note.title.ifBlank { "Untitled note" },
        subtitle = note.content.take(80).ifBlank { null },
    )
}
