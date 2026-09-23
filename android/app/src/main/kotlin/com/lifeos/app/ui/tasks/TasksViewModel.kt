package com.lifeos.app.ui.tasks

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.lifeos.app.data.local.entities.CourseEntity
import com.lifeos.app.data.local.entities.PersonEntity
import com.lifeos.app.data.local.entities.ProjectEntity
import com.lifeos.app.data.local.entities.TaskEntity
import com.lifeos.app.data.repository.PersonRepository
import com.lifeos.app.data.repository.ProjectRepository
import com.lifeos.app.data.repository.StudyRepository
import com.lifeos.app.data.repository.TaskRepository
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class TasksViewModel(
    private val taskRepository: TaskRepository,
    projectRepository: ProjectRepository,
    personRepository: PersonRepository,
    studyRepository: StudyRepository,
) : ViewModel() {

    /** "Next" view — the exact same overdue/dated/undated ordering Home's
     * NEXT section shows a preview of; this is the untruncated version. */
    val nextTasks: StateFlow<List<TaskEntity>> = taskRepository.observeOpenTasks()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    /** Unfiltered — Today/Upcoming/Waiting/Completed are sliced from this
     * one list client-side in TasksScreen (see TaskDao.observeAll). */
    val allTasks: StateFlow<List<TaskEntity>> = taskRepository.observeAll()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val projects: StateFlow<List<ProjectEntity>> = projectRepository.observeActive()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val people: StateFlow<List<PersonEntity>> = personRepository.observeAll()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val courses: StateFlow<List<CourseEntity>> = studyRepository.observeCourses()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    /** Create-in-context: a non-null projectId/courseId/personId links the
     * new task immediately, matching the desktop app's ?project=/etc. prefill
     * (see backend apps.tasks.views.task_list's create-in-context handling). */
    fun createTask(title: String, priority: String, projectId: String?, courseId: String? = null, personId: String? = null) {
        if (title.isBlank()) return
        viewModelScope.launch {
            taskRepository.createTask(
                title.trim(), priority, null, projectId, courseId, personId,
                projectName = projects.value.firstOrNull { it.id == projectId }?.name,
                courseName = courses.value.firstOrNull { it.id == courseId }?.name,
            )
        }
    }

    fun toggleComplete(task: TaskEntity) {
        viewModelScope.launch { taskRepository.toggleComplete(task) }
    }

    fun updateTask(
        task: TaskEntity, title: String, priority: String, dueDateEpochDay: Long?,
        projectId: String?, courseId: String?, personId: String?, waitingOn: String, followUpDateEpochDay: Long?,
    ) {
        if (title.isBlank()) return
        viewModelScope.launch {
            taskRepository.updateTask(
                task, title.trim(), priority, dueDateEpochDay,
                projectId, projects.value.firstOrNull { it.id == projectId }?.name,
                courseId, courses.value.firstOrNull { it.id == courseId }?.name,
                personId, waitingOn.trim(), followUpDateEpochDay,
            )
        }
    }
}
