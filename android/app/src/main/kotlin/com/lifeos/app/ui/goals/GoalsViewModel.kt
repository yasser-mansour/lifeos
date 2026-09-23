package com.lifeos.app.ui.goals

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.lifeos.app.data.local.entities.CourseEntity
import com.lifeos.app.data.local.entities.GoalEntity
import com.lifeos.app.data.local.entities.ProjectEntity
import com.lifeos.app.data.repository.GoalRepository
import com.lifeos.app.data.repository.ProjectRepository
import com.lifeos.app.data.repository.StudyRepository
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class GoalsViewModel(
    private val repository: GoalRepository,
    projectRepository: ProjectRepository,
    studyRepository: StudyRepository,
) : ViewModel() {
    val goals: StateFlow<List<GoalEntity>> = repository.observeActive()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val projects: StateFlow<List<ProjectEntity>> = projectRepository.observeActive()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val courses: StateFlow<List<CourseEntity>> = studyRepository.observeCourses()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun createGoal(title: String, goalType: String, projectId: String?, courseId: String?) {
        if (title.isBlank()) return
        viewModelScope.launch { repository.createGoal(title.trim(), goalType, projectId, courseId) }
    }
}
