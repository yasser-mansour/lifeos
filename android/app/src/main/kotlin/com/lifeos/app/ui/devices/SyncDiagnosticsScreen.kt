package com.lifeos.app.ui.devices

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import com.lifeos.app.ui.components.PrimaryButton
import com.lifeos.app.ui.components.ScreenHeader
import com.lifeos.app.ui.components.SectionLabel
import com.lifeos.app.ui.components.StatRow
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.Spacing

/**
 * Settings → Devices & Sync → Diagnostics (spec §71) — safe technical
 * detail for troubleshooting. Deliberately never shows the device's own
 * bearer token; everything else here is fine to see, since it's local-only
 * and never leaves the phone except in a support conversation the owner
 * starts themselves.
 */
@Composable
fun SyncDiagnosticsScreen(viewModel: DevicesViewModel, onResetPairing: () -> Unit) {
    val state by viewModel.screenState.collectAsState()
    val colors = LocalLifeOSColors.current
    var baseUrl by remember { mutableStateOf<String?>(null) }
    var deviceId by remember { mutableStateOf<String?>(null) }
    var serverHealth by remember { mutableStateOf("Checking…") }

    LaunchedEffect(Unit) {
        baseUrl = viewModel.currentBaseUrl()
        deviceId = viewModel.currentDeviceId()
        serverHealth = if (viewModel.checkServerHealth()) "OK" else "Unreachable"
    }

    Column(modifier = Modifier.fillMaxSize().padding(Spacing.xl)) {
        ScreenHeader("Diagnostics")

        SectionLabel("Connection")
        Column(modifier = Modifier.fillMaxWidth().padding(bottom = Spacing.xl)) {
            StatRow("Mac endpoint", baseUrl ?: "—")
            StatRow("This device", deviceId?.take(8) ?: "—")
            StatRow("Server health", serverHealth, valueColor = if (serverHealth == "OK") colors.success else colors.danger)
        }

        SectionLabel("Sync")
        Column(modifier = Modifier.fillMaxWidth().padding(bottom = Spacing.xl2)) {
            StatRow("Last successful sync", if (state.lastSyncAtEpochMs != null) "Synced" else "Never")
            StatRow("Pending operations", "${state.pendingCount}", valueColor = if (state.pendingCount > 0) colors.warning else null)
            StatRow("Sync conflicts", "Resolve on your Mac if any appear", valueColor = colors.textMuted)
            state.lastSyncError?.let { StatRow("Last error", it, valueColor = colors.danger) }
        }

        PrimaryButton(text = "Test connection", onClick = { viewModel.refreshConnection() }, modifier = Modifier.fillMaxWidth().padding(bottom = Spacing.md))
        androidx.compose.material3.OutlinedButton(onClick = viewModel::syncNow, modifier = Modifier.fillMaxWidth().padding(bottom = Spacing.md)) {
            Text("Sync now")
        }
        TextButton(onClick = onResetPairing) { Text("Re-pair with Mac", color = colors.danger) }

        Text(
            "Your device's own sync credential is never shown here.",
            style = androidx.compose.material3.MaterialTheme.typography.bodySmall, color = colors.textMuted,
            modifier = Modifier.padding(top = Spacing.xl),
        )
    }
}
