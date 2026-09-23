package com.lifeos.app.ui.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.lifeos.app.data.local.entities.StudySessionEntity
import com.lifeos.app.data.local.entities.TaskEntity
import com.lifeos.app.data.local.entities.TransactionEntity
import com.lifeos.app.data.repository.FinanceRepository
import com.lifeos.app.data.repository.FinanceRepository.Companion.liveBalance
import com.lifeos.app.data.repository.ProjectRepository
import com.lifeos.app.data.repository.StudyRepository
import com.lifeos.app.data.repository.TaskRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import java.math.BigDecimal

/** One row in Home's merged "Recent" feed (spec §8) — a transaction, a
 * finished focus session, or a completed task, whichever happened last. */
sealed class HomeActivityRow(val atEpochMs: Long) {
    class Money(val transaction: TransactionEntity) : HomeActivityRow(transaction.updatedAtEpochMs)
    class Focus(val session: StudySessionEntity, val durationSeconds: Long) : HomeActivityRow(session.endedAtEpochMs ?: session.updatedAtEpochMs)
    class TaskDone(val task: TaskEntity) : HomeActivityRow(task.completedAtEpochMs ?: task.updatedAtEpochMs)
}

data class HomeUiState(
    val openTasks: List<TaskEntity> = emptyList(),
    val personalBalance: BigDecimal = BigDecimal.ZERO,
    val businessBalance: BigDecimal = BigDecimal.ZERO,
    val totalBalance: BigDecimal = BigDecimal.ZERO,
    val singleCurrency: String? = null,
    val activeSession: StudySessionEntity? = null,
    val todayFocusSeconds: Long = 0,
    val todayTopDomain: Pair<String, Long>? = null,
    val recentActivity: List<HomeActivityRow> = emptyList(),
)

class HomeViewModel(
    private val taskRepository: TaskRepository,
    projectRepository: ProjectRepository,
    private val financeRepository: FinanceRepository,
    private val studyRepository: StudyRepository,
) : ViewModel() {

    private data class MoneyPart(val personal: BigDecimal, val business: BigDecimal, val total: BigDecimal, val currency: String?)

    private val moneyPart: Flow<MoneyPart> = combine(
        financeRepository.observeAccounts(), financeRepository.observePendingTransactions(), financeRepository.observePendingTransfers(),
    ) { accounts, pendingTxns, pendingTransfers ->
        val currencies = accounts.map { it.currency }.distinct()
        val currency = currencies.singleOrNull()
        fun sum(ctx: String?) = accounts.filter { ctx == null || it.context == ctx }.fold(BigDecimal.ZERO) { acc, a -> acc + liveBalance(a, pendingTxns, pendingTransfers) }
        MoneyPart(personal = sum("personal"), business = sum("business"), total = if (currency != null) sum(null) else BigDecimal.ZERO, currency = currency)
    }

    private data class FocusPart(val todaySeconds: Long, val todayByDomain: Map<String, Long>, val recentFinished: List<Pair<StudySessionEntity, Long>>)

    private val focusPart = combine(
        studyRepository.observeTodayFocusBreakdown(), studyRepository.observeRecentFinishedWithDuration(5),
    ) { (todaySeconds, byDomain), recentFinished -> FocusPart(todaySeconds, byDomain, recentFinished) }

    val uiState: StateFlow<HomeUiState> = combine(
        taskRepository.observeOpenTasks(),
        moneyPart,
        studyRepository.observeActiveSession(),
        financeRepository.observeRecentTransactions(10),
        focusPart,
    ) { tasks, money, activeSession, transactions, focus ->
        val recentTasks = tasks.filter { it.completedAtEpochMs != null }
        val activity = (
            transactions.map { HomeActivityRow.Money(it) } +
                focus.recentFinished.map { HomeActivityRow.Focus(it.first, it.second) } +
                recentTasks.map { HomeActivityRow.TaskDone(it) }
            ).sortedByDescending { it.atEpochMs }.take(8)

        HomeUiState(
            openTasks = tasks.filter { it.completedAtEpochMs == null }.take(5),
            personalBalance = money.personal, businessBalance = money.business, totalBalance = money.total, singleCurrency = money.currency,
            activeSession = activeSession,
            todayFocusSeconds = focus.todaySeconds, todayTopDomain = focus.todayByDomain.maxByOrNull { it.value }?.toPair(),
            recentActivity = activity,
        )
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), HomeUiState())
}
