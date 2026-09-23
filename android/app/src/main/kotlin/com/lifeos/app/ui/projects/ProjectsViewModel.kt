package com.lifeos.app.ui.projects

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.launch
import com.lifeos.app.data.local.entities.CLOSED_TASK_STATUSES
import com.lifeos.app.data.local.entities.NoteEntity
import com.lifeos.app.data.local.entities.ProjectEntity
import com.lifeos.app.data.local.entities.TaskEntity
import com.lifeos.app.data.local.entities.TransactionEntity
import com.lifeos.app.data.repository.FinanceRepository
import com.lifeos.app.data.repository.NoteRepository
import com.lifeos.app.data.repository.ProjectRepository
import com.lifeos.app.data.repository.StudyRepository
import com.lifeos.app.data.repository.TaskRepository
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn

/** Open-task count + this-week focus time — the two numbers the compact list
 * row shows per spec's own mockup ("Northstar / Active / 6 open tasks / 2h
 * 12m focus this week"). */
data class ProjectStat(val openTaskCount: Int = 0, val thisWeekFocusSeconds: Long = 0L)

data class ProjectDetailState(
    val project: ProjectEntity? = null,
    val openTasks: List<TaskEntity> = emptyList(),
    val thisWeekFocusSeconds: Long = 0L,
    val transactions: List<TransactionEntity> = emptyList(),
    val notes: List<NoteEntity> = emptyList(),
)

class ProjectsViewModel(
    private val projectRepository: ProjectRepository,
    private val taskRepository: TaskRepository,
    private val studyRepository: StudyRepository,
    private val financeRepository: FinanceRepository,
    private val noteRepository: NoteRepository,
) : ViewModel() {
    val projects: StateFlow<List<ProjectEntity>> = projectRepository.observeActive()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    /** One shared computation for every list row's stat line — so the list
     * and a project's own detail screen can never show two different counts
     * for the same project. */
    val projectStats: StateFlow<Map<String, ProjectStat>> = combine(
        taskRepository.observeAll().map { tasks ->
            tasks.filter { it.status !in CLOSED_TASK_STATUSES && it.projectId != null }.groupingBy { it.projectId!! }.eachCount()
        },
        studyRepository.observeThisWeekFocusByProject(),
    ) { taskCounts, focusMap ->
        (taskCounts.keys + focusMap.keys).associateWith { id -> ProjectStat(taskCounts[id] ?: 0, focusMap[id] ?: 0L) }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyMap())

    /**
     * Everything Project detail needs, combined once. Callers MUST wrap this
     * in `remember(projectId) { ... }` at the call site — it starts a fresh
     * sharing coroutine on every invocation (there's no per-id caching here,
     * the same reason AccountDetailScreen takes a plain id instead of a
     * dedicated per-entity ViewModel), so calling it bare from a Composable
     * body would restart the underlying Flow pipeline on every recomposition.
     */
    fun detailState(projectId: String): StateFlow<ProjectDetailState> {
        val openTasks = taskRepository.observeAll()
            .map { tasks -> tasks.filter { it.projectId == projectId && it.status !in CLOSED_TASK_STATUSES } }
        val transactions = financeRepository.observeAllTransactions()
            .map { txns -> txns.filter { it.projectId == projectId } }
        val notes = noteRepository.observeAll()
            .map { notes -> notes.filter { it.projectId == projectId } }

        return combine(
            projectRepository.observeById(projectId), openTasks, studyRepository.observeThisWeekFocusSecondsForProject(projectId), transactions, notes,
        ) { project, tasks, focusSeconds, txns, projectNotes ->
            ProjectDetailState(project, tasks, focusSeconds, txns, projectNotes)
        }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), ProjectDetailState())
    }

    /** The one action Project detail's read-only task preview supports
     * directly — Edit/Start Focus for a task stay on the Tasks tab itself
     * rather than duplicating that whole sheet here (spec §17: "Do not
     * attempt to fit desktop dashboard into phone"). */
    fun toggleTaskComplete(task: TaskEntity) {
        viewModelScope.launch { taskRepository.toggleComplete(task) }
    }
}
