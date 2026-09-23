package com.lifeos.app.study

import com.lifeos.app.data.local.entities.StudySessionEntity

data class PomodoroState(
    val phase: String, // focus | short_break | long_break
    val remainingSeconds: Long,
    val cycleNumber: Int,
    val totalCycles: Int,
    val phaseJustCompleted: Boolean,
)

/**
 * A Pomodoro session is a small local state machine layered on top of the
 * same event-sourced timer everything else uses: total duration still comes
 * from StudyTimerEngine (never from this), but "which phase am I in and how
 * long is left in it" needs its own tiny bit of state — see
 * StudySessionEntity.currentPhaseStartedAtEpochMs.
 */
object PomodoroEngine {
    fun phaseDurationSeconds(session: StudySessionEntity, phase: String): Int = when (phase) {
        "short_break" -> session.pomodoroShortBreakSeconds
        "long_break" -> session.pomodoroLongBreakSeconds
        else -> session.pomodoroFocusSeconds
    }

    fun currentState(session: StudySessionEntity, nowEpochMs: Long): PomodoroState {
        val elapsedInPhase = ((nowEpochMs - session.currentPhaseStartedAtEpochMs) / 1000).coerceAtLeast(0)
        val phaseDuration = phaseDurationSeconds(session, session.currentPhase)
        val remaining = phaseDuration - elapsedInPhase
        // A cycle is one focus block plus the break right after it — while
        // on that break, this is still "cycle N", not N+1; the number only
        // advances once the NEXT focus block starts.
        val cycleNumber = if (session.currentPhase == "focus") session.completedFocusCycles + 1 else session.completedFocusCycles
        return PomodoroState(
            phase = session.currentPhase,
            remainingSeconds = remaining.coerceAtLeast(0),
            cycleNumber = cycleNumber.coerceAtLeast(1),
            totalCycles = session.pomodoroCyclesBeforeLongBreak,
            phaseJustCompleted = remaining <= 0,
        )
    }

    /** What the session looks like after its current phase runs out — the
     * next phase, whether a focus cycle was just completed, and the reset
     * phase-start timestamp. Focus always leads to a break; a break always
     * leads back to focus; every Nth completed focus cycle gets the long
     * break instead of the short one. */
    fun advance(session: StudySessionEntity, atEpochMs: Long): StudySessionEntity {
        val wasFocus = session.currentPhase == "focus"
        val newCompletedCycles = if (wasFocus) session.completedFocusCycles + 1 else session.completedFocusCycles
        val nextPhase = when {
            wasFocus && session.pomodoroCyclesBeforeLongBreak > 0 && newCompletedCycles % session.pomodoroCyclesBeforeLongBreak == 0 -> "long_break"
            wasFocus -> "short_break"
            else -> "focus"
        }
        return session.copy(currentPhase = nextPhase, completedFocusCycles = newCompletedCycles, currentPhaseStartedAtEpochMs = atEpochMs)
    }

    fun phaseLabel(phase: String): String = when (phase) {
        "short_break" -> "Short break"
        "long_break" -> "Long break"
        else -> "Focus"
    }
}
