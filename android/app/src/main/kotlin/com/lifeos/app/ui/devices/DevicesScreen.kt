package com.lifeos.app.ui.devices

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import com.lifeos.app.ui.components.PrimaryButton
import com.lifeos.app.ui.components.ScreenHeader
import com.lifeos.app.ui.components.StatRow
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.Spacing

@Composable
fun DevicesScreen(viewModel: DevicesViewModel, onPairNewDevice: () -> Unit, onDiagnostics: () -> Unit) {
    val state by viewModel.screenState.collectAsState()
    val colors = LocalLifeOSColors.current

    LaunchedEffect(Unit) { viewModel.refreshConnection() }

    Column(modifier = Modifier.fillMaxSize().padding(Spacing.xl)) {
        ScreenHeader("Devices")

        if (!state.isPaired) {
            Text("Not paired yet.", color = colors.textPrimary, style = MaterialTheme.typography.bodyLarge)
            Text(
                "LIFEOS keeps working offline — pairing lets it sync with your Mac.",
                color = colors.textMuted, style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(top = Spacing.xs, bottom = Spacing.xl),
            )
            PrimaryButton(text = "Pair with Mac", onClick = onPairNewDevice)
            return@Column
        }

        Text(state.macName, style = MaterialTheme.typography.titleLarge, color = colors.textPrimary)
        Text("Paired", color = colors.success, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(bottom = Spacing.lg))

        when (state.connection) {
            is ConnectionState.Unreachable -> {
                // Wording matters here (spec §49): this is not an app error,
                // and nothing about the phone's own data is at risk.
                Text("Mac unavailable", style = MaterialTheme.typography.titleMedium, color = colors.warning)
                Text(
                    "Your Android data remains available. Changes will sync when the Mac returns.",
                    color = colors.textSecondary, style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.padding(top = Spacing.xs, bottom = Spacing.xl),
                )
            }
            else -> {
                Column(modifier = Modifier.fillMaxWidth().padding(bottom = Spacing.xl)) {
                    StatRow(
                        "Connection",
                        if (state.connection is ConnectionState.Online) "Online" else "Checking…",
                        valueColor = if (state.connection is ConnectionState.Online) colors.success else colors.textMuted,
                    )
                    StatRow("Last sync", relativeTime(state.lastSyncAtEpochMs))
                    StatRow(
                        "Pending", if (state.pendingCount > 0) "${state.pendingCount}" else "0",
                        valueColor = if (state.pendingCount > 0) colors.warning else null,
                    )
                    state.lastSyncError?.let {
                        StatRow("Last error", it, valueColor = colors.danger)
                    }
                }
            }
        }

        PrimaryButton(text = "Sync now", onClick = viewModel::syncNow, modifier = Modifier.fillMaxWidth().padding(bottom = Spacing.md))
        TextButton(onClick = onDiagnostics) { Text("Diagnostics") }
        TextButton(onClick = viewModel::unpair, modifier = Modifier.padding(top = Spacing.xl)) {
            Text("Unpair", color = colors.danger)
        }
    }
}

private fun relativeTime(epochMs: Long?): String {
    if (epochMs == null) return "Never"
    val minutes = (System.currentTimeMillis() - epochMs) / 60000
    return when {
        minutes < 1 -> "Just now"
        minutes < 60 -> "$minutes min ago"
        minutes < 24 * 60 -> "${minutes / 60}h ago"
        else -> "${minutes / (24 * 60)}d ago"
    }
}
