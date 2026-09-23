package com.lifeos.app.ui.devices

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import com.lifeos.app.ui.components.PrimaryButton
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.Spacing

/** Fallback pairing entry point for when the camera can't scan the QR code
 * shown on Settings → Devices → Pair New Device on the Mac — that same page
 * also prints the host/port/code as plain text for exactly this screen. */
@Composable
fun ManualPairScreen(viewModel: DevicesViewModel, onPaired: () -> Unit) {
    val colors = LocalLifeOSColors.current
    val pairingState by viewModel.pairingState.collectAsState()
    val screenState by viewModel.screenState.collectAsState()

    var host by remember { mutableStateOf("") }
    var port by remember { mutableStateOf("8420") }
    var code by remember { mutableStateOf("") }

    if (pairingState is PairingUiState.Success) {
        PairingSuccessScreen(macName = screenState.macName, onContinue = onPaired)
        return
    }

    Column(modifier = Modifier.fillMaxSize().padding(Spacing.xl2)) {
        Text(
            "Enter Pairing Details", style = MaterialTheme.typography.headlineMedium, color = colors.textPrimary,
            fontWeight = FontWeight.SemiBold, modifier = Modifier.padding(bottom = Spacing.sm),
        )
        Text(
            "On your Mac: Settings → Devices → Pair New Device → \"Can't scan? Enter these manually\".",
            style = MaterialTheme.typography.bodyMedium, color = colors.textSecondary, modifier = Modifier.padding(bottom = Spacing.xl),
        )

        OutlinedTextField(value = host, onValueChange = { host = it }, label = { Text("Host / IP address") }, singleLine = true, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(value = port, onValueChange = { port = it }, label = { Text("Port") }, singleLine = true, modifier = Modifier.fillMaxWidth().padding(top = Spacing.md))
        OutlinedTextField(value = code, onValueChange = { code = it }, label = { Text("Code") }, singleLine = true, modifier = Modifier.fillMaxWidth().padding(top = Spacing.md))

        when (val state = pairingState) {
            is PairingUiState.Error -> Text(state.message, color = colors.danger, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(top = Spacing.md))
            is PairingUiState.Pairing -> Row(modifier = Modifier.padding(top = Spacing.lg), verticalAlignment = Alignment.CenterVertically) {
                CircularProgressIndicator(color = colors.accent)
                Text("  Checking and pairing…", color = colors.textSecondary, modifier = Modifier.padding(start = Spacing.sm))
            }
            else -> {}
        }

        PrimaryButton(
            text = "Connect",
            onClick = { viewModel.onManualPairSubmitted(host, port, code) },
            enabled = pairingState !is PairingUiState.Pairing,
            modifier = Modifier.fillMaxWidth().padding(top = Spacing.xl2),
        )
    }
}
