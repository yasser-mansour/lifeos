package com.lifeos.app.ui.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.selection.selectable
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import com.lifeos.app.data.prefs.DeviceStore
import com.lifeos.app.ui.components.LifeOSListRow
import com.lifeos.app.ui.components.ScreenHeader
import com.lifeos.app.ui.components.SectionLabel
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.Spacing
import kotlinx.coroutines.launch

private val THEME_OPTIONS = listOf("system" to "System", "light" to "Light", "dark" to "Dark")

/**
 * Organized into named sections (spec §18) rather than one long page — only
 * the sections with something real behind them: no "Security" section is
 * shown, because there is no app-lock/biometric feature on Android to
 * configure yet (a real gap, not a UI omission — see the rebuild report).
 * A settings section with toggles that do nothing would be worse than not
 * having the section at all.
 */
@Composable
fun SettingsScreen(deviceStore: DeviceStore, onDevices: () -> Unit) {
    val colors = LocalLifeOSColors.current
    val scope = rememberCoroutineScope()
    val currentTheme by deviceStore.themeFlow.collectAsState(initial = "system")
    val hapticsEnabled by deviceStore.hapticsEnabledFlow.collectAsState(initial = true)

    LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = Spacing.xl)) {
        item {
            ScreenHeader("Settings")

            SectionLabel("General")
            Row(
                modifier = Modifier.fillMaxWidth().padding(vertical = Spacing.sm),
                horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text("Haptics", color = colors.textPrimary, style = MaterialTheme.typography.bodyLarge)
                    Text(
                        "A light tap for focus actions, completed tasks, and saved transactions.",
                        color = colors.textMuted, style = MaterialTheme.typography.bodySmall,
                    )
                }
                Switch(
                    checked = hapticsEnabled, onCheckedChange = { scope.launch { deviceStore.setHapticsEnabled(it) } },
                    colors = SwitchDefaults.colors(checkedTrackColor = colors.accent, checkedThumbColor = Color.White),
                )
            }

            SectionLabel("Appearance", modifier = Modifier.padding(top = Spacing.xl2))
            THEME_OPTIONS.forEach { (value, label) ->
                Row(
                    modifier = Modifier.fillMaxWidth().selectable(selected = currentTheme == value) {
                        scope.launch { deviceStore.setTheme(value) }
                    }.padding(vertical = Spacing.sm),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    RadioButton(selected = currentTheme == value, onClick = null)
                    Text(label, color = colors.textPrimary, modifier = Modifier.padding(start = Spacing.sm))
                }
            }

            SectionLabel("Devices & Sync", modifier = Modifier.padding(top = Spacing.xl2))
            LifeOSListRow(title = "Manage devices & sync", subtitle = "Pairing, connection, and sync status", onClick = onDevices)

            SectionLabel("About", modifier = Modifier.padding(top = Spacing.xl2, bottom = Spacing.xs))
            Text("LIFEOS for Android", color = colors.textPrimary)
            Text("Version 0.1.0", color = colors.textMuted, style = MaterialTheme.typography.bodySmall)
            Text(
                "Backups run on your Mac — Android always mirrors what's already backed up there, nothing extra to manage on this device.",
                color = colors.textMuted, style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(top = Spacing.sm, bottom = Spacing.xl3),
            )
        }
    }
}
