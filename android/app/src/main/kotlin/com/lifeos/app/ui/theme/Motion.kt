package com.lifeos.app.ui.theme

import androidx.compose.animation.core.tween
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext
import android.provider.Settings

/**
 * Restrained motion, matching desktop's --motion-* tokens: named durations,
 * nothing bouncy/springy. LIFEOS is a life-management tool, not a game —
 * motion should explain a change, never decorate one.
 */
object Motion {
    const val MICRO_MS = 120   // a toggle, a chip selection
    const val PANEL_MS = 220   // a bottom sheet, a dialog
    const val PAGE_MS = 260    // a navigation transition

    fun <T> micro() = tween<T>(MICRO_MS)
    fun <T> panel() = tween<T>(PANEL_MS)
    fun <T> page() = tween<T>(PAGE_MS)
}

/** Mirrors the desktop prefers-reduced-motion collapse — reads the system
 * "Remove animations" accessibility setting so motion can be skipped the
 * same way it is on the web build. */
@Composable
fun reducedMotionEnabled(): Boolean {
    val context = LocalContext.current
    return try {
        Settings.Global.getFloat(context.contentResolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f) == 0f
    } catch (e: Exception) {
        false
    }
}
