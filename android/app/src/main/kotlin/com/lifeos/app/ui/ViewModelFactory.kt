package com.lifeos.app.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.CreationExtras
import com.lifeos.app.LifeOSApplication
import com.lifeos.app.ui.calendar.CalendarViewModel
import com.lifeos.app.ui.devices.DevicesViewModel
import com.lifeos.app.ui.finance.FinanceViewModel
import com.lifeos.app.ui.goals.GoalsViewModel
import com.lifeos.app.ui.home.HomeViewModel
import com.lifeos.app.ui.journal.JournalViewModel
import com.lifeos.app.ui.notes.NotesViewModel
import com.lifeos.app.ui.people.PeopleViewModel
import com.lifeos.app.ui.projects.ProjectsViewModel
import com.lifeos.app.ui.study.StudyViewModel
import com.lifeos.app.ui.tasks.TasksViewModel

/** One factory for every screen's ViewModel — matches the manual DI used in
 * LifeOSApplication (see its doc comment for why there's no DI framework). */
class LifeOSViewModelFactory(private val app: LifeOSApplication) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>, extras: CreationExtras): T {
        return when (modelClass) {
            HomeViewModel::class.java -> HomeViewModel(app.taskRepository, app.projectRepository, app.financeRepository, app.studyRepository) as T
            StudyViewModel::class.java -> StudyViewModel(app.studyRepository, app) as T
            TasksViewModel::class.java -> TasksViewModel(app.taskRepository, app.projectRepository, app.personRepository, app.studyRepository) as T
            FinanceViewModel::class.java -> FinanceViewModel(app.financeRepository, app.projectRepository, app.personRepository, app.organizationRepository) as T
            JournalViewModel::class.java -> JournalViewModel(app.journalRepository) as T
            ProjectsViewModel::class.java -> ProjectsViewModel(
                app.projectRepository, app.taskRepository, app.studyRepository, app.financeRepository, app.noteRepository,
            ) as T
            DevicesViewModel::class.java -> DevicesViewModel(app.deviceStore, app) as T
            PeopleViewModel::class.java -> PeopleViewModel(app.personRepository, app.organizationRepository, app.taskRepository, app.financeRepository, app.noteRepository) as T
            NotesViewModel::class.java -> NotesViewModel(
                app.noteRepository, app.projectRepository, app.taskRepository, app.personRepository, app.studyRepository, app.goalRepository,
            ) as T
            GoalsViewModel::class.java -> GoalsViewModel(app.goalRepository, app.projectRepository, app.studyRepository) as T
            CalendarViewModel::class.java -> CalendarViewModel(app.eventRepository, app.projectRepository, app.personRepository, app.studyRepository) as T
            else -> throw IllegalArgumentException("Unknown ViewModel class: $modelClass")
        }
    }
}
