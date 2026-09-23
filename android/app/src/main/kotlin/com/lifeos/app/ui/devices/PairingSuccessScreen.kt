package com.lifeos.app.ui.devices

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.lifeos.app.ui.components.PrimaryButton
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.Spacing

/**
 * Shown after a successful claim, before handing control back to the app
 * (spec §50) — pairing used to jump straight to Devices the instant the
 * network call succeeded, with nothing on screen to say it worked. A
 * one-tap "Continue" (rather than an auto-advancing timer) means the
 * confirmation is never missed even if the phone is put down for a moment.
 */
@Composable
fun PairingSuccessScreen(macName: String, onContinue: () -> Unit) {
    val colors = LocalLifeOSColors.current
    Column(
        modifier = Modifier.fillMaxSize().background(colors.bgPrimary).padding(Spacing.xl2),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Box(
            modifier = Modifier.size(64.dp).clip(CircleShape).background(colors.successSoft),
            contentAlignment = Alignment.Center,
        ) {
            Icon(Icons.Filled.Check, contentDescription = null, tint = colors.success)
        }
        Text(
            "Paired successfully", style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.SemiBold),
            color = colors.textPrimary, modifier = Modifier.padding(top = Spacing.lg, bottom = Spacing.xs),
        )
        Text(macName, style = MaterialTheme.typography.bodyMedium, color = colors.textSecondary, modifier = Modifier.padding(bottom = Spacing.xs))
        // The first sync was just queued (WorkManager, not awaited here), so
        // this says "starting", never "complete" — an honest sync indicator
        // on Devices is what actually reports when it finishes.
        Text("Syncing your data…", style = MaterialTheme.typography.bodyMedium, color = colors.textMuted, modifier = Modifier.padding(bottom = Spacing.xl3))
        PrimaryButton(text = "Continue", onClick = onContinue, modifier = Modifier.fillMaxWidth())
    }
}
