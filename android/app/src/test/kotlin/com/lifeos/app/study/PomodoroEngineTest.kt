package com.lifeos.app.study

import com.lifeos.app.data.local.entities.StudySessionEntity
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PomodoroEngineTest {

    private val base = 1_700_000_000_000L
    private fun t(offsetSeconds: Long) = base + offsetSeconds * 1000

    private fun session(
        phase: String = "focus", completedCycles: Int = 0, phaseStartedAt: Long = base,
        focusSeconds: Int = 1500, shortBreakSeconds: Int = 300, longBreakSeconds: Int = 900, cyclesBeforeLong: Int = 4,
    ) = StudySessionEntity(
        id = "s1", domain = "school", courseId = null, courseName = null, topicId = null, topicName = null,
        taskId = null, projectId = null, projectName = null, bookId = null, bookName = null,
        mode = "pomodoro", status = "active", plannedDurationSeconds = null,
        pomodoroFocusSeconds = focusSeconds, pomodoroShortBreakSeconds = shortBreakSeconds,
        pomodoroLongBreakSeconds = longBreakSeconds, pomodoroCyclesBeforeLongBreak = cyclesBeforeLong,
        currentPhase = phase, completedFocusCycles = completedCycles, currentPhaseStartedAtEpochMs = phaseStartedAt,
        startedAtEpochMs = base, endedAtEpochMs = null, originDeviceName = null,
        correctedDurationSeconds = null, correctionReason = null, notes = "",
        updatedAtEpochMs = base, version = 1, syncStatus = "synced",
    )

    @Test
    fun `counts down within the current focus phase`() {
        val state = PomodoroEngine.currentState(session(focusSeconds = 1500), t(100))
        assertEquals("focus", state.phase)
        assertEquals(1400L, state.remainingSeconds)
        assertFalse(state.phaseJustCompleted)
    }

    @Test
    fun `flags phase complete once elapsed reaches the phase duration`() {
        val state = PomodoroEngine.currentState(session(focusSeconds = 1500), t(1500))
        assertEquals(0L, state.remainingSeconds)
        assertTrue(state.phaseJustCompleted)
    }

    @Test
    fun `never reports negative remaining time`() {
        val state = PomodoroEngine.currentState(session(focusSeconds = 1500), t(9999))
        assertEquals(0L, state.remainingSeconds)
    }

    @Test
    fun `focus advances to a short break before the long-break cycle`() {
        val next = PomodoroEngine.advance(session(phase = "focus", completedCycles = 0, cyclesBeforeLong = 4), t(1500))
        assertEquals("short_break", next.currentPhase)
        assertEquals(1, next.completedFocusCycles)
    }

    @Test
    fun `every Nth completed focus cycle gets a long break instead`() {
        val next = PomodoroEngine.advance(session(phase = "focus", completedCycles = 3, cyclesBeforeLong = 4), t(1500))
        assertEquals("long_break", next.currentPhase)
        assertEquals(4, next.completedFocusCycles)
    }

    @Test
    fun `a break always advances back to focus`() {
        val fromShort = PomodoroEngine.advance(session(phase = "short_break", completedCycles = 1), t(300))
        assertEquals("focus", fromShort.currentPhase)
        assertEquals(1, fromShort.completedFocusCycles) // a break completing doesn't itself add a cycle

        val fromLong = PomodoroEngine.advance(session(phase = "long_break", completedCycles = 4), t(900))
        assertEquals("focus", fromLong.currentPhase)
    }

    @Test
    fun `advancing resets the phase-start timestamp`() {
        val next = PomodoroEngine.advance(session(phase = "focus", phaseStartedAt = base), t(1500))
        assertEquals(t(1500), next.currentPhaseStartedAtEpochMs)
    }

    @Test
    fun `cycle number shown is one-indexed`() {
        assertEquals(1, PomodoroEngine.currentState(session(completedCycles = 0), t(0)).cycleNumber)
        assertEquals(3, PomodoroEngine.currentState(session(completedCycles = 2), t(0)).cycleNumber)
    }

    @Test
    fun `the break after a cycle's focus block still counts as that same cycle`() {
        // Cycle 1's focus just completed (completedFocusCycles=1) and we're
        // now on its break — this must still read "Cycle 1", not "Cycle 2":
        // the number should only advance once cycle 2's focus block starts.
        val onBreak = PomodoroEngine.currentState(session(phase = "short_break", completedCycles = 1), t(0))
        assertEquals(1, onBreak.cycleNumber)

        val nextFocus = PomodoroEngine.currentState(session(phase = "focus", completedCycles = 1), t(0))
        assertEquals(2, nextFocus.cycleNumber)
    }
}
