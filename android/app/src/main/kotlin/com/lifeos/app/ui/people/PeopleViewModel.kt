package com.lifeos.app.ui.people

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.lifeos.app.data.local.entities.CLOSED_TASK_STATUSES
import com.lifeos.app.data.local.entities.NoteEntity
import com.lifeos.app.data.local.entities.OrganizationEntity
import com.lifeos.app.data.local.entities.PersonEntity
import com.lifeos.app.data.local.entities.TaskEntity
import com.lifeos.app.data.local.entities.TransactionEntity
import com.lifeos.app.data.repository.FinanceRepository
import com.lifeos.app.data.repository.NoteRepository
import com.lifeos.app.data.repository.OrganizationRepository
import com.lifeos.app.data.repository.PersonRepository
import com.lifeos.app.data.repository.TaskRepository
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class PersonDetailState(
    val person: PersonEntity? = null,
    val openTasks: List<TaskEntity> = emptyList(),
    val transactions: List<TransactionEntity> = emptyList(),
    val notes: List<NoteEntity> = emptyList(),
)

/** The Organization-side equivalent of PersonDetailState — no open-tasks
 * section, since nothing on Android links a Task to an Organization
 * (mirrors the backend, which has the identical gap — see
 * apps.people.services.organization_summary). */
data class OrganizationDetailState(
    val organization: OrganizationEntity? = null,
    val transactions: List<TransactionEntity> = emptyList(),
)

class PeopleViewModel(
    private val repository: PersonRepository,
    private val organizationRepository: OrganizationRepository,
    private val taskRepository: TaskRepository,
    private val financeRepository: FinanceRepository,
    private val noteRepository: NoteRepository,
) : ViewModel() {
    val people: StateFlow<List<PersonEntity>> = repository.observeAll()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val organizations: StateFlow<List<OrganizationEntity>> = organizationRepository.observeAll()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    /** Open-task count per person for the list row — same shared-computation
     * shape as ProjectsViewModel.projectStats, for the same reason. */
    val openTaskCounts: StateFlow<Map<String, Int>> = taskRepository.observeAll()
        .map { tasks -> tasks.filter { it.status !in CLOSED_TASK_STATUSES && it.personId != null }.groupingBy { it.personId!! }.eachCount() }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyMap())

    fun createPerson(name: String, organization: String) {
        if (name.isBlank()) return
        viewModelScope.launch { repository.createPerson(name.trim(), organization.trim()) }
    }

    fun createOrganization(name: String, category: String) {
        if (name.isBlank()) return
        viewModelScope.launch { organizationRepository.createOrganization(name.trim(), category) }
    }

    /**
     * Contact / Tasks / Finance / Notes — no Projects section here even
     * though the desktop's Person detail has one: Project<->Person is a
     * many-to-many on the backend with no Room table and no sync coverage
     * on Android yet (the same gap noted on Project detail's missing People
     * section — one gap, seen from both sides, not two). Callers must wrap
     * this in `remember(personId) { ... }` — see ProjectsViewModel.detailState.
     */
    fun detailState(personId: String): StateFlow<PersonDetailState> {
        val openTasks = taskRepository.observeAll()
            .map { tasks -> tasks.filter { it.personId == personId && it.status !in CLOSED_TASK_STATUSES } }
        val transactions = financeRepository.observeAllTransactions()
            .map { txns -> txns.filter { it.personId == personId } }
        val notes = noteRepository.observeAll()
            .map { notes -> notes.filter { it.personId == personId } }

        return combine(repository.observeById(personId), openTasks, transactions, notes) { person, tasks, txns, personNotes ->
            PersonDetailState(person, tasks, txns, personNotes)
        }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), PersonDetailState())
    }

    /** Same "wrap in remember(id)" contract as detailState above. */
    fun organizationDetailState(organizationId: String): StateFlow<OrganizationDetailState> {
        val transactions = financeRepository.observeAllTransactions()
            .map { txns -> txns.filter { it.organizationId == organizationId } }
        return combine(organizationRepository.observeById(organizationId), transactions) { organization, txns ->
            OrganizationDetailState(organization, txns)
        }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), OrganizationDetailState())
    }

    fun toggleTaskComplete(task: TaskEntity) {
        viewModelScope.launch { taskRepository.toggleComplete(task) }
    }
}
