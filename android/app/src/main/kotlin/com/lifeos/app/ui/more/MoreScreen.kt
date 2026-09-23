package com.lifeos.app.ui.more

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Book
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Devices
import androidx.compose.material.icons.filled.Flag
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.People
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.lifeos.app.ui.components.LifeOSListRow
import com.lifeos.app.ui.components.ScreenHeader
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.Spacing

@Composable
fun MoreScreen(
    onProjects: () -> Unit,
    onPeople: () -> Unit,
    onGoals: () -> Unit,
    onCalendar: () -> Unit,
    onNotes: () -> Unit,
    onJournal: () -> Unit,
    onDevices: () -> Unit,
    onSettings: () -> Unit,
) {
    val colors = LocalLifeOSColors.current
    Column(modifier = Modifier.fillMaxSize().padding(horizontal = Spacing.xl)) {
        ScreenHeader("More")
        LifeOSListRow(title = "Projects", leading = { Icon(Icons.Filled.Folder, null, tint = colors.textSecondary) }, onClick = onProjects)
        LifeOSListRow(title = "People & Organizations", leading = { Icon(Icons.Filled.People, null, tint = colors.textSecondary) }, onClick = onPeople)
        LifeOSListRow(title = "Goals", leading = { Icon(Icons.Filled.Flag, null, tint = colors.textSecondary) }, onClick = onGoals)
        LifeOSListRow(title = "Calendar", leading = { Icon(Icons.Filled.CalendarMonth, null, tint = colors.textSecondary) }, onClick = onCalendar)
        LifeOSListRow(title = "Notes", leading = { Icon(Icons.Filled.Description, null, tint = colors.textSecondary) }, onClick = onNotes)
        LifeOSListRow(title = "Journal", leading = { Icon(Icons.Filled.Book, null, tint = colors.textSecondary) }, onClick = onJournal)
        LifeOSListRow(title = "Devices", leading = { Icon(Icons.Filled.Devices, null, tint = colors.textSecondary) }, onClick = onDevices)
        LifeOSListRow(title = "Settings", leading = { Icon(Icons.Filled.Settings, null, tint = colors.textSecondary) }, onClick = onSettings)
    }
}
