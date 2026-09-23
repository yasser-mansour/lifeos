package com.lifeos.app

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import com.lifeos.app.data.local.LifeOSDatabase
import com.lifeos.app.data.prefs.DeviceStore
import com.lifeos.app.data.remote.LifeOSApi
import com.lifeos.app.data.remote.NetworkModule
import com.lifeos.app.data.repository.EventRepository
import com.lifeos.app.data.repository.FinanceRepository
import com.lifeos.app.data.repository.GoalRepository
import com.lifeos.app.data.repository.JournalRepository
import com.lifeos.app.data.repository.NoteRepository
import com.lifeos.app.data.repository.OrganizationRepository
import com.lifeos.app.data.repository.PersonRepository
import com.lifeos.app.data.repository.ProjectRepository
import com.lifeos.app.data.repository.StudyRepository
import com.lifeos.app.data.repository.TaskRepository
import com.lifeos.app.sync.SyncScheduler

/**
 * Simple hand-rolled service locator — deliberately no DI framework. At
 * this project's size (one process, a handful of repositories) Hilt would
 * add a build-time/complexity cost without buying much; every dependency
 * here is constructed once, in order, in one place you can read top to
 * bottom.
 */
class LifeOSApplication : Application() {
    lateinit var database: LifeOSDatabase
        private set
    lateinit var deviceStore: DeviceStore
        private set
    lateinit var api: LifeOSApi
        private set
    lateinit var taskRepository: TaskRepository
        private set
    lateinit var projectRepository: ProjectRepository
        private set
    lateinit var financeRepository: FinanceRepository
        private set
    lateinit var studyRepository: StudyRepository
        private set
    lateinit var journalRepository: JournalRepository
        private set
    lateinit var personRepository: PersonRepository
        private set
    lateinit var organizationRepository: OrganizationRepository
        private set
    lateinit var noteRepository: NoteRepository
        private set
    lateinit var goalRepository: GoalRepository
        private set
    lateinit var eventRepository: EventRepository
        private set

    override fun onCreate() {
        super.onCreate()

        database = LifeOSDatabase.get(this)
        deviceStore = DeviceStore(this)
        api = NetworkModule.create(deviceStore)

        taskRepository = TaskRepository(database.taskDao(), database.syncQueueDao(), api)
        projectRepository = ProjectRepository(database.projectDao(), api)
        financeRepository = FinanceRepository(database.financeDao(), database.syncQueueDao(), api)
        studyRepository = StudyRepository(database.studyDao(), database.syncQueueDao(), api, deviceStore)
        journalRepository = JournalRepository(database.journalDao(), database.syncQueueDao(), api)
        personRepository = PersonRepository(database.personDao(), database.syncQueueDao(), api)
        organizationRepository = OrganizationRepository(database.organizationDao(), database.syncQueueDao(), api)
        noteRepository = NoteRepository(database.noteDao(), database.syncQueueDao(), api)
        goalRepository = GoalRepository(database.goalDao(), database.syncQueueDao(), api)
        eventRepository = EventRepository(database.eventDao(), database.syncQueueDao(), api)

        createNotificationChannels()
        SyncScheduler.schedulePeriodicSync(this)
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(STUDY_CHANNEL_ID, "Active focus session", NotificationManager.IMPORTANCE_LOW).apply {
                description = "Shows the running timer while you study"
                setShowBadge(false)
            }
        )
    }

    companion object {
        const val STUDY_CHANNEL_ID = "lifeos_study_timer"
    }
}
