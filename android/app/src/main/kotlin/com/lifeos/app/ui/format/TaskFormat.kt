package com.lifeos.app.ui.format

import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter

private val MONTH_DAY: DateTimeFormatter = DateTimeFormatter.ofPattern("MMM d")

/**
 * "Due today" / "Overdue" / "Due Aug 30" phrasing shared by every screen that
 * shows a task's due date (Home's NEXT list, Tasks' Next/Today/Upcoming rows)
 * — one copy so the wording can never drift between them. Previously lived
 * as a private copy inside HomeScreen.kt; pulled out here the same way
 * ui/format/Money.kt was, the moment a second screen needed it.
 */
fun dueDatePhrase(dueDateEpochDay: Long?): String? = dueDateEpochDay?.let {
    val due = LocalDate.ofEpochDay(it)
    val today = LocalDate.now()
    when {
        due.isBefore(today) -> "Overdue"
        due == today -> "Due today"
        due == today.plusDays(1) -> "Due tomorrow"
        else -> "Due ${due.format(MONTH_DAY)}"
    }
}

/** "Northstar · Due today" style row subtitle — context first, due phrase second. */
fun taskSubtitle(context: String?, dueDateEpochDay: Long?): String? =
    listOfNotNull(context, dueDatePhrase(dueDateEpochDay)).joinToString(" · ").ifBlank { null }

/** For the Waiting view — follow-up date framed the same way a due date is. */
fun followUpPhrase(followUpDateEpochDay: Long?): String {
    if (followUpDateEpochDay == null) return "No follow-up date set"
    val date = LocalDate.ofEpochDay(followUpDateEpochDay)
    val today = LocalDate.now()
    return when {
        date.isBefore(today) -> "Follow up overdue · ${date.format(MONTH_DAY)}"
        date == today -> "Follow up today"
        date == today.plusDays(1) -> "Follow up tomorrow"
        else -> "Follow up ${date.format(MONTH_DAY)}"
    }
}

/** For the Completed view — when a task was finished, in the same relative style. */
fun completedPhrase(completedAtEpochMs: Long?): String {
    if (completedAtEpochMs == null) return "Completed"
    val date = Instant.ofEpochMilli(completedAtEpochMs).atZone(ZoneId.systemDefault()).toLocalDate()
    val today = LocalDate.now()
    return when {
        date == today -> "Completed today"
        date == today.minusDays(1) -> "Completed yesterday"
        else -> "Completed ${date.format(MONTH_DAY)}"
    }
}
