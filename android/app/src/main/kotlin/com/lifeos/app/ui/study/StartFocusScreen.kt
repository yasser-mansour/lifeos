package com.lifeos.app.ui.study

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.selection.selectable
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.lifeos.app.data.local.dao.RecentFocusContext
import com.lifeos.app.data.local.entities.FOCUS_DOMAINS
import com.lifeos.app.data.local.entities.SCHOOL_DOMAINS
import com.lifeos.app.ui.components.FilterChipRow
import com.lifeos.app.ui.components.PrimaryButton
import com.lifeos.app.ui.components.ScreenHeader
import com.lifeos.app.ui.components.SectionLabel
import com.lifeos.app.ui.haptics.rememberLifeOsHaptics
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.Spacing

private val MODES = listOf("stopwatch" to "Stopwatch", "countdown" to "Countdown", "pomodoro" to "Pomodoro")
private val COUNTDOWN_PRESETS = listOf(10, 15, 25, 30, 45, 60, 90)

/**
 * Start Focus, rebuilt to be fast (spec §12/§13): pick a domain, pick a
 * recent context (or search the full list), pick a mode, go. Recent
 * contexts come straight from session history — no separate "favorites" to
 * maintain — so the very first thing a repeat session shows is exactly
 * what was last used in that domain.
 */
@Composable
fun StartFocusScreen(
    viewModel: StudyViewModel, onStarted: () -> Unit, initialDomain: String = "school",
    initialProjectId: String? = null, initialCourseId: String? = null,
) {
    val state by viewModel.overviewState.collectAsState()
    val projects by viewModel.projects.collectAsState(initial = emptyList())
    val colors = LocalLifeOSColors.current
    val haptics = rememberLifeOsHaptics()

    var domain by remember { mutableStateOf(initialDomain) }
    // Only the id is ever tracked as state — the display name is resolved
    // from the already-loaded course/project list at the point of use, so a
    // create-in-context launch (e.g. "Start Focus" from a Task, spec §16)
    // only needs to pass an id and never has two variables that can drift.
    var selectedCourseId by remember { mutableStateOf(initialCourseId) }
    var selectedProjectId by remember { mutableStateOf(initialProjectId) }
    var mode by remember { mutableStateOf("stopwatch") }
    var countdownMinutes by remember { mutableStateOf(25) }
    var showPomodoroSettings by remember { mutableStateOf(false) }
    var pomodoroFocus by remember { mutableStateOf(25) }
    var pomodoroShortBreak by remember { mutableStateOf(5) }
    var pomodoroLongBreak by remember { mutableStateOf(15) }
    var pomodoroCycles by remember { mutableStateOf(4) }

    var recentCourses by remember { mutableStateOf<List<RecentFocusContext>>(emptyList()) }
    var recentProjects by remember { mutableStateOf<List<RecentFocusContext>>(emptyList()) }
    LaunchedEffect(domain) {
        if (domain == "school") recentCourses = viewModel.recentCourses()
        if (domain != "school") recentProjects = viewModel.recentProjects(domain)
    }

    LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = Spacing.xl)) {
        item { ScreenHeader("Start Focus") }

        item {
            SectionLabel("What are you focusing on?")
            FilterChipRow(
                options = FOCUS_DOMAINS, selected = domain,
                onSelect = { domain = it ?: "other"; selectedCourseId = null; selectedProjectId = null },
                allLabel = null, modifier = Modifier.padding(bottom = Spacing.lg),
            )
        }

        if (domain in SCHOOL_DOMAINS) {
            if (recentCourses.isNotEmpty()) {
                item { SectionLabel("Recent") }
                items(recentCourses, key = { "recent_${it.id}" }) { recent ->
                    ContextOptionRow(
                        label = recent.name, selected = selectedCourseId == recent.id,
                        onSelect = { selectedCourseId = recent.id },
                    )
                }
            }
            item { SectionLabel("All courses", modifier = Modifier.padding(top = Spacing.lg)) }
            items(state.courses, key = { it.id }) { course ->
                ContextOptionRow(
                    label = course.name, selected = selectedCourseId == course.id,
                    onSelect = { selectedCourseId = course.id },
                )
            }
        } else if (domain == "project" || domain == "business") {
            if (recentProjects.isNotEmpty()) {
                item { SectionLabel("Recent") }
                items(recentProjects, key = { "recent_${it.id}" }) { recent ->
                    ContextOptionRow(
                        label = recent.name, selected = selectedProjectId == recent.id,
                        onSelect = { selectedProjectId = recent.id },
                    )
                }
            }
            item { SectionLabel("All projects", modifier = Modifier.padding(top = Spacing.lg)) }
            items(projects, key = { it.id }) { project ->
                ContextOptionRow(
                    label = project.name, selected = selectedProjectId == project.id,
                    onSelect = { selectedProjectId = project.id },
                )
            }
        }

        item {
            SectionLabel("Mode", modifier = Modifier.padding(top = Spacing.lg))
            Column {
                MODES.forEach { (value, label) ->
                    Row(
                        modifier = Modifier.fillMaxWidth().selectable(selected = mode == value) { mode = value }.padding(vertical = Spacing.sm),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        RadioButton(selected = mode == value, onClick = null)
                        Text(label, color = colors.textPrimary, modifier = Modifier.padding(start = Spacing.sm))
                    }
                }
            }
        }

        if (mode == "countdown") {
            item {
                SectionLabel("Duration", modifier = Modifier.padding(top = Spacing.sm))
                Row(modifier = Modifier.fillMaxWidth()) {
                    COUNTDOWN_PRESETS.forEach { minutes ->
                        Text(
                            "${minutes}m",
                            color = if (countdownMinutes == minutes) colors.accent else colors.textSecondary,
                            fontWeight = if (countdownMinutes == minutes) FontWeight.SemiBold else FontWeight.Normal,
                            modifier = Modifier
                                .padding(end = Spacing.lg)
                                .selectable(selected = countdownMinutes == minutes) { countdownMinutes = minutes },
                        )
                    }
                }
            }
        }

        if (mode == "pomodoro") {
            item {
                Text(
                    "$pomodoroFocus min focus · $pomodoroShortBreak min break · $pomodoroCycles cycles",
                    style = androidx.compose.material3.MaterialTheme.typography.bodyMedium, color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.sm),
                )
                Text(
                    if (showPomodoroSettings) "Hide customization" else "Customize",
                    color = colors.accent, style = androidx.compose.material3.MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.padding(top = Spacing.xs).clickable { showPomodoroSettings = !showPomodoroSettings },
                )
            }
            if (showPomodoroSettings) {
                item {
                    MinutesStepper("Focus", pomodoroFocus, onChange = { pomodoroFocus = it })
                    MinutesStepper("Short break", pomodoroShortBreak, onChange = { pomodoroShortBreak = it })
                    MinutesStepper("Long break", pomodoroLongBreak, onChange = { pomodoroLongBreak = it })
                    MinutesStepper("Cycles before long break", pomodoroCycles, onChange = { pomodoroCycles = it }, min = 1)
                }
            }
        }

        item {
            PrimaryButton(
                text = "Start",
                onClick = {
                    haptics.tick()
                    val course = selectedCourseId.takeIf { domain in SCHOOL_DOMAINS }
                    val courseName = course?.let { id -> state.courses.firstOrNull { it.id == id }?.name }
                    val project = selectedProjectId.takeIf { domain == "project" || domain == "business" }
                    val projectName = project?.let { id -> projects.firstOrNull { it.id == id }?.name }
                    viewModel.startSession(
                        domain = domain, courseId = course, courseName = courseName, projectId = project, projectName = projectName,
                        mode = mode, plannedMinutes = if (mode == "countdown") countdownMinutes else null,
                        pomodoroFocusMinutes = pomodoroFocus, pomodoroShortBreakMinutes = pomodoroShortBreak,
                        pomodoroLongBreakMinutes = pomodoroLongBreak, pomodoroCycles = pomodoroCycles,
                    )
                    onStarted()
                },
                modifier = Modifier.fillMaxWidth().padding(top = Spacing.xl3, bottom = Spacing.xl2),
            )
        }
    }
}

@Composable
private fun ContextOptionRow(label: String, selected: Boolean, onSelect: () -> Unit) {
    val colors = LocalLifeOSColors.current
    Row(
        modifier = Modifier.fillMaxWidth().selectable(selected = selected, onClick = onSelect).padding(vertical = Spacing.sm),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        RadioButton(selected = selected, onClick = null)
        Text(label, color = colors.textPrimary, modifier = Modifier.padding(start = Spacing.sm))
    }
}

@Composable
private fun MinutesStepper(label: String, value: Int, onChange: (Int) -> Unit, min: Int = 1, max: Int = 120) {
    val colors = LocalLifeOSColors.current
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = Spacing.xs),
        horizontalArrangement = androidx.compose.foundation.layout.Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(label, color = colors.textSecondary)
        Row(verticalAlignment = Alignment.CenterVertically) {
            androidx.compose.material3.IconButton(
                onClick = { if (value > min) onChange(value - 1) },
                modifier = Modifier.semantics { contentDescription = "Decrease $label" },
            ) {
                Text("−", color = colors.accent, style = androidx.compose.material3.MaterialTheme.typography.titleLarge)
            }
            Text("$value", color = colors.textPrimary, modifier = Modifier.padding(horizontal = Spacing.sm))
            androidx.compose.material3.IconButton(
                onClick = { if (value < max) onChange(value + 1) },
                modifier = Modifier.semantics { contentDescription = "Increase $label" },
            ) {
                Text("+", color = colors.accent, style = androidx.compose.material3.MaterialTheme.typography.titleLarge)
            }
        }
    }
}
