package com.lifeos.app.ui.haptics

import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import com.lifeos.app.LifeOSApplication

/**
 * One tick, one call site each — spec §60: "subtle... Do not overuse." A
 * single feedback type kept deliberately for every use rather than a
 * different vibration pattern per action, so this stays a small confirming
 * pulse (focus start/pause/finish, task completed, transaction saved)
 * instead of the app developing its own vocabulary of buzzes to learn.
 * Respects the user's own toggle (Settings -> General) — see DeviceStore.
 */
class LifeOsHaptics(private val enabled: Boolean, private val delegate: androidx.compose.ui.hapticfeedback.HapticFeedback) {
    fun tick() {
        if (enabled) delegate.performHapticFeedback(HapticFeedbackType.LongPress)
    }
}

@Composable
fun rememberLifeOsHaptics(): LifeOsHaptics {
    val app = LocalContext.current.applicationContext as LifeOSApplication
    val enabled by app.deviceStore.hapticsEnabledFlow.collectAsState(initial = true)
    val delegate = LocalHapticFeedback.current
    return LifeOsHaptics(enabled, delegate)
}
