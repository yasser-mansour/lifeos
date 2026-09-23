package com.lifeos.app.ui.format

/** "1h 42m" / "24m" — every screen that shows a focus-time total (Home,
 * Focus overview, Project detail's "this week" stat) formats it identically.
 * Previously a private copy duplicated in HomeScreen.kt and
 * StudyOverviewScreen.kt; pulled out here the moment a third screen
 * (Projects) needed the same thing, same reasoning as ui/format/Money.kt. */
fun formatDurationCompact(totalSeconds: Long): String {
    val h = totalSeconds / 3600
    val m = (totalSeconds % 3600) / 60
    return if (h > 0) "${h}h ${m}m" else "${m}m"
}
