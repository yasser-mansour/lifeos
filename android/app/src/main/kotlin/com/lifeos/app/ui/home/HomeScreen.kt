package com.lifeos.app.ui.home

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import com.lifeos.app.data.local.entities.FOCUS_DOMAINS
import com.lifeos.app.ui.components.LifeOSListRow
import com.lifeos.app.ui.components.PrimaryButton
import com.lifeos.app.ui.components.SectionLabel
import com.lifeos.app.ui.format.formatDurationCompact
import com.lifeos.app.ui.format.formatMoney
import com.lifeos.app.ui.format.formatMoneySigned
import com.lifeos.app.ui.format.taskSubtitle
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.Spacing
import com.lifeos.app.ui.theme.monoFamily
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.time.format.TextStyle
import java.util.Locale

/**
 * Home, rebuilt from zero as an orientation layer (spec §8) — not a
 * dashboard, not a card grid. NEXT / FOCUS / MONEY / RECENT, in the order a
 * person would actually ask those questions, separated by plain dividers,
 * nothing competing for attention except the one primary action per
 * section. Deliberately does not show Projects — that's a deeper-review
 * surface, and Android's Home is for orientation, not management.
 */
@Composable
fun HomeScreen(viewModel: HomeViewModel, onStartFocus: () -> Unit, onOpenActiveSession: () -> Unit, onShowAllTasks: () -> Unit) {
    val state by viewModel.uiState.collectAsState()
    val colors = LocalLifeOSColors.current

    LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = Spacing.xl)) {
        item {
            Text(
                LocalDate.now().let { "${it.dayOfWeek.getDisplayName(TextStyle.FULL, Locale.getDefault())}, ${it.format(DateTimeFormatter.ofPattern("MMM d"))}" },
                style = MaterialTheme.typography.headlineLarge, color = colors.textPrimary, fontWeight = FontWeight.SemiBold,
                modifier = Modifier.padding(top = Spacing.xl, bottom = Spacing.xl2),
            )
        }

        item { SectionLabel("Next") }
        if (state.openTasks.isEmpty()) {
            item { Text("Nothing due.", color = colors.textMuted, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(bottom = Spacing.sm)) }
        } else {
            items(state.openTasks, key = { it.id }) { task ->
                LifeOSListRow(title = task.title, subtitle = taskSubtitle(task.projectName ?: task.courseName, task.dueDateEpochDay))
            }
        }
        item {
            Text(
                "Show all →", color = colors.accent, style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(top = Spacing.xs, bottom = Spacing.xl).clickable(onClick = onShowAllTasks),
            )
        }

        item { HomeDivider() }

        item {
            SectionLabel("Focus")
            Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
                Text(
                    formatDurationCompact(state.todayFocusSeconds),
                    style = MaterialTheme.typography.displayMedium.copy(fontFamily = monoFamily, fontWeight = FontWeight.SemiBold), color = colors.textPrimary,
                )
                Text("today", style = MaterialTheme.typography.bodyMedium, color = colors.textMuted, modifier = Modifier.padding(bottom = Spacing.xs))
            }
            state.todayTopDomain?.let { (domain, seconds) ->
                val label = FOCUS_DOMAINS.firstOrNull { it.first == domain }?.second ?: domain
                Text(
                    "${formatDurationCompact(seconds)} $label", style = MaterialTheme.typography.bodyMedium, color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xs, bottom = Spacing.md),
                )
            }
            PrimaryButton(
                text = if (state.activeSession != null) "Active Session" else "Start Focus",
                onClick = if (state.activeSession != null) onOpenActiveSession else onStartFocus,
                modifier = Modifier.fillMaxWidth().padding(top = Spacing.sm, bottom = Spacing.xl),
            )
        }

        item { HomeDivider() }

        item {
            SectionLabel("Money")
            if (state.singleCurrency != null) {
                Text(
                    formatMoney(state.totalBalance, state.singleCurrency!!), style = MaterialTheme.typography.displayMedium.copy(fontFamily = monoFamily, fontWeight = FontWeight.SemiBold),
                    color = colors.textPrimary, modifier = Modifier.padding(bottom = Spacing.md),
                )
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("Personal", color = colors.textSecondary, style = MaterialTheme.typography.bodyMedium)
                    Text(formatMoney(state.personalBalance, state.singleCurrency!!), color = colors.textPrimary, style = MaterialTheme.typography.titleMedium.copy(fontFamily = monoFamily))
                }
                Row(modifier = Modifier.fillMaxWidth().padding(top = Spacing.xs, bottom = Spacing.xl), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("Business", color = colors.textSecondary, style = MaterialTheme.typography.bodyMedium)
                    Text(formatMoney(state.businessBalance, state.singleCurrency!!), color = colors.textPrimary, style = MaterialTheme.typography.titleMedium.copy(fontFamily = monoFamily))
                }
            } else {
                Text("Add an account on your Mac to get started.", color = colors.textMuted, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(bottom = Spacing.xl))
            }
        }

        item { HomeDivider() }

        item { SectionLabel("Recent") }
        if (state.recentActivity.isEmpty()) {
            item { Text("Nothing yet.", color = colors.textMuted, style = MaterialTheme.typography.bodyMedium) }
        } else {
            items(state.recentActivity, key = { row -> when (row) {
                is HomeActivityRow.Money -> "txn_${row.transaction.id}"
                is HomeActivityRow.Focus -> "focus_${row.session.id}"
                is HomeActivityRow.TaskDone -> "task_${row.task.id}"
            } }) { row ->
                Row(modifier = Modifier.fillMaxWidth().padding(vertical = Spacing.xs), horizontalArrangement = Arrangement.SpaceBetween) {
                    when (row) {
                        is HomeActivityRow.Money -> {
                            Text(row.transaction.description.ifBlank { row.transaction.type.replaceFirstChar { it.uppercase() } }, color = colors.textPrimary)
                            Text(
                                formatMoneySigned(row.transaction.signedAmountDecimal(), row.transaction.currency),
                                style = MaterialTheme.typography.bodyMedium.copy(fontFamily = monoFamily),
                                color = if (row.transaction.direction == "in") colors.success else colors.textSecondary,
                            )
                        }
                        is HomeActivityRow.Focus -> {
                            Text(row.session.courseName ?: row.session.projectName ?: row.session.bookName ?: "Focus session", color = colors.textPrimary)
                            Text(formatDurationCompact(row.durationSeconds), style = MaterialTheme.typography.bodyMedium.copy(fontFamily = monoFamily), color = colors.textSecondary)
                        }
                        is HomeActivityRow.TaskDone -> {
                            Text(row.task.title, color = colors.textPrimary)
                            Text("Done", style = MaterialTheme.typography.bodyMedium, color = colors.success)
                        }
                    }
                }
            }
        }

        item { androidx.compose.foundation.layout.Spacer(modifier = Modifier.size(Spacing.xl4)) }
    }
}

@Composable
private fun HomeDivider() {
    androidx.compose.material3.HorizontalDivider(
        modifier = Modifier.padding(vertical = Spacing.md), color = LocalLifeOSColors.current.borderSubtle,
    )
}

