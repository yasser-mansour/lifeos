package com.lifeos.app.ui.goals

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import com.lifeos.app.ui.components.PrimaryButton
import com.lifeos.app.ui.components.RelationOptionRow
import com.lifeos.app.ui.components.ScreenHeader
import com.lifeos.app.ui.components.SectionLabel
import com.lifeos.app.ui.components.relationPicker
import com.lifeos.app.ui.theme.Spacing

private val GOAL_TYPES = listOf("personal" to "Personal", "academic" to "Academic", "financial" to "Financial", "business" to "Business", "project" to "Project", "other" to "Other")

@Composable
fun AddGoalScreen(viewModel: GoalsViewModel, onSaved: () -> Unit) {
    val projects by viewModel.projects.collectAsState()
    val courses by viewModel.courses.collectAsState()

    var title by remember { mutableStateOf("") }
    var goalType by remember { mutableStateOf("personal") }
    var selectedProjectId by remember { mutableStateOf<String?>(null) }
    var selectedCourseId by remember { mutableStateOf<String?>(null) }

    LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = Spacing.xl)) {
        item {
            ScreenHeader("New Goal")
            OutlinedTextField(
                value = title, onValueChange = { title = it }, placeholder = { Text("Study 100 hours this semester") },
                singleLine = true, modifier = Modifier.fillMaxWidth(),
            )
            SectionLabel("Type", modifier = Modifier.padding(top = Spacing.xl))
        }
        items(GOAL_TYPES) { (value, label) ->
            RelationOptionRow(label = label, selected = goalType == value, onSelect = { goalType = value })
        }

        item { SectionLabel("Project (optional)", modifier = Modifier.padding(top = Spacing.lg)) }
        relationPicker(entities = projects, selectedId = selectedProjectId, idOf = { it.id }, labelOf = { it.name }, onSelect = { selectedProjectId = it })

        item { SectionLabel("Course (optional)", modifier = Modifier.padding(top = Spacing.lg)) }
        relationPicker(entities = courses, selectedId = selectedCourseId, idOf = { it.id }, labelOf = { it.name }, onSelect = { selectedCourseId = it })

        item {
            PrimaryButton(
                text = "Create Goal",
                onClick = { viewModel.createGoal(title, goalType, selectedProjectId, selectedCourseId); onSaved() },
                enabled = title.isNotBlank(),
                modifier = Modifier.fillMaxWidth().padding(top = Spacing.xl2, bottom = Spacing.xl2),
            )
        }
    }
}
