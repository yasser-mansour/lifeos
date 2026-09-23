package com.lifeos.app.study

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Mirrors backend apps/study/tests.py::TimerEngineTests — same scenarios,
 * same expected outputs, proving the two engines agree. */
class StudyTimerEngineTest {

    private val base = 1_700_000_000_000L // arbitrary fixed epoch ms

    private fun t(offsetSeconds: Long) = base + offsetSeconds * 1000

    @Test
    fun `zero second session`() {
        val events = listOf(TimedEvent("start", t(0)), TimedEvent("finish", t(0)))
        assertEquals(0L, StudyTimerEngine.computeDurationSeconds(events, t(0)))
    }

    @Test
    fun `one second session`() {
        val events = listOf(TimedEvent("start", t(0)), TimedEvent("finish", t(1)))
        assertEquals(1L, StudyTimerEngine.computeDurationSeconds(events, t(1)))
    }

    @Test
    fun `one hour session`() {
        val events = listOf(TimedEvent("start", t(0)), TimedEvent("finish", t(3600)))
        assertEquals(3600L, StudyTimerEngine.computeDurationSeconds(events, t(3600)))
    }

    @Test
    fun `single pause excludes paused time`() {
        val events = listOf(
            TimedEvent("start", t(0)), TimedEvent("pause", t(60)),
            TimedEvent("resume", t(600)), TimedEvent("finish", t(660)),
        )
        assertEquals(120L, StudyTimerEngine.computeDurationSeconds(events, t(660)))
    }

    @Test
    fun `multiple pauses`() {
        val events = listOf(
            TimedEvent("start", t(0)), TimedEvent("pause", t(100)),
            TimedEvent("resume", t(200)), TimedEvent("pause", t(250)),
            TimedEvent("resume", t(300)), TimedEvent("finish", t(320)),
        )
        assertEquals(170L, StudyTimerEngine.computeDurationSeconds(events, t(320)))
    }

    @Test
    fun `in-progress session counts up to as-of`() {
        val events = listOf(TimedEvent("start", t(0)))
        assertEquals(45L, StudyTimerEngine.computeDurationSeconds(events, t(45)))
    }

    @Test
    fun `paused session freezes regardless of as-of`() {
        val events = listOf(TimedEvent("start", t(0)), TimedEvent("pause", t(30)))
        assertEquals(30L, StudyTimerEngine.computeDurationSeconds(events, t(9999)))
    }

    @Test
    fun `cancelled session stops accumulating`() {
        val events = listOf(TimedEvent("start", t(0)), TimedEvent("cancel", t(15)))
        assertEquals(15L, StudyTimerEngine.computeDurationSeconds(events, t(500)))
    }

    @Test
    fun `is currently running reflects last event`() {
        assertTrue(StudyTimerEngine.isCurrentlyRunning(listOf(TimedEvent("start", t(0)))))
        assertFalse(StudyTimerEngine.isCurrentlyRunning(listOf(TimedEvent("start", t(0)), TimedEvent("pause", t(10)))))
        assertTrue(
            StudyTimerEngine.isCurrentlyRunning(
                listOf(TimedEvent("start", t(0)), TimedEvent("pause", t(10)), TimedEvent("resume", t(20)))
            )
        )
        assertFalse(StudyTimerEngine.isCurrentlyRunning(listOf(TimedEvent("start", t(0)), TimedEvent("finish", t(10)))))
    }

    @Test
    fun `survives out-of-order event insertion by sorting on timestamp`() {
        val events = listOf(TimedEvent("finish", t(60)), TimedEvent("start", t(0)))
        assertEquals(60L, StudyTimerEngine.computeDurationSeconds(events, t(60)))
    }
}
