package com.lifeos.app.ui.study

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.lifeos.app.LifeOSApplication
import com.lifeos.app.data.local.dao.RecentFocusContext
import com.lifeos.app.data.local.entities.CourseEntity
import com.lifeos.app.data.local.entities.SCHOOL_DOMAINS
import com.lifeos.app.data.local.entities.StudySessionEntity
import com.lifeos.app.data.repository.StudyRepository
import com.lifeos.app.study.PomodoroEngine
import com.lifeos.app.study.StudyTimerService
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class StudyOverviewState(
    val activeSession: StudySessionEntity? = null,
    val recentSessions: List<StudySessionEntity> = emptyList(),
    val courses: List<CourseEntity> = emptyList(),
    val todaySeconds: Long = 0,
    val todayByDomain: Map<String, Long> = emptyMap(),
)

class StudyViewModel(
    private val repository: StudyRepository,
    private val app: LifeOSApplication,
) : ViewModel() {

    val overviewState: StateFlow<StudyOverviewState> = combine(
        repository.observeActiveSession(),
        repository.observeCompletedSessions(),
        app.database.studyDao().observeCourses(),
        repository.observeTodayFocusBreakdown(),
    ) { active, completed, courses, todayBreakdown ->
        StudyOverviewState(
            activeSession = active, recentSessions = completed.take(20), courses = courses,
            todaySeconds = todayBreakdown.first, todayByDomain = todayBreakdown.second,
        )
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), StudyOverviewState())

    fun startSession(
        domain: String, courseId: String?, courseName: String?, projectId: String?, projectName: String?,
        mode: String, plannedMinutes: Int?,
        pomodoroFocusMinutes: Int = 25, pomodoroShortBreakMinutes: Int = 5, pomodoroLongBreakMinutes: Int = 15, pomodoroCycles: Int = 4,
    ) {
        viewModelScope.launch {
            val session = repository.startSession(
                domain = domain, courseId = courseId, courseName = courseName, topicId = null, topicName = null,
                taskId = null, projectId = projectId, projectName = projectName, mode = mode,
                plannedDurationSeconds = plannedMinutes?.times(60),
                pomodoroFocusSeconds = pomodoroFocusMinutes * 60, pomodoroShortBreakSeconds = pomodoroShortBreakMinutes * 60,
                pomodoroLongBreakSeconds = pomodoroLongBreakMinutes * 60, pomodoroCyclesBeforeLongBreak = pomodoroCycles,
            )
            StudyTimerService.start(app, session.id)
        }
    }

    fun pause(sessionId: String) = viewModelScope.launch { repository.pauseSession(sessionId) }
    fun resume(sessionId: String) = viewModelScope.launch { repository.resumeSession(sessionId) }

    fun finish(sessionId: String) = viewModelScope.launch {
        repository.finishSession(sessionId)
        StudyTimerService.stop(app)
    }

    fun cancel(sessionId: String) = viewModelScope.launch {
        repository.cancelSession(sessionId)
        StudyTimerService.stop(app)
    }

    suspend fun currentDuration(sessionId: String): Long = repository.durationSecondsFor(sessionId, System.currentTimeMillis())

    /** Advances a Pomodoro session to its next phase — called once the
     * countdown for the current phase reaches zero (spec §17). */
    fun advancePomodoroPhase(session: StudySessionEntity) = viewModelScope.launch {
        val next = PomodoroEngine.advance(session, System.currentTimeMillis())
        repository.advancePomodoroPhase(session, next)
    }

    suspend fun recentCourses(limit: Int = 5): List<RecentFocusContext> = app.database.studyDao().recentCourseContexts(limit)
    suspend fun recentProjects(domain: String, limit: Int = 5): List<RecentFocusContext> = app.database.studyDao().recentProjectContexts(domain, limit)
    val projects = app.projectRepository.observeActive()
}
