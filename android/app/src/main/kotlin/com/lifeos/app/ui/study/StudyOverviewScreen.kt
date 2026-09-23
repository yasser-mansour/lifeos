package com.lifeos.app.ui.study

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import com.lifeos.app.data.local.entities.FOCUS_DOMAINS
import com.lifeos.app.ui.components.EmptyState
import com.lifeos.app.ui.components.FilterChipRow
import com.lifeos.app.ui.components.LifeOSListRow
import com.lifeos.app.ui.components.PrimaryButton
import com.lifeos.app.ui.components.ScreenHeader
import com.lifeos.app.ui.components.SectionLabel
import com.lifeos.app.ui.components.StatRow
import com.lifeos.app.ui.format.formatDurationCompact
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.Spacing
import java.time.Instant
import java.time.ZoneId

/**
 * The general Focus overview — a calm today-summary (spec §11), not a
 * dashboard: total, then a breakdown by domain only when there's more than
 * one domain's worth of time to break down, then recent sessions filterable
 * by domain. "Study" is this same screen with the School chip selected.
 */
@Composable
fun StudyOverviewScreen(viewModel: StudyViewModel, onStartFocus: () -> Unit, onActiveSession: () -> Unit) {
    val state by viewModel.overviewState.collectAsState()
    val colors = LocalLifeOSColors.current
    var domainFilter by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(state.activeSession?.id) {
        if (state.activeSession != null) onActiveSession()
    }
    if (state.activeSession != null) return

    val filteredSessions = if (domainFilter == null) state.recentSessions else state.recentSessions.filter { it.domain == domainFilter }
    val domainsWithTime = state.todayByDomain.filterValues { it > 0 }

    LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = Spacing.xl)) {
        item {
            ScreenHeader("Focus")
            Text("Today", style = MaterialTheme.typography.bodyMedium, color = colors.textMuted)
            Text(
                formatDurationCompact(state.todaySeconds),
                style = MaterialTheme.typography.displayMedium.copy(fontFamily = com.lifeos.app.ui.theme.monoFamily, fontWeight = FontWeight.SemiBold),
                color = colors.textPrimary, modifier = Modifier.padding(bottom = Spacing.md),
            )
            if (domainsWithTime.size > 1) {
                Column(verticalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(bottom = Spacing.lg)) {
                    domainsWithTime.entries.sortedByDescending { it.value }.forEach { (domain, seconds) ->
                        val label = FOCUS_DOMAINS.firstOrNull { it.first == domain }?.second ?: domain
                        StatRow(label = label, value = formatDurationCompact(seconds))
                    }
                }
            }
            PrimaryButton(text = "Start Focus", onClick = onStartFocus, modifier = Modifier.fillMaxWidth().padding(bottom = Spacing.lg))
            FilterChipRow(
                options = FOCUS_DOMAINS, selected = domainFilter, onSelect = { domainFilter = it },
                modifier = Modifier.padding(bottom = Spacing.lg),
            )
        }

        item { SectionLabel("Recent") }

        if (filteredSessions.isEmpty()) {
            item {
                EmptyState(
                    icon = Icons.Filled.PlayArrow, title = "No sessions yet",
                    body = if (domainFilter == null) "Start your first focus session — stopwatch, countdown, or Pomodoro." else "Nothing here yet for this filter.",
                )
            }
        } else {
            items(filteredSessions, key = { it.id }) { session ->
                val date = Instant.ofEpochMilli(session.startedAtEpochMs).atZone(ZoneId.systemDefault()).toLocalDate()
                LifeOSListRow(
                    title = session.courseName ?: session.projectName ?: session.bookName ?: "Focus session",
                    subtitle = "$date · ${session.mode.replaceFirstChar { it.uppercase() }}",
                )
            }
        }
    }
}
