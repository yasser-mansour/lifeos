package com.lifeos.app.ui.finance

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.lifeos.app.data.local.entities.AccountEntity
import com.lifeos.app.data.local.entities.CategoryEntity
import com.lifeos.app.data.local.entities.FundEntity
import com.lifeos.app.data.local.entities.OrganizationEntity
import com.lifeos.app.data.local.entities.PersonEntity
import com.lifeos.app.data.local.entities.ProjectEntity
import com.lifeos.app.data.local.entities.TransactionEntity
import com.lifeos.app.data.local.entities.TransferEntity
import com.lifeos.app.data.repository.FinanceRepository
import com.lifeos.app.data.repository.FinanceRepository.Companion.liveBalance
import com.lifeos.app.data.repository.OrganizationRepository
import com.lifeos.app.data.repository.PersonRepository
import com.lifeos.app.data.repository.ProjectRepository
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.math.BigDecimal
import java.time.LocalDate

/** An account paired with its live balance — server-confirmed balance plus
 * whatever this device has queued locally but not yet synced (spec §33). */
data class AccountWithLiveBalance(val account: AccountEntity, val liveBalance: BigDecimal)

data class FinanceHomeState(
    val accounts: List<AccountWithLiveBalance> = emptyList(),
    val recentTransactions: List<TransactionEntity> = emptyList(),
    val recentTransfers: List<TransferEntity> = emptyList(),
    val pendingCount: Int = 0,
)

class FinanceViewModel(
    private val repository: FinanceRepository,
    projectRepository: ProjectRepository,
    personRepository: PersonRepository,
    organizationRepository: OrganizationRepository,
) : ViewModel() {

    val homeState: StateFlow<FinanceHomeState> = combine(
        repository.observeAccounts(),
        repository.observeRecentTransactions(),
        repository.observeRecentTransfers(),
        repository.observePendingTransactions(),
        repository.observePendingTransfers(),
    ) { accounts, transactions, transfers, pendingTxns, pendingTransfers ->
        FinanceHomeState(
            accounts = accounts.map { AccountWithLiveBalance(it, liveBalance(it, pendingTxns, pendingTransfers)) },
            recentTransactions = transactions.filter { it.syncStatus != "pending_delete" },
            recentTransfers = transfers.filter { it.syncStatus != "pending_delete" },
            pendingCount = pendingTxns.count { it.syncStatus == "pending_push" } + pendingTransfers.count { it.syncStatus == "pending_push" },
        )
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), FinanceHomeState())

    // Kept for the Add Transaction / Transfer forms — the home state above
    // already carries live-balance accounts, but a plain list is simpler
    // wherever only "which accounts exist" matters.
    val accounts: StateFlow<List<AccountEntity>> = repository.observeAccounts()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val categories: StateFlow<List<CategoryEntity>> = repository.observeCategories()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val projects: StateFlow<List<ProjectEntity>> = projectRepository.observeActive()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val people: StateFlow<List<PersonEntity>> = personRepository.observeAll()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val organizations: StateFlow<List<OrganizationEntity>> = organizationRepository.observeAll()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    /** "What the money is for" (docs/FINANCE_V2.md) — Living, Family
     * Support, a per-project fund. Paired with live balance the same way
     * accounts are, so a not-yet-synced expense already moves the number
     * shown on Fund detail. */
    // Fund detail filters this client-side by fundId — the same
    // "one unfiltered flow, filter views client-side" pattern
    // Project/Person detail already use for their own Tasks/Finance/Notes
    // sections.
    val allTransactions: StateFlow<List<TransactionEntity>> = repository.observeAllTransactions()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val funds: StateFlow<List<FundWithLiveBalance>> = combine(
        repository.observeFunds(), repository.observePendingTransactions(), repository.observePendingTransfers(),
    ) { funds, pendingTxns, pendingTransfers ->
        funds.map { FundWithLiveBalance(it, FinanceRepository.Companion.liveFundBalance(it, pendingTxns, pendingTransfers)) }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun accountLiveBalance(accountId: String, pendingTxns: List<TransactionEntity>, pendingTransfers: List<TransferEntity>): BigDecimal? {
        val account = accounts.value.firstOrNull { it.id == accountId } ?: return null
        return liveBalance(account, pendingTxns, pendingTransfers)
    }

    fun transactionsForAccount(accountId: String) = repository.observeForAccount(accountId)
    fun transfersForAccount(accountId: String) = repository.observeTransfersForAccount(accountId)

    fun addTransaction(
        accountId: String, amount: BigDecimal, type: String, categoryId: String?, description: String,
        projectId: String? = null, personId: String? = null, fundId: String? = null, organizationId: String? = null,
    ) {
        if (amount <= BigDecimal.ZERO) return
        val direction = if (type in listOf("income", "refund")) "in" else "out"
        val categoryName = categories.value.firstOrNull { it.id == categoryId }?.name
        val fundName = fundId?.let { id -> funds.value.firstOrNull { it.fund.id == id }?.fund?.name }
        val organizationName = organizationId?.let { id -> organizations.value.firstOrNull { it.id == id }?.name }
        viewModelScope.launch {
            repository.createTransaction(
                accountId = accountId, amount = amount, currency = "MAD", type = type, direction = direction,
                dateEpochDay = LocalDate.now().toEpochDay(), categoryId = categoryId, categoryName = categoryName, description = description,
                projectId = projectId, personId = personId, fundId = fundId, fundName = fundName,
                organizationId = organizationId, organizationName = organizationName,
            )
        }
    }

    fun deleteTransaction(id: String) = viewModelScope.launch { repository.deleteTransaction(id) }

    fun addTransfer(
        fromAccountId: String, toAccountId: String, amount: BigDecimal, description: String,
        fromFundId: String? = null, toFundId: String? = null,
    ) {
        if (amount <= BigDecimal.ZERO) return
        if (fromAccountId == toAccountId && fromFundId == toFundId) return // nothing would actually move
        val fromFundName = fromFundId?.let { id -> funds.value.firstOrNull { it.fund.id == id }?.fund?.name }
        val toFundName = toFundId?.let { id -> funds.value.firstOrNull { it.fund.id == id }?.fund?.name }
        viewModelScope.launch {
            repository.createTransfer(
                fromAccountId, toAccountId, amount, "MAD", LocalDate.now().toEpochDay(), description,
                fromFundId, fromFundName, toFundId, toFundName,
            )
        }
    }

    fun deleteTransfer(id: String) = viewModelScope.launch { repository.deleteTransfer(id) }
}

data class FundWithLiveBalance(val fund: FundEntity, val liveBalance: BigDecimal)
