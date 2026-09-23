package com.lifeos.app.ui.journal

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import com.lifeos.app.ui.theme.Spacing
import kotlinx.coroutines.delay

@Composable
fun JournalEditorScreen(viewModel: JournalViewModel, entryId: String) {
    val entries by viewModel.entries.collectAsState()
    val entry = entries.find { it.id == entryId } ?: return

    var title by remember(entryId) { mutableStateOf(entry.title) }
    var body by remember(entryId) { mutableStateOf(entry.body) }

    // Debounced autosave — matches the desktop editor's "Saved" / "Saving…"
    // behavior described in spec §83, minus the visible status label here
    // since the sync queue already surfaces pending state on Devices.
    LaunchedEffect(title, body) {
        delay(800)
        viewModel.save(entry, title, body, entry.mood)
    }

    Column(modifier = Modifier.fillMaxSize().padding(Spacing.xl)) {
        TextField(
            value = title, onValueChange = { title = it },
            placeholder = { Text("Untitled") },
            textStyle = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.SemiBold),
            colors = TextFieldDefaults.colors(unfocusedContainerColor = Color.Transparent, focusedContainerColor = Color.Transparent, unfocusedIndicatorColor = Color.Transparent, focusedIndicatorColor = Color.Transparent),
            modifier = Modifier.fillMaxWidth(),
        )
        TextField(
            value = body, onValueChange = { body = it },
            placeholder = { Text("Start writing…") },
            textStyle = MaterialTheme.typography.bodyLarge,
            colors = TextFieldDefaults.colors(unfocusedContainerColor = Color.Transparent, focusedContainerColor = Color.Transparent, unfocusedIndicatorColor = Color.Transparent, focusedIndicatorColor = Color.Transparent),
            modifier = Modifier.fillMaxSize(),
        )
    }
}
