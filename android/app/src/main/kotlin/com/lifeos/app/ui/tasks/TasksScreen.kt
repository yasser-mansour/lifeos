package com.lifeos.app.ui.tasks

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberDatePickerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.lifeos.app.data.local.entities.CLOSED_TASK_STATUSES
import com.lifeos.app.data.local.entities.CourseEntity
import com.lifeos.app.data.local.entities.PersonEntity
import com.lifeos.app.data.local.entities.ProjectEntity
import com.lifeos.app.data.local.entities.TaskEntity
import com.lifeos.app.ui.components.CheckToggle
import com.lifeos.app.ui.components.EmptyState
import com.lifeos.app.ui.components.FilterChipRow
import com.lifeos.app.ui.components.LifeOSListRow
import com.lifeos.app.ui.components.PrimaryButton
import com.lifeos.app.ui.components.ScreenHeader
import com.lifeos.app.ui.components.SectionLabel
import com.lifeos.app.ui.components.StatusDot
import com.lifeos.app.ui.components.relationPicker
import com.lifeos.app.ui.format.completedPhrase
import com.lifeos.app.ui.format.followUpPhrase
import com.lifeos.app.ui.format.taskSubtitle
import com.lifeos.app.ui.haptics.rememberLifeOsHaptics
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.Spacing
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter

private val PRIORITY_RANK = mapOf("urgent" to 0, "high" to 1, "normal" to 2, "low" to 3)
private val TASK_VIEWS = listOf("next" to "Next", "today" to "Today", "upcoming" to "Upcoming", "waiting" to "Waiting", "completed" to "Completed")
private val PRIORITY_OPTIONS = listOf("urgent" to "Urgent", "high" to "High", "normal" to "Normal", "low" to "Low")
private val DATE_FORMAT = DateTimeFormatter.ofPattern("MMM d, yyyy")

/**
 * Tasks, rebuilt around the same five views the desktop uses to answer "what
 * should I do" (spec §16) instead of one flat list: Next mirrors Home's own
 * ordering, Today/Upcoming split the calendar-relevant work apart, Waiting
 * surfaces what's blocked on someone else, and Completed is a quiet archive
 * rather than clutter in the other four. Detail and edit are both bottom
 * sheets — no full-screen navigation for something this quick.
 */
@Composable
fun TasksScreen(viewModel: TasksViewModel, onStartFocus: (domain: String, projectId: String?, courseId: String?) -> Unit) {
    val nextTasks by viewModel.nextTasks.collectAsState()
    val allTasks by viewModel.allTasks.collectAsState()
    val projects by viewModel.projects.collectAsState()
    val courses by viewModel.courses.collectAsState()
    val people by viewModel.people.collectAsState()
    val colors = LocalLifeOSColors.current

    var view by remember { mutableStateOf("next") }
    var showAddSheet by remember { mutableStateOf(false) }
    var selectedTask by remember { mutableStateOf<TaskEntity?>(null) }

    val today = remember { LocalDate.now().toEpochDay() }
    val visibleTasks = remember(view, nextTasks, allTasks, today) {
        when (view) {
            "next" -> nextTasks
            "today" -> allTasks.filter { it.status !in CLOSED_TASK_STATUSES && it.dueDateEpochDay == today }
                .sortedBy { PRIORITY_RANK[it.priority] ?: 4 }
            "upcoming" -> allTasks.filter { it.status !in CLOSED_TASK_STATUSES && it.dueDateEpochDay != null && it.dueDateEpochDay > today }
                .sortedWith(compareBy({ it.dueDateEpochDay }, { PRIORITY_RANK[it.priority] ?: 4 }))
            "waiting" -> allTasks.filter { it.status == "waiting" }
                .sortedWith(compareBy({ it.followUpDateEpochDay == null }, { it.followUpDateEpochDay }))
            else -> allTasks.filter { it.status == "done" }.sortedByDescending { it.completedAtEpochMs }
        }
    }

    Scaffold(
        containerColor = colors.bgPrimary,
        floatingActionButton = {
            FloatingActionButton(onClick = { showAddSheet = true }, containerColor = colors.accent) {
                Icon(Icons.Filled.Add, contentDescription = "New Task", tint = Color.White)
            }
        },
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(horizontal = Spacing.xl)) {
            ScreenHeader("Tasks")
            FilterChipRow(
                options = TASK_VIEWS, selected = view, onSelect = { view = it ?: "next" }, allLabel = null,
                modifier = Modifier.padding(bottom = Spacing.md),
            )

            if (visibleTasks.isEmpty()) {
                EmptyState(icon = Icons.Filled.CheckCircle, title = emptyTitleFor(view), body = emptyBodyFor(view))
            } else {
                LazyColumn(modifier = Modifier.fillMaxSize()) {
                    items(visibleTasks, key = { it.id }) { task ->
                        TaskRow(task = task, view = view, onToggle = { viewModel.toggleComplete(task) }, onClick = { selectedTask = task })
                    }
                }
            }
        }
    }

    if (showAddSheet) {
        AddTaskSheet(
            projects = projects, courses = courses, people = people,
            onDismiss = { showAddSheet = false },
            onCreate = { title, priority, projectId, courseId, personId -> viewModel.createTask(title, priority, projectId, courseId, personId) },
        )
    }

    selectedTask?.let { task ->
        TaskDetailSheet(
            task = task, projects = projects, courses = courses, people = people,
            onDismiss = { selectedTask = null },
            onToggleComplete = { viewModel.toggleComplete(task); selectedTask = null },
            onStartFocus = { domain, projectId, courseId -> selectedTask = null; onStartFocus(domain, projectId, courseId) },
            onSave = { title, priority, dueDate, projectId, courseId, personId, waitingOn, followUp ->
                viewModel.updateTask(task, title, priority, dueDate, projectId, courseId, personId, waitingOn, followUp)
                selectedTask = null
            },
        )
    }
}

private fun emptyTitleFor(view: String) = when (view) {
    "waiting" -> "Nothing waiting"
    "completed" -> "Nothing completed yet"
    else -> "Nothing here"
}

private fun emptyBodyFor(view: String) = when (view) {
    "today" -> "Nothing due today."
    "upcoming" -> "No upcoming due dates."
    "waiting" -> "Tasks you're waiting on someone else for will show up here."
    "completed" -> "Finished tasks show up here."
    else -> "Add a task to get started."
}

private fun subtitleFor(task: TaskEntity, view: String): String? {
    val context = listOfNotNull(task.projectName, task.courseName).joinToString(" · ").ifBlank { null }
    return when (view) {
        "waiting" -> listOfNotNull(task.waitingOn.ifBlank { null }, followUpPhrase(task.followUpDateEpochDay)).joinToString(" · ")
        "completed" -> listOfNotNull(context, completedPhrase(task.completedAtEpochMs)).joinToString(" · ")
        else -> taskSubtitle(context, task.dueDateEpochDay)
    }
}

@Composable
private fun TaskRow(task: TaskEntity, view: String, onToggle: () -> Unit, onClick: () -> Unit) {
    val colors = LocalLifeOSColors.current
    val haptics = rememberLifeOsHaptics()
    LifeOSListRow(
        title = task.title,
        subtitle = subtitleFor(task, view),
        leading = {
            CheckToggle(
                checked = task.status == "done",
                // Only the completing tap gets a tick (spec §60's "task
                // completed" trigger) — un-completing is a correction, not
                // an accomplishment, so it stays silent.
                onToggle = { if (task.status != "done") haptics.tick(); onToggle() },
            )
        },
        trailing = {
            when (task.priority) {
                "urgent" -> StatusDot(color = colors.danger)
                "high" -> StatusDot(color = colors.warning)
                else -> {}
            }
        },
        onClick = onClick,
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AddTaskSheet(
    projects: List<ProjectEntity>, courses: List<CourseEntity>, people: List<PersonEntity>,
    onDismiss: () -> Unit, onCreate: (String, String, String?, String?, String?) -> Unit,
) {
    val colors = LocalLifeOSColors.current
    var title by remember { mutableStateOf("") }
    var priority by remember { mutableStateOf("normal") }
    var projectId by remember { mutableStateOf<String?>(null) }
    var courseId by remember { mutableStateOf<String?>(null) }
    var personId by remember { mutableStateOf<String?>(null) }
    var showMore by remember { mutableStateOf(false) }

    ModalBottomSheet(onDismissRequest = onDismiss, containerColor = colors.surfacePrimary) {
        LazyColumn(modifier = Modifier.fillMaxWidth().padding(horizontal = Spacing.xl).heightIn(max = 560.dp)) {
            item {
                Text(
                    "New Task", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.SemiBold,
                    color = colors.textPrimary, modifier = Modifier.padding(bottom = Spacing.lg),
                )
                OutlinedTextField(
                    value = title, onValueChange = { title = it }, placeholder = { Text("What needs doing?") },
                    singleLine = true, modifier = Modifier.fillMaxWidth(),
                )
                SectionLabel("Priority", modifier = Modifier.padding(top = Spacing.lg, bottom = Spacing.sm))
                FilterChipRow(options = PRIORITY_OPTIONS, selected = priority, onSelect = { priority = it ?: "normal" }, allLabel = null)

                Text(
                    if (showMore) "Hide details" else "Project, course, person…",
                    color = colors.accent, style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.padding(top = Spacing.lg, bottom = Spacing.sm).clickable { showMore = !showMore },
                )
            }
            if (showMore) {
                item { SectionLabel("Project") }
                relationPicker(projects, projectId, { it.id }, { it.name }, { projectId = it })
                item { SectionLabel("Course", modifier = Modifier.padding(top = Spacing.md)) }
                relationPicker(courses, courseId, { it.id }, { it.name }, { courseId = it })
                item { SectionLabel("Person", modifier = Modifier.padding(top = Spacing.md)) }
                relationPicker(people, personId, { it.id }, { it.name }, { personId = it })
            }
            item {
                PrimaryButton(
                    text = "Add Task", enabled = title.isNotBlank(),
                    onClick = { onCreate(title.trim(), priority, projectId, courseId, personId); onDismiss() },
                    modifier = Modifier.fillMaxWidth().padding(top = Spacing.xl, bottom = Spacing.xl3),
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TaskDetailSheet(
    task: TaskEntity, projects: List<ProjectEntity>, courses: List<CourseEntity>, people: List<PersonEntity>,
    onDismiss: () -> Unit, onToggleComplete: () -> Unit,
    onStartFocus: (domain: String, projectId: String?, courseId: String?) -> Unit,
    onSave: (String, String, Long?, String?, String?, String?, String, Long?) -> Unit,
) {
    val colors = LocalLifeOSColors.current
    var editing by remember(task.id) { mutableStateOf(false) }

    ModalBottomSheet(onDismissRequest = onDismiss, containerColor = colors.surfacePrimary) {
        if (!editing) {
            TaskDetailContent(
                task = task, projects = projects,
                onToggleComplete = onToggleComplete, onEdit = { editing = true }, onStartFocus = onStartFocus,
            )
        } else {
            TaskEditContent(task = task, projects = projects, courses = courses, people = people, onCancel = onDismiss, onSave = onSave)
        }
    }
}

@Composable
private fun TaskDetailContent(
    task: TaskEntity, projects: List<ProjectEntity>,
    onToggleComplete: () -> Unit, onEdit: () -> Unit, onStartFocus: (String, String?, String?) -> Unit,
) {
    val colors = LocalLifeOSColors.current
    Column(modifier = Modifier.fillMaxWidth().padding(Spacing.xl).padding(bottom = Spacing.xl3)) {
        Text(task.title, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.SemiBold, color = colors.textPrimary)
        val context = listOfNotNull(task.projectName, task.courseName).joinToString(" · ").ifBlank { null }
        Text(
            taskSubtitle(context, task.dueDateEpochDay) ?: "No due date",
            style = MaterialTheme.typography.bodyMedium, color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xs, bottom = Spacing.md),
        )

        if (task.status == "waiting") {
            Text(
                "Waiting on ${task.waitingOn.ifBlank { "…" }}", style = MaterialTheme.typography.bodyMedium,
                color = colors.warning, modifier = Modifier.padding(bottom = Spacing.xs),
            )
            Text(followUpPhrase(task.followUpDateEpochDay), style = MaterialTheme.typography.bodySmall, color = colors.textMuted)
        }

        HorizontalDivider(color = colors.borderSubtle, modifier = Modifier.padding(vertical = Spacing.lg))

        PrimaryButton(
            text = if (task.status == "done") "Mark as not done" else "Complete",
            onClick = onToggleComplete, modifier = Modifier.fillMaxWidth().padding(bottom = Spacing.sm),
        )
        OutlinedButton(
            onClick = {
                val project = projects.firstOrNull { it.id == task.projectId }
                val domain = when {
                    task.courseId != null -> "school"
                    task.projectId != null && project?.area == "business" -> "business"
                    task.projectId != null -> "project"
                    else -> "other"
                }
                onStartFocus(domain, task.projectId, task.courseId)
            },
            modifier = Modifier.fillMaxWidth().padding(bottom = Spacing.sm),
        ) { Text("Start Focus") }
        TextButton(onClick = onEdit, modifier = Modifier.fillMaxWidth()) { Text("Edit") }
    }
}

@Composable
private fun TaskEditContent(
    task: TaskEntity, projects: List<ProjectEntity>, courses: List<CourseEntity>, people: List<PersonEntity>,
    onCancel: () -> Unit, onSave: (String, String, Long?, String?, String?, String?, String, Long?) -> Unit,
) {
    val colors = LocalLifeOSColors.current
    var title by remember { mutableStateOf(task.title) }
    var priority by remember { mutableStateOf(task.priority) }
    var dueDateEpochDay by remember { mutableStateOf(task.dueDateEpochDay) }
    var projectId by remember { mutableStateOf(task.projectId) }
    var courseId by remember { mutableStateOf(task.courseId) }
    var personId by remember { mutableStateOf(task.personId) }
    var waitingOn by remember { mutableStateOf(task.waitingOn) }
    var followUpDateEpochDay by remember { mutableStateOf(task.followUpDateEpochDay) }
    var showDatePicker by remember { mutableStateOf(false) }
    var showFollowUpPicker by remember { mutableStateOf(false) }

    LazyColumn(modifier = Modifier.fillMaxWidth().padding(horizontal = Spacing.xl).heightIn(max = 600.dp)) {
        item {
            Text(
                "Edit Task", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.SemiBold,
                color = colors.textPrimary, modifier = Modifier.padding(bottom = Spacing.lg),
            )
            OutlinedTextField(value = title, onValueChange = { title = it }, singleLine = true, modifier = Modifier.fillMaxWidth())

            SectionLabel("Priority", modifier = Modifier.padding(top = Spacing.lg, bottom = Spacing.sm))
            FilterChipRow(options = PRIORITY_OPTIONS, selected = priority, onSelect = { priority = it ?: "normal" }, allLabel = null)

            SectionLabel("Due date", modifier = Modifier.padding(top = Spacing.lg, bottom = Spacing.xs))
            Row(verticalAlignment = Alignment.CenterVertically) {
                TextButton(onClick = { showDatePicker = true }) {
                    Text(dueDateEpochDay?.let { LocalDate.ofEpochDay(it).format(DATE_FORMAT) } ?: "No due date")
                }
                if (dueDateEpochDay != null) {
                    TextButton(onClick = { dueDateEpochDay = null }) { Text("Clear", color = colors.textMuted) }
                }
            }

            SectionLabel("Waiting for (optional)", modifier = Modifier.padding(top = Spacing.lg, bottom = Spacing.xs))
            Text(
                "Fill this in when the task is blocked on someone else — it moves to Waiting until you clear it.",
                style = MaterialTheme.typography.bodySmall, color = colors.textMuted, modifier = Modifier.padding(bottom = Spacing.xs),
            )
            OutlinedTextField(
                value = waitingOn, onValueChange = { waitingOn = it }, placeholder = { Text("e.g. Reply from Sara") },
                singleLine = true, modifier = Modifier.fillMaxWidth(),
            )
            if (waitingOn.isNotBlank()) {
                TextButton(onClick = { showFollowUpPicker = true }, modifier = Modifier.padding(top = Spacing.xs)) {
                    Text(followUpDateEpochDay?.let { "Follow up ${LocalDate.ofEpochDay(it).format(DATE_FORMAT)}" } ?: "Set a follow-up date (optional)")
                }
            }
        }

        item { SectionLabel("Project", modifier = Modifier.padding(top = Spacing.lg)) }
        relationPicker(projects, projectId, { it.id }, { it.name }, { projectId = it })
        item { SectionLabel("Course", modifier = Modifier.padding(top = Spacing.md)) }
        relationPicker(courses, courseId, { it.id }, { it.name }, { courseId = it })
        item { SectionLabel("Person", modifier = Modifier.padding(top = Spacing.md)) }
        relationPicker(people, personId, { it.id }, { it.name }, { personId = it })

        item {
            Row(modifier = Modifier.fillMaxWidth().padding(top = Spacing.xl, bottom = Spacing.xl3)) {
                TextButton(onClick = onCancel, modifier = Modifier.weight(1f)) { Text("Cancel") }
                PrimaryButton(
                    text = "Save", enabled = title.isNotBlank(),
                    onClick = { onSave(title.trim(), priority, dueDateEpochDay, projectId, courseId, personId, waitingOn.trim(), followUpDateEpochDay) },
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }

    if (showDatePicker) {
        SingleDatePickerDialog(
            initialEpochDay = dueDateEpochDay,
            onDismiss = { showDatePicker = false },
            onConfirm = { dueDateEpochDay = it; showDatePicker = false },
        )
    }
    if (showFollowUpPicker) {
        SingleDatePickerDialog(
            initialEpochDay = followUpDateEpochDay,
            onDismiss = { showFollowUpPicker = false },
            onConfirm = { followUpDateEpochDay = it; showFollowUpPicker = false },
        )
    }
}

/** A date-only picker (no time component — tasks only ever store a due
 * date), following the same DatePickerDialog-wraps-DatePicker shape
 * AddEventScreen's DateTimePickerDialog already established for this app. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SingleDatePickerDialog(initialEpochDay: Long?, onDismiss: () -> Unit, onConfirm: (Long?) -> Unit) {
    val initialMillis = (initialEpochDay ?: LocalDate.now().toEpochDay()) * 86_400_000L
    val state = rememberDatePickerState(initialSelectedDateMillis = initialMillis)
    DatePickerDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            TextButton(onClick = {
                val millis = state.selectedDateMillis
                onConfirm(millis?.let { Instant.ofEpochMilli(it).atZone(ZoneId.of("UTC")).toLocalDate().toEpochDay() })
            }) { Text("Done") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    ) { DatePicker(state = state) }
}
