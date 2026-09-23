package com.lifeos.app.ui.notes

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
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
import androidx.compose.ui.unit.dp
import com.lifeos.app.ui.components.SectionLabel
import com.lifeos.app.ui.components.relationPicker
import com.lifeos.app.ui.theme.Spacing
import kotlinx.coroutines.delay

@Composable
fun NoteEditorScreen(viewModel: NotesViewModel, noteId: String) {
    val notes by viewModel.notes.collectAsState()
    val note = notes.find { it.id == noteId } ?: return
    val projects by viewModel.projects.collectAsState()
    val tasks by viewModel.tasks.collectAsState()
    val people by viewModel.people.collectAsState()
    val courses by viewModel.courses.collectAsState()
    val goals by viewModel.goals.collectAsState()

    var title by remember(noteId) { mutableStateOf(note.title) }
    var content by remember(noteId) { mutableStateOf(note.content) }
    var projectId by remember(noteId) { mutableStateOf(note.projectId) }
    var taskId by remember(noteId) { mutableStateOf(note.taskId) }
    var personId by remember(noteId) { mutableStateOf(note.personId) }
    var courseId by remember(noteId) { mutableStateOf(note.courseId) }
    var goalId by remember(noteId) { mutableStateOf(note.goalId) }

    // Debounced autosave, same shape as JournalEditorScreen — any field
    // change (text or a relation pick) queues a save 800ms after the user
    // stops touching this screen.
    LaunchedEffect(title, content, projectId, taskId, personId, courseId, goalId) {
        delay(800)
        viewModel.save(note, title, content, projectId, taskId, personId, courseId, goalId)
    }

    LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = Spacing.xl)) {
        item {
            TextField(
                value = title, onValueChange = { title = it },
                placeholder = { Text("Untitled") },
                textStyle = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.SemiBold),
                colors = TextFieldDefaults.colors(unfocusedContainerColor = Color.Transparent, focusedContainerColor = Color.Transparent, unfocusedIndicatorColor = Color.Transparent, focusedIndicatorColor = Color.Transparent),
                modifier = Modifier.fillMaxWidth().padding(top = Spacing.lg),
            )
            TextField(
                value = content, onValueChange = { content = it },
                placeholder = { Text("Write in Markdown…") },
                textStyle = MaterialTheme.typography.bodyLarge,
                colors = TextFieldDefaults.colors(unfocusedContainerColor = Color.Transparent, focusedContainerColor = Color.Transparent, unfocusedIndicatorColor = Color.Transparent, focusedIndicatorColor = Color.Transparent),
                modifier = Modifier.fillMaxWidth().height(200.dp),
            )
            SectionLabel("Project", modifier = Modifier.padding(top = Spacing.md))
        }
        relationPicker(entities = projects, selectedId = projectId, idOf = { it.id }, labelOf = { it.name }, onSelect = { projectId = it })
        item { SectionLabel("Task", modifier = Modifier.padding(top = Spacing.md)) }
        relationPicker(entities = tasks, selectedId = taskId, idOf = { it.id }, labelOf = { it.title }, onSelect = { taskId = it })
        item { SectionLabel("Person", modifier = Modifier.padding(top = Spacing.md)) }
        relationPicker(entities = people, selectedId = personId, idOf = { it.id }, labelOf = { it.name }, onSelect = { personId = it })
        item { SectionLabel("Course", modifier = Modifier.padding(top = Spacing.md)) }
        relationPicker(entities = courses, selectedId = courseId, idOf = { it.id }, labelOf = { it.name }, onSelect = { courseId = it })
        item { SectionLabel("Goal", modifier = Modifier.padding(top = Spacing.md, bottom = Spacing.xl2)) }
        relationPicker(entities = goals, selectedId = goalId, idOf = { it.id }, labelOf = { it.title }, onSelect = { goalId = it })
    }
}
