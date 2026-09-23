package com.lifeos.app.ui.notes

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.lifeos.app.data.local.entities.CourseEntity
import com.lifeos.app.data.local.entities.GoalEntity
import com.lifeos.app.data.local.entities.NoteEntity
import com.lifeos.app.data.local.entities.PersonEntity
import com.lifeos.app.data.local.entities.ProjectEntity
import com.lifeos.app.data.local.entities.TaskEntity
import com.lifeos.app.data.repository.GoalRepository
import com.lifeos.app.data.repository.NoteRepository
import com.lifeos.app.data.repository.PersonRepository
import com.lifeos.app.data.repository.ProjectRepository
import com.lifeos.app.data.repository.StudyRepository
import com.lifeos.app.data.repository.TaskRepository
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class NotesViewModel(
    private val repository: NoteRepository,
    projectRepository: ProjectRepository,
    taskRepository: TaskRepository,
    personRepository: PersonRepository,
    studyRepository: StudyRepository,
    goalRepository: GoalRepository,
) : ViewModel() {
    val notes: StateFlow<List<NoteEntity>> = repository.observeAll()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val projects: StateFlow<List<ProjectEntity>> = projectRepository.observeActive()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
    val tasks: StateFlow<List<TaskEntity>> = taskRepository.observeOpenTasks()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
    val people: StateFlow<List<PersonEntity>> = personRepository.observeAll()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
    val courses: StateFlow<List<CourseEntity>> = studyRepository.observeCourses()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
    val goals: StateFlow<List<GoalEntity>> = goalRepository.observeActive()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    /** Create-in-context: passing a non-null id pre-links the new note to
     * whatever entity it was opened from (see NoteRepository.createNote). */
    fun createNote(
        onCreated: (String) -> Unit,
        projectId: String? = null, taskId: String? = null, personId: String? = null, courseId: String? = null, goalId: String? = null,
    ) {
        viewModelScope.launch {
            val note = repository.createNote(projectId, taskId, personId, courseId, goalId)
            onCreated(note.id)
        }
    }

    fun save(note: NoteEntity, title: String, content: String, projectId: String?, taskId: String?, personId: String?, courseId: String?, goalId: String?) {
        viewModelScope.launch { repository.saveNote(note, title, content, projectId, taskId, personId, courseId, goalId) }
    }
}
