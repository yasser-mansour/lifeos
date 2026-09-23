package com.lifeos.app.ui.projects

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Folder
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import com.lifeos.app.data.local.entities.ProjectEntity
import com.lifeos.app.ui.components.EmptyState
import com.lifeos.app.ui.components.LifeOSListRow
import com.lifeos.app.ui.components.ScreenHeader
import com.lifeos.app.ui.format.formatDurationCompact
import com.lifeos.app.ui.theme.Spacing

/**
 * A compact list, not a card grid (spec §17): name, status, and the two
 * numbers that actually answer "how is this project doing" — open tasks and
 * this week's focus time — on one subtitle line rather than the mockup's
 * separate lines, so the row stays a normal list row instead of a card.
 */
@Composable
fun ProjectsScreen(viewModel: ProjectsViewModel, onOpenProject: (String) -> Unit) {
    val projects by viewModel.projects.collectAsState()
    val stats by viewModel.projectStats.collectAsState()

    Column(modifier = Modifier.fillMaxSize().padding(horizontal = Spacing.xl)) {
        ScreenHeader("Projects")
        if (projects.isEmpty()) {
            EmptyState(icon = Icons.Filled.Folder, title = "No projects yet", body = "Projects sync down once you're paired with your Mac.")
        } else {
            LazyColumn(modifier = Modifier.fillMaxSize()) {
                items(projects, key = { it.id }) { project ->
                    val stat = stats[project.id]
                    LifeOSListRow(
                        title = project.name,
                        subtitle = rowSubtitle(project, stat),
                        onClick = { onOpenProject(project.id) },
                    )
                }
            }
        }
    }
}

private fun rowSubtitle(project: ProjectEntity, stat: ProjectStat?): String {
    val parts = mutableListOf(project.status.replaceFirstChar { it.uppercase() })
    val taskCount = stat?.openTaskCount ?: 0
    if (taskCount > 0) parts += if (taskCount == 1) "1 open task" else "$taskCount open tasks"
    val focusSeconds = stat?.thisWeekFocusSeconds ?: 0L
    if (focusSeconds > 0) parts += "${formatDurationCompact(focusSeconds)} this week"
    return parts.joinToString(" · ")
}
