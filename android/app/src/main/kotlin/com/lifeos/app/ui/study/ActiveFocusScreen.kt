package com.lifeos.app.ui.study

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.lifeos.app.data.local.entities.FOCUS_DOMAINS
import com.lifeos.app.study.PomodoroEngine
import com.lifeos.app.ui.haptics.rememberLifeOsHaptics
import com.lifeos.app.ui.components.LifeOSBadge
import com.lifeos.app.ui.components.PrimaryButton
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.Spacing
import com.lifeos.app.ui.theme.monoFamily
import kotlinx.coroutines.delay

/**
 * A mode, not a page (spec §14): no header, no bottom nav (auto-hidden by
 * the nav host for any non-top-level route), nothing but the timer and the
 * two or three actions that matter while it's running. Stopwatch shows
 * elapsed time; Countdown counts down against its planned length; Pomodoro
 * shows the current phase, its own countdown, and where in the cycle this
 * session is — three different displays sharing one calm layout.
 */
@Composable
fun ActiveFocusScreen(viewModel: StudyViewModel, onFinished: () -> Unit) {
    val state by viewModel.overviewState.collectAsState()
    val session = state.activeSession
    val colors = LocalLifeOSColors.current
    val haptics = rememberLifeOsHaptics()

    // overviewState is a fresh StateFlow every time this screen is navigated
    // to (a new back-stack entry means a new StudyViewModel), so its very
    // first emission is the cold default (activeSession = null) — arriving
    // before Room's real query resolves, not because the session actually
    // ended. Treating that first null as "finished" bounced straight back
    // to Focus, which immediately redirected here again: an infinite loop
    // that never showed a timer. Only a null AFTER a real session was seen
    // means it actually finished.
    var sawSession by remember { mutableStateOf(false) }
    LaunchedEffect(session) {
        if (session != null) sawSession = true
        if (session == null && sawSession) onFinished()
    }
    if (session == null) return

    var durationSeconds by remember { mutableLongStateOf(0L) }
    var pomodoro by remember { mutableStateOf(PomodoroEngine.currentState(session, System.currentTimeMillis())) }
    var showCancelConfirm by remember { mutableStateOf(false) }

    LaunchedEffect(session.id, session.status, session.currentPhase, session.currentPhaseStartedAtEpochMs) {
        while (true) {
            durationSeconds = viewModel.currentDuration(session.id)
            if (session.mode == "pomodoro" && session.status == "active") {
                val next = PomodoroEngine.currentState(session, System.currentTimeMillis())
                pomodoro = next
                if (next.phaseJustCompleted) {
                    viewModel.advancePomodoroPhase(session)
                    break // this session object is now stale; the outer LaunchedEffect key change picks up the new phase
                }
            }
            delay(1000)
        }
    }

    Column(
        modifier = Modifier.fillMaxSize().padding(Spacing.xl2),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        val domainLabel = FOCUS_DOMAINS.firstOrNull { it.first == session.domain }?.second ?: "Focus"
        LifeOSBadge(text = domainLabel.uppercase(), color = colors.accent, backgroundColor = colors.accentSoft, modifier = Modifier.padding(bottom = Spacing.sm))
        // Skip the plain-text title when it's just repeating the domain
        // badge above it — only worth its own line when there's a real
        // course/project/book name to show (spec's own examples always
        // have one: "MATHEMATICS", "CONNECFY").
        if (session.courseName != null || session.projectName != null || session.bookName != null) {
            Text(session.focusTitle, style = MaterialTheme.typography.labelMedium, color = colors.textMuted)
        }

        when (session.mode) {
            "countdown" -> {
                val planned = (session.plannedDurationSeconds ?: 0).toLong()
                val remaining = (planned - durationSeconds).coerceAtLeast(0)
                Text(
                    formatClock(remaining),
                    style = MaterialTheme.typography.displayLarge.copy(fontFamily = monoFamily, fontWeight = FontWeight.SemiBold),
                    color = colors.textPrimary, modifier = Modifier.padding(vertical = Spacing.lg),
                )
                if (planned > 0) {
                    LinearProgressIndicator(
                        progress = { (durationSeconds.toFloat() / planned.toFloat()).coerceIn(0f, 1f) },
                        modifier = Modifier.width(160.dp).padding(bottom = Spacing.md),
                        color = colors.accent, trackColor = colors.surfaceSecondary,
                    )
                }
                Text(
                    session.focusSubtitle + if (session.status == "paused") " · Paused" else if (remaining == 0L) " · Time's up" else "",
                    style = MaterialTheme.typography.bodyMedium, color = colors.textSecondary, modifier = Modifier.padding(bottom = Spacing.xl3),
                )
            }
            "pomodoro" -> {
                Text(
                    PomodoroEngine.phaseLabel(pomodoro.phase),
                    style = MaterialTheme.typography.labelLarge, color = if (pomodoro.phase == "focus") colors.accent else colors.success,
                    modifier = Modifier.padding(top = Spacing.xs),
                )
                Text(
                    formatClock(pomodoro.remainingSeconds),
                    style = MaterialTheme.typography.displayLarge.copy(fontFamily = monoFamily, fontWeight = FontWeight.SemiBold),
                    color = colors.textPrimary, modifier = Modifier.padding(vertical = Spacing.lg),
                )
                Text(
                    "Cycle ${pomodoro.cycleNumber} of ${pomodoro.totalCycles}" + if (session.status == "paused") " · Paused" else "",
                    style = MaterialTheme.typography.bodyMedium, color = colors.textSecondary, modifier = Modifier.padding(bottom = Spacing.sm),
                )
                Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(bottom = Spacing.xl2)) {
                    repeat(pomodoro.totalCycles) { index ->
                        val filled = index < pomodoro.cycleNumber - 1
                        Box(modifier = Modifier.size(8.dp).clip(CircleShape).background(if (filled) colors.accent else colors.surfaceSecondary))
                    }
                }
            }
            else -> {
                Text(
                    formatClock(durationSeconds),
                    style = MaterialTheme.typography.displayLarge.copy(fontFamily = monoFamily, fontWeight = FontWeight.SemiBold),
                    color = colors.textPrimary, modifier = Modifier.padding(vertical = Spacing.lg),
                )
                Text(
                    session.focusSubtitle + if (session.status == "paused") " · Paused" else "",
                    style = MaterialTheme.typography.bodyMedium, color = colors.textSecondary, modifier = Modifier.padding(bottom = Spacing.xl3),
                )
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.lg)) {
            OutlinedButton(onClick = {
                haptics.tick()
                if (session.status == "paused") viewModel.resume(session.id) else viewModel.pause(session.id)
            }, modifier = Modifier.width(120.dp)) {
                Text(if (session.status == "paused") "Resume" else "Pause")
            }
            PrimaryButton(text = "Finish", onClick = { haptics.tick(); viewModel.finish(session.id) }, modifier = Modifier.width(120.dp))
        }

        TextButton(onClick = { showCancelConfirm = true }, modifier = Modifier.padding(top = Spacing.lg)) {
            Text("Cancel session", color = colors.textMuted)
        }

        if (showCancelConfirm) {
            AlertDialog(
                onDismissRequest = { showCancelConfirm = false },
                title = { Text("Cancel this session?") },
                text = { Text("It will be marked cancelled, not deleted.") },
                confirmButton = {
                    TextButton(onClick = { viewModel.cancel(session.id); showCancelConfirm = false }) { Text("Cancel Session") }
                },
                dismissButton = { TextButton(onClick = { showCancelConfirm = false }) { Text("Keep Going") } },
            )
        }
    }
}

private fun formatClock(totalSeconds: Long): String {
    val h = totalSeconds / 3600
    val m = (totalSeconds % 3600) / 60
    val s = totalSeconds % 60
    return if (h > 0) "%d:%02d:%02d".format(h, m, s) else "%02d:%02d".format(m, s)
}
