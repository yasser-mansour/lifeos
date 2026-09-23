package com.lifeos.app.sync

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.google.gson.Gson
import com.lifeos.app.LifeOSApplication
import com.lifeos.app.data.local.entities.AccountEntity
import com.lifeos.app.data.local.entities.CourseEntity
import com.lifeos.app.data.local.entities.EventEntity
import com.lifeos.app.data.local.entities.FundEntity
import com.lifeos.app.data.local.entities.GoalEntity
import com.lifeos.app.data.local.entities.JournalEntryEntity
import com.lifeos.app.data.local.entities.NoteEntity
import com.lifeos.app.data.local.entities.OrganizationEntity
import com.lifeos.app.data.local.entities.PersonEntity
import com.lifeos.app.data.local.entities.ProjectEntity
import com.lifeos.app.data.local.entities.StudySessionEntity
import com.lifeos.app.data.local.entities.TaskEntity
import com.lifeos.app.data.local.entities.TopicEntity
import com.lifeos.app.data.local.entities.TransactionEntity
import com.lifeos.app.data.local.entities.TransferEntity
import com.lifeos.app.data.remote.AccountDto
import com.lifeos.app.data.remote.FundDto
import com.lifeos.app.data.remote.LifeOSApi
import com.lifeos.app.data.remote.TaskDto
import com.lifeos.app.data.remote.TransactionDto
import com.lifeos.app.data.remote.TransferDto
import retrofit2.Response
import java.time.Instant
import java.time.LocalDate
import java.time.format.DateTimeParseException

/**
 * The whole sync contract in one worker: drain the local sync_queue (push),
 * then pull each collection and reconcile it into Room. See docs/SYNC.md
 * for why this is push-then-pull (a local change should never be
 * immediately overwritten by a pull that started before it existed) and
 * for the "pending_push wins" conflict rule applied in every repository's
 * applyServerX() method.
 */
class SyncWorker(appContext: Context, params: WorkerParameters) : CoroutineWorker(appContext, params) {
    private val app = appContext.applicationContext as LifeOSApplication
    private val gson = Gson()

    override suspend fun doWork(): Result {
        val token = app.deviceStore.currentToken()
        val baseUrl = app.deviceStore.currentBaseUrl()
        if (token.isNullOrBlank() || baseUrl.isNullOrBlank()) return Result.success() // not paired yet — nothing to do

        return try {
            push()
            pull()
            app.deviceStore.recordSyncAttempt(succeededAtEpochMs = System.currentTimeMillis(), error = null)
            Result.success()
        } catch (e: Exception) {
            app.deviceStore.recordSyncAttempt(succeededAtEpochMs = null, error = e.message ?: e.javaClass.simpleName)
            Result.retry()
        }
    }

    private suspend fun push() {
        val pending = app.database.syncQueueDao().getAllPending()
        for (entry in pending) {
            try {
                when (pushOne(app.api, entry.entityType, entry.entityId, entry.operation, entry.payloadJson)) {
                    // A conflict (409) means the Mac's backend rejected this
                    // payload as stale and parked it for a human to resolve
                    // under Settings > Sync > Conflicts — this device's job is
                    // done either way, so stop retrying it and defer to
                    // whatever pull() fetches next (see markLocalSynced below).
                    PushOutcome.OK, PushOutcome.CONFLICT -> {
                        app.database.syncQueueDao().remove(entry)
                        markLocalSynced(entry.entityType, entry.entityId, entry.operation)
                    }
                    PushOutcome.RETRY -> {
                        // Leave it queued; WorkManager's own retry/backoff covers
                        // transient failures, and a stuck row is visible to the
                        // user as "pending" on the Devices screen rather than
                        // silently dropped (spec §77/§78).
                    }
                }
            } catch (e: Exception) {
                // Network/parse failure — same "leave it queued" handling as RETRY above.
            }
        }
    }

    private enum class PushOutcome { OK, CONFLICT, RETRY }

    private suspend fun pushOne(api: LifeOSApi, entityType: String, entityId: String, operation: String, payloadJson: String): PushOutcome {
        @Suppress("UNCHECKED_CAST")
        val payload = gson.fromJson(payloadJson, Map::class.java) as Map<String, Any?>
        val response: Response<*> = when (entityType) {
            "task" -> if (operation == "create") api.createTask(payload) else api.updateTask(entityId, payload)
            "transaction" -> when (operation) {
                "create" -> api.createTransaction(payload)
                "delete" -> api.deleteTransaction(entityId)
                else -> return PushOutcome.OK
            }
            "transfer" -> when (operation) {
                "create" -> api.createTransfer(payload)
                "delete" -> api.deleteTransfer(entityId)
                else -> return PushOutcome.OK
            }
            "journal_entry" -> if (operation == "create") api.createJournalEntry(payload) else api.updateJournalEntry(entityId, payload)
            "person" -> if (operation == "create") api.createPerson(payload) else api.updatePerson(entityId, payload)
            "organization" -> if (operation == "create") api.createOrganization(payload) else api.updateOrganization(entityId, payload)
            "fund" -> if (operation == "create") api.createFund(payload) else api.updateFund(entityId, payload)
            "note" -> if (operation == "create") api.createNote(payload) else api.updateNote(entityId, payload)
            "goal" -> if (operation == "create") api.createGoal(payload) else api.updateGoal(entityId, payload)
            "event" -> if (operation == "create") api.createEvent(payload) else api.updateEvent(entityId, payload)
            "study_session" -> when (operation) {
                "start" -> api.startStudySession(payload)
                // payload carries {"phase": ...} for a Pomodoro transition,
                // or is empty for a plain pause/resume — either way it's
                // safe to forward as-is (see apps.study.api.pause/resume).
                "pause" -> api.pauseStudySession(entityId, payload)
                "resume" -> api.resumeStudySession(entityId, payload)
                "finish" -> api.finishStudySession(entityId)
                "cancel" -> api.cancelStudySession(entityId)
                else -> return PushOutcome.OK
            }
            else -> return PushOutcome.OK
        }
        return when {
            response.isSuccessful -> PushOutcome.OK
            // A delete that 404s means the row is already gone server-side
            // (e.g. a retried delete after a dropped response) — that's the
            // desired end state, not a failure, so don't retry it forever.
            operation == "delete" && response.code() == 404 -> PushOutcome.OK
            response.code() == 409 -> PushOutcome.CONFLICT
            else -> PushOutcome.RETRY
        }
    }

    /** Clears the "pending_push"/"pending_delete" flag a push leaves on the
     * local row once the server has the last word on it — either it
     * accepted the push, or it rejected it as a conflict for a human to
     * resolve on the Mac. Until this runs, applyServerX()'s "pending_push
     * wins" rule blocks every future pull for that row, which — before this
     * fix — was permanent, since nothing ever cleared it: any local edit
     * silently froze that row out of sync forever. A confirmed delete
     * removes the row outright rather than marking it "synced". */
    private suspend fun markLocalSynced(entityType: String, entityId: String, operation: String) {
        when (entityType) {
            "task" -> app.taskRepository.markSynced(entityId)
            "transaction" -> if (operation == "delete") app.financeRepository.deleteTransactionRow(entityId) else app.financeRepository.markTransactionSynced(entityId)
            "transfer" -> if (operation == "delete") app.financeRepository.deleteTransferRow(entityId) else app.financeRepository.markTransferSynced(entityId)
            "journal_entry" -> app.journalRepository.markSynced(entityId)
            "person" -> app.personRepository.markSynced(entityId)
            "organization" -> app.organizationRepository.markSynced(entityId)
            "fund" -> app.financeRepository.markFundSynced(entityId)
            "note" -> app.noteRepository.markSynced(entityId)
            "goal" -> app.goalRepository.markSynced(entityId)
            "event" -> app.eventRepository.markSynced(entityId)
            "study_session" -> app.studyRepository.markSynced(entityId)
        }
    }

    private suspend fun pull() {
        val api = app.api

        val tasks = api.getTasks().body()?.results.orEmpty().map { it.toEntity() }
        app.taskRepository.applyServerTasks(tasks)

        val projects = api.getProjects().body()?.results.orEmpty().map {
            ProjectEntity(it.id, it.name, it.description, it.area, it.status, it.priority, it.archived, it.updatedAt.toEpochMsOrNow(), it.version, "synced")
        }
        app.projectRepository.applyServerProjects(projects)

        val courses = api.getCourses().body()?.results.orEmpty()
        app.studyRepository.applyServerCourses(courses.map { CourseEntity(it.id, it.name, it.teacher, it.color, it.archived, System.currentTimeMillis()) })
        val allTopics = courses.flatMap { c -> c.topics.map { TopicEntity(it.id, it.course, it.name, it.order) } }
        app.database.studyDao().upsertTopics(allTopics)

        // Finance uses an incremental cursor (spec §36/§39) rather than
        // always fetching page 1 fresh: modified_since=<last successful
        // pull> also returns anything soft-deleted since then, flagged
        // `deleted`, which is how a Mac-side delete ever reaches this
        // device at all — without it, a soft-deleted row simply vanishes
        // from a normal list response and this device would never know.
        val financeCursor = app.deviceStore.financeSyncCursor()
        val financeCursorForThisRun = Instant.now().toString()

        val accountDtos = api.getAccounts(modifiedSince = financeCursor).body()?.results.orEmpty()
        val (deletedAccounts, activeAccountDtos) = accountDtos.partition { it.deleted }
        app.financeRepository.applyServerAccounts(activeAccountDtos.map { it.toEntity() })
        // Accounts don't get resurrected as tombstones elsewhere — applyServerAccounts
        // already removes an inactive account's row, and a deleted account is
        // never "active", so no separate removal call is needed here.

        val transactionDtos = api.getTransactions(modifiedSince = financeCursor).body()?.results.orEmpty()
        val (deletedTransactions, activeTransactionDtos) = transactionDtos.partition { it.deleted }
        app.financeRepository.applyServerTransactions(activeTransactionDtos.map { it.toEntity() })
        app.financeRepository.removeTransactionsDeletedOnServer(deletedTransactions.map { it.id })

        val transferDtos = api.getTransfers(modifiedSince = financeCursor).body()?.results.orEmpty()
        val (deletedTransfers, activeTransferDtos) = transferDtos.partition { it.deleted }
        app.financeRepository.applyServerTransfers(activeTransferDtos.map { it.toEntity() })
        app.financeRepository.removeTransfersDeletedOnServer(deletedTransfers.map { it.id })

        // Fund (Finance V2) rides the same incremental cursor as the rest of
        // Finance — it's tombstone-aware on the backend (DeletionAwareSyncMixin)
        // exactly like Account/Transaction/Transfer, so a Fund deleted on the
        // Mac needs the same deleted-flag handling, not just a fresh upsert.
        val fundDtos = api.getFunds(modifiedSince = financeCursor).body()?.results.orEmpty()
        val (deletedFunds, activeFundDtos) = fundDtos.partition { it.deleted }
        app.financeRepository.applyServerFunds(activeFundDtos.map { it.toEntity() })
        // A deleted Fund's linked Transactions already had their fund_id
        // cleared server-side (see finance.views.fund_delete) — nothing
        // locally needs to change beyond removing the Fund row itself, and
        // the next Transaction pull naturally carries the now-null fund.
        app.financeRepository.removeFundsDeletedOnServer(deletedFunds.map { it.id })

        app.deviceStore.setFinanceSyncCursor(financeCursorForThisRun)

        val sessions = api.getStudySessions().body()?.results.orEmpty().map { dto ->
            val startedAtMs = dto.startedAt.toEpochMsOrNow()
            StudySessionEntity(
                id = dto.id, domain = dto.domain, courseId = dto.course, courseName = null, topicId = dto.topic, topicName = null,
                taskId = dto.task, projectId = dto.project, projectName = null, bookId = dto.book, bookName = null, mode = dto.mode, status = dto.status,
                plannedDurationSeconds = dto.plannedDurationSeconds,
                pomodoroFocusSeconds = dto.pomodoroFocusSeconds, pomodoroShortBreakSeconds = dto.pomodoroShortBreakSeconds,
                pomodoroLongBreakSeconds = dto.pomodoroLongBreakSeconds, pomodoroCyclesBeforeLongBreak = dto.pomodoroCyclesBeforeLongBreak,
                currentPhase = dto.currentPhase, completedFocusCycles = dto.completedFocusCycles,
                // A session pulled from the server (another device's phase
                // transition) has no local phase-start timestamp to trust —
                // "now" is the best available anchor until this device
                // itself drives the next transition.
                currentPhaseStartedAtEpochMs = System.currentTimeMillis(),
                startedAtEpochMs = startedAtMs, endedAtEpochMs = dto.endedAt?.toEpochMsOrNow(),
                originDeviceName = dto.originDevice, correctedDurationSeconds = null, correctionReason = null, notes = "",
                updatedAtEpochMs = System.currentTimeMillis(), version = dto.version, syncStatus = "synced",
            )
        }
        sessions.forEach { app.studyRepository.applyServerSession(it) }

        val journalEntries = api.getJournalEntries().body()?.results.orEmpty().map {
            JournalEntryEntity(it.id, it.date.toEpochDayOrNow(), it.title, it.body, it.mood, it.updatedAt.toEpochMsOrNow(), it.version, "synced")
        }
        app.journalRepository.applyServerEntries(journalEntries)

        // People/Notes/Goals/Events — previously fetched by no one; see
        // docs/SYNC.md, this was flagged as unfinished sync coverage.
        val people = api.getPeople().body()?.results.orEmpty().map {
            PersonEntity(it.id, it.name, it.organization, it.email, it.phone, gson.toJson(it.relationshipTypes), it.updatedAt.toEpochMsOrNow(), it.version, "synced")
        }
        app.personRepository.applyServerPeople(people)

        // Organization (Finance V2) — reuses the Finance cursor above rather
        // than a cursor of its own: it's tombstone-aware on the backend the
        // same way Fund is, and it's conceptually a Finance counterparty
        // sibling, so introducing a whole separate cursor field for one new
        // entity wasn't worth the extra state (a disclosed, minor scope
        // choice — see the rebuild report).
        val organizationDtos = api.getOrganizations(modifiedSince = financeCursor).body()?.results.orEmpty()
        val (deletedOrganizations, activeOrganizationDtos) = organizationDtos.partition { it.deleted }
        val organizations = activeOrganizationDtos.map {
            OrganizationEntity(
                it.id, it.name, it.website, it.email, it.phone, it.category, it.notes,
                gson.toJson(it.relationshipTypes), it.archived, it.updatedAt.toEpochMsOrNow(), it.version, "synced",
            )
        }
        app.organizationRepository.applyServerOrganizations(organizations)
        app.organizationRepository.removeDeletedOnServer(deletedOrganizations.map { it.id })

        val notes = api.getNotes().body()?.results.orEmpty().map {
            NoteEntity(it.id, it.title, it.content, it.project, it.task, it.person, it.course, it.goal, it.updatedAt.toEpochMsOrNow(), it.version, "synced")
        }
        app.noteRepository.applyServerNotes(notes)

        val goals = api.getGoals().body()?.results.orEmpty().map {
            GoalEntity(
                it.id, it.title, it.description, it.goalType, it.targetValue, it.currentValue, it.unit,
                it.deadline?.toEpochDayOrNow(), it.status, it.project, it.course, it.deriveFromStudyHours, it.progressPercent,
                it.updatedAt.toEpochMsOrNow(), it.version, "synced",
            )
        }
        app.goalRepository.applyServerGoals(goals)

        val events = api.getEvents().body()?.results.orEmpty().map {
            EventEntity(
                it.id, it.title, it.description, it.start.toEpochMsOrNow(), it.end?.toEpochMsOrNow(), it.allDay, it.category,
                it.project, it.person, it.course, it.updatedAt.toEpochMsOrNow(), it.version, "synced",
            )
        }
        app.eventRepository.applyServerEvents(events)
    }
}

private fun AccountDto.toEntity(): AccountEntity =
    AccountEntity(id, name, institution, accountType, context, currency, openingBalance, balance, active, updatedAt.toEpochMsOrNow(), version, "synced")

private fun FundDto.toEntity(): FundEntity =
    FundEntity(id, name, context, project, notes, archived, balance, updatedAt.toEpochMsOrNow(), version, "synced")

private fun TransactionDto.toEntity(): TransactionEntity = TransactionEntity(
    id, account, fund, null, amount, currency, type, direction, date.toEpochDayOrNow(), category, null, description, project, person,
    organization, null, notes, updatedAt.toEpochMsOrNow(), version, "synced",
)

private fun TransferDto.toEntity(): TransferEntity = TransferEntity(
    id, fromAccount, toAccount, fromFund, null, toFund, null, amount, currency, date.toEpochDayOrNow(), description, notes,
    updatedAt.toEpochMsOrNow(), version, "synced",
)

private fun TaskDto.toEntity(): TaskEntity = TaskEntity(
    id = id, title = title, description = description, status = status, priority = priority,
    dueDateEpochDay = dueDate?.let { runCatching { LocalDate.parse(it).toEpochDay() }.getOrNull() },
    projectId = project, projectName = null, courseId = course, courseName = null, personId = person,
    waitingOn = waitingOn.orEmpty(), followUpDateEpochDay = followUpDate?.let { runCatching { LocalDate.parse(it).toEpochDay() }.getOrNull() },
    completedAtEpochMs = completedAt?.toEpochMsOrNow(), updatedAtEpochMs = updatedAt.toEpochMsOrNow(), version = version, syncStatus = "synced",
)

private fun String.toEpochMsOrNow(): Long = try {
    Instant.parse(this).toEpochMilli()
} catch (e: DateTimeParseException) {
    System.currentTimeMillis()
}

private fun String.toEpochDayOrNow(): Long = try {
    LocalDate.parse(this).toEpochDay()
} catch (e: DateTimeParseException) {
    LocalDate.now().toEpochDay()
}
