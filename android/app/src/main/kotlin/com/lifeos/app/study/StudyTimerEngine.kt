package com.lifeos.app.study

/**
 * Kotlin twin of backend/apps/study/engine.py. Same contract: replay
 * (eventType, timestamp) pairs into an elapsed-focus duration, never trust
 * an incrementing counter. This is what lets the Android timer survive
 * process death, screen-off, and app backgrounding (spec §53/§56) — on
 * reopen we just re-run this function over the events already in Room.
 */

private val RUNNING_EVENTS = setOf("start", "resume")
private val STOPPING_EVENTS = setOf("pause", "finish", "cancel")

data class TimedEvent(val eventType: String, val timestampEpochMs: Long)

object StudyTimerEngine {

    fun computeDurationSeconds(events: List<TimedEvent>, asOfEpochMs: Long): Long {
        var totalMs = 0L
        var runningSinceMs: Long? = null

        for (event in events.sortedBy { it.timestampEpochMs }) {
            when (event.eventType) {
                in RUNNING_EVENTS -> if (runningSinceMs == null) runningSinceMs = event.timestampEpochMs
                in STOPPING_EVENTS -> {
                    if (runningSinceMs != null) {
                        totalMs += event.timestampEpochMs - runningSinceMs
                        runningSinceMs = null
                    }
                }
                // "correction" carries no timing weight of its own.
            }
        }

        if (runningSinceMs != null) {
            totalMs += asOfEpochMs - runningSinceMs
        }

        return maxOf(0L, totalMs / 1000)
    }

    fun isCurrentlyRunning(events: List<TimedEvent>): Boolean {
        var running = false
        for (event in events.sortedBy { it.timestampEpochMs }) {
            when (event.eventType) {
                in RUNNING_EVENTS -> running = true
                in STOPPING_EVENTS -> running = false
            }
        }
        return running
    }
}
