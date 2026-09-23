package com.lifeos.app.ui.notes

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Description
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import com.lifeos.app.ui.components.EmptyState
import com.lifeos.app.ui.components.LifeOSListRow
import com.lifeos.app.ui.components.ScreenHeader
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.Spacing

@Composable
fun NotesScreen(viewModel: NotesViewModel, onOpenNote: (String) -> Unit) {
    val notes by viewModel.notes.collectAsState()
    val colors = LocalLifeOSColors.current

    Scaffold(
        containerColor = colors.bgPrimary,
        floatingActionButton = {
            FloatingActionButton(onClick = { viewModel.createNote(onCreated = onOpenNote) }, containerColor = colors.accent) {
                Icon(Icons.Filled.Add, contentDescription = "New Note", tint = Color.White)
            }
        },
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(horizontal = Spacing.xl)) {
            ScreenHeader("Notes")
            if (notes.isEmpty()) {
                EmptyState(icon = Icons.Filled.Description, title = "No notes yet", body = "Quick thoughts, linked to what they're about.")
            } else {
                LazyColumn(modifier = Modifier.fillMaxSize()) {
                    items(notes, key = { it.id }) { note ->
                        LifeOSListRow(
                            title = note.title.ifBlank { "Untitled" },
                            subtitle = note.content.take(60).ifBlank { null },
                            onClick = { onOpenNote(note.id) },
                        )
                    }
                }
            }
        }
    }
}
