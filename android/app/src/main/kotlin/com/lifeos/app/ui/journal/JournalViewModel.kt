package com.lifeos.app.ui.journal

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.lifeos.app.data.local.entities.JournalEntryEntity
import com.lifeos.app.data.repository.JournalRepository
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class JournalViewModel(private val repository: JournalRepository) : ViewModel() {
    val entries: StateFlow<List<JournalEntryEntity>> = repository.observeAll()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun createEntry(onCreated: (String) -> Unit) {
        viewModelScope.launch {
            val entry = repository.createEntry()
            onCreated(entry.id)
        }
    }

    fun save(entry: JournalEntryEntity, title: String, body: String, mood: String) {
        viewModelScope.launch { repository.saveEntry(entry, title, body, mood) }
    }
}
