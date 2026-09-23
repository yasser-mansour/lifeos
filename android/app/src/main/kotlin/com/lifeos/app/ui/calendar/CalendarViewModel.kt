package com.lifeos.app.ui.calendar

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.lifeos.app.data.local.entities.CourseEntity
import com.lifeos.app.data.local.entities.EventEntity
import com.lifeos.app.data.local.entities.PersonEntity
import com.lifeos.app.data.local.entities.ProjectEntity
import com.lifeos.app.data.repository.EventRepository
import com.lifeos.app.data.repository.PersonRepository
import com.lifeos.app.data.repository.ProjectRepository
import com.lifeos.app.data.repository.StudyRepository
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class CalendarViewModel(
    private val repository: EventRepository,
    projectRepository: ProjectRepository,
    personRepository: PersonRepository,
    studyRepository: StudyRepository,
) : ViewModel() {
    val upcomingEvents: StateFlow<List<EventEntity>> = repository.observeUpcoming()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val projects: StateFlow<List<ProjectEntity>> = projectRepository.observeActive()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
    val people: StateFlow<List<PersonEntity>> = personRepository.observeAll()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
    val courses: StateFlow<List<CourseEntity>> = studyRepository.observeCourses()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun createEvent(title: String, startEpochMs: Long, category: String, projectId: String?, personId: String?, courseId: String?) {
        if (title.isBlank()) return
        viewModelScope.launch { repository.createEvent(title.trim(), startEpochMs, category, projectId, personId, courseId) }
    }
}
