package com.lifeos.app.ui.journal

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Book
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
import java.time.LocalDate
import java.time.format.DateTimeFormatter

private val ROW_DATE_FORMAT = DateTimeFormatter.ofPattern("EEE, MMM d")

@Composable
fun JournalScreen(viewModel: JournalViewModel, onOpenEntry: (String) -> Unit) {
    val entries by viewModel.entries.collectAsState()
    val colors = LocalLifeOSColors.current

    Scaffold(
        containerColor = colors.bgPrimary,
        floatingActionButton = {
            FloatingActionButton(onClick = { viewModel.createEntry(onOpenEntry) }, containerColor = colors.accent) {
                Icon(Icons.Filled.Add, contentDescription = "New Entry", tint = Color.White)
            }
        },
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(horizontal = Spacing.xl)) {
            ScreenHeader("Journal")
            if (entries.isEmpty()) {
                EmptyState(icon = Icons.Filled.Book, title = "No entries yet", body = "A private place to write.")
            } else {
                LazyColumn(modifier = Modifier.fillMaxSize()) {
                    items(entries, key = { it.id }) { entry ->
                        LifeOSListRow(
                            title = entry.title.ifBlank { "Untitled" },
                            subtitle = ROW_DATE_FORMAT.format(LocalDate.ofEpochDay(entry.dateEpochDay)),
                            onClick = { onOpenEntry(entry.id) },
                        )
                    }
                }
            }
        }
    }
}
