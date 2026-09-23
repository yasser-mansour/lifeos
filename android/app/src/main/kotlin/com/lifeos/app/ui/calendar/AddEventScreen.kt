package com.lifeos.app.ui.calendar

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TimePicker
import androidx.compose.material3.rememberDatePickerState
import androidx.compose.material3.rememberTimePickerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import com.lifeos.app.ui.components.PrimaryButton
import com.lifeos.app.ui.components.ScreenHeader
import com.lifeos.app.ui.components.SectionLabel
import com.lifeos.app.ui.components.relationPicker
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.Spacing
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

private val DISPLAY_FORMAT = DateTimeFormatter.ofPattern("EEE, MMM d · HH:mm")

@Composable
fun AddEventScreen(viewModel: CalendarViewModel, onSaved: () -> Unit) {
    val projects by viewModel.projects.collectAsState()
    val people by viewModel.people.collectAsState()
    val courses by viewModel.courses.collectAsState()

    var title by remember { mutableStateOf("") }
    var startEpochMs by remember { mutableStateOf(System.currentTimeMillis()) }
    var showPicker by remember { mutableStateOf(false) }
    var selectedProjectId by remember { mutableStateOf<String?>(null) }
    var selectedPersonId by remember { mutableStateOf<String?>(null) }
    var selectedCourseId by remember { mutableStateOf<String?>(null) }

    LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = Spacing.xl)) {
        item {
            ScreenHeader("New Event")
            OutlinedTextField(
                value = title, onValueChange = { title = it }, placeholder = { Text("Title") },
                singleLine = true, modifier = Modifier.fillMaxWidth(),
            )
            SectionLabel("When", modifier = Modifier.padding(top = Spacing.lg))
            val when_ = Instant.ofEpochMilli(startEpochMs).atZone(ZoneId.systemDefault())
            TextButton(onClick = { showPicker = true }) { Text(DISPLAY_FORMAT.format(when_)) }
        }

        item { SectionLabel("Project (optional)", modifier = Modifier.padding(top = Spacing.lg)) }
        relationPicker(entities = projects, selectedId = selectedProjectId, idOf = { it.id }, labelOf = { it.name }, onSelect = { selectedProjectId = it })
        item { SectionLabel("Person (optional)", modifier = Modifier.padding(top = Spacing.lg)) }
        relationPicker(entities = people, selectedId = selectedPersonId, idOf = { it.id }, labelOf = { it.name }, onSelect = { selectedPersonId = it })
        item { SectionLabel("Course (optional)", modifier = Modifier.padding(top = Spacing.lg)) }
        relationPicker(entities = courses, selectedId = selectedCourseId, idOf = { it.id }, labelOf = { it.name }, onSelect = { selectedCourseId = it })

        item {
            PrimaryButton(
                text = "Save Event",
                onClick = { viewModel.createEvent(title, startEpochMs, "other", selectedProjectId, selectedPersonId, selectedCourseId); onSaved() },
                enabled = title.isNotBlank(),
                modifier = Modifier.fillMaxWidth().padding(top = Spacing.xl2, bottom = Spacing.xl2),
            )
        }
    }

    if (showPicker) {
        DateTimePickerDialog(
            initialEpochMs = startEpochMs,
            onDismiss = { showPicker = false },
            onConfirm = { startEpochMs = it; showPicker = false },
        )
    }
}

/** Two Material3 pickers (date, then time) in one dialog flow — this app has
 * no prior date+time picker to match, so this follows the stock M3 pattern
 * (DatePickerDialog wraps DatePicker; TimePicker needs its own container). */
@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
private fun DateTimePickerDialog(initialEpochMs: Long, onDismiss: () -> Unit, onConfirm: (Long) -> Unit) {
    var pickingTime by remember { mutableStateOf(false) }
    val dateState = rememberDatePickerState(initialSelectedDateMillis = initialEpochMs)
    val initial = Instant.ofEpochMilli(initialEpochMs).atZone(ZoneId.systemDefault())
    val timeState = rememberTimePickerState(initialHour = initial.hour, initialMinute = initial.minute, is24Hour = true)

    if (!pickingTime) {
        DatePickerDialog(
            onDismissRequest = onDismiss,
            confirmButton = { TextButton(onClick = { pickingTime = true }, enabled = dateState.selectedDateMillis != null) { Text("Next") } },
            dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
        ) { androidx.compose.material3.DatePicker(state = dateState) }
    } else {
        Dialog(onDismissRequest = onDismiss) {
            androidx.compose.material3.Surface(shape = MaterialTheme.shapes.large) {
                androidx.compose.foundation.layout.Column(modifier = Modifier.padding(24.dp)) {
                    TimePicker(state = timeState)
                    androidx.compose.foundation.layout.Row(modifier = Modifier.padding(top = 16.dp)) {
                        TextButton(onClick = onDismiss) { Text("Cancel") }
                        TextButton(onClick = {
                            val pickedDateMs = dateState.selectedDateMillis ?: initialEpochMs
                            val pickedDate = Instant.ofEpochMilli(pickedDateMs).atZone(ZoneId.of("UTC")).toLocalDate()
                            val combined = pickedDate.atTime(timeState.hour, timeState.minute).atZone(ZoneId.systemDefault())
                            onConfirm(combined.toInstant().toEpochMilli())
                        }) { Text("Done") }
                    }
                }
            }
        }
    }
}
