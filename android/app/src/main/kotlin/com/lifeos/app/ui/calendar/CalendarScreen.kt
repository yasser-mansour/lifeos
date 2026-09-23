package com.lifeos.app.ui.calendar

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.CalendarMonth
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
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

private val ROW_FORMAT = DateTimeFormatter.ofPattern("EEE, MMM d · HH:mm")

@Composable
fun CalendarScreen(viewModel: CalendarViewModel, onAddEvent: () -> Unit) {
    val events by viewModel.upcomingEvents.collectAsState()
    val colors = LocalLifeOSColors.current

    Scaffold(
        containerColor = colors.bgPrimary,
        floatingActionButton = {
            FloatingActionButton(onClick = onAddEvent, containerColor = colors.accent) {
                Icon(Icons.Filled.Add, contentDescription = "New Event", tint = Color.White)
            }
        },
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(horizontal = Spacing.xl)) {
            ScreenHeader("Calendar")
            if (events.isEmpty()) {
                EmptyState(icon = Icons.Filled.CalendarMonth, title = "Nothing scheduled", body = "Tasks, events and deadlines will show up here.")
            } else {
                LazyColumn(modifier = Modifier.fillMaxSize()) {
                    items(events, key = { it.id }) { event ->
                        val start = Instant.ofEpochMilli(event.startEpochMs).atZone(ZoneId.systemDefault())
                        LifeOSListRow(title = event.title, subtitle = ROW_FORMAT.format(start))
                    }
                }
            }
        }
    }
}
