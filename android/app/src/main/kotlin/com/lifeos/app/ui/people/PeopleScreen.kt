package com.lifeos.app.ui.people

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Business
import androidx.compose.material.icons.filled.People
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import com.lifeos.app.data.local.entities.OrganizationEntity
import com.lifeos.app.data.local.entities.PersonEntity
import com.lifeos.app.ui.components.EmptyState
import com.lifeos.app.ui.components.LifeOSListRow
import com.lifeos.app.ui.components.PrimaryButton
import com.lifeos.app.ui.components.ScreenHeader
import com.lifeos.app.ui.format.relationshipLabels
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.Spacing

/** One row in the combined People & Organizations list (Finance V2 spec
 * §2/§11) — a Person and an Organization render slightly differently but
 * share one alphabetical list rather than two separate screens. */
private sealed class DirectoryEntry(val name: String) {
    class Person(val entity: PersonEntity) : DirectoryEntry(entity.name)
    class Org(val entity: OrganizationEntity) : DirectoryEntry(entity.name)
}

@Composable
fun PeopleScreen(viewModel: PeopleViewModel, onOpenPerson: (String) -> Unit, onOpenOrganization: (String) -> Unit) {
    val people by viewModel.people.collectAsState()
    val organizations by viewModel.organizations.collectAsState()
    val taskCounts by viewModel.openTaskCounts.collectAsState()
    val colors = LocalLifeOSColors.current
    var showAddPersonSheet by remember { mutableStateOf(false) }
    var showAddOrgSheet by remember { mutableStateOf(false) }

    val entries = remember(people, organizations) {
        (people.map { DirectoryEntry.Person(it) } + organizations.map { DirectoryEntry.Org(it) }).sortedBy { it.name.lowercase() }
    }

    Scaffold(
        containerColor = colors.bgPrimary,
        floatingActionButton = {
            FloatingActionButton(onClick = { showAddPersonSheet = true }, containerColor = colors.accent) {
                Icon(Icons.Filled.Add, contentDescription = "New Person", tint = Color.White)
            }
        },
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(horizontal = Spacing.xl)) {
            ScreenHeader(
                "People & Organizations",
                action = { Text("+ Org", color = colors.accent, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.clickable { showAddOrgSheet = true }) },
            )
            if (entries.isEmpty()) {
                EmptyState(icon = Icons.Filled.People, title = "Nothing here yet", body = "Clients, family, banks, and service providers — everyone you deal with financially.")
            } else {
                LazyColumn(modifier = Modifier.fillMaxSize()) {
                    items(entries, key = { if (it is DirectoryEntry.Person) "p_${it.entity.id}" else "o_${(it as DirectoryEntry.Org).entity.id}" }) { entry ->
                        when (entry) {
                            is DirectoryEntry.Person -> LifeOSListRow(
                                title = entry.entity.name,
                                subtitle = personSubtitle(entry.entity, taskCounts[entry.entity.id] ?: 0),
                                leading = { Icon(Icons.Filled.Person, contentDescription = "Person", tint = colors.textSecondary) },
                                onClick = { onOpenPerson(entry.entity.id) },
                            )
                            is DirectoryEntry.Org -> LifeOSListRow(
                                title = entry.entity.name,
                                subtitle = orgSubtitle(entry.entity),
                                leading = { Icon(Icons.Filled.Business, contentDescription = "Organization", tint = colors.textSecondary) },
                                onClick = { onOpenOrganization(entry.entity.id) },
                            )
                        }
                    }
                }
            }
        }
    }

    if (showAddPersonSheet) {
        AddPersonSheet(onDismiss = { showAddPersonSheet = false }, onCreate = viewModel::createPerson)
    }
    if (showAddOrgSheet) {
        AddOrganizationSheet(onDismiss = { showAddOrgSheet = false }, onCreate = viewModel::createOrganization)
    }
}

private fun personSubtitle(person: PersonEntity, openTaskCount: Int): String {
    val parts = mutableListOf<String>()
    parts += relationshipLabels(person.relationshipTypesJson)
    if (person.organization.isNotBlank()) parts += person.organization
    if (openTaskCount > 0) parts += if (openTaskCount == 1) "1 open task" else "$openTaskCount open tasks"
    return parts.joinToString(" · ").ifBlank { "No details yet" }
}

private fun orgSubtitle(org: OrganizationEntity): String {
    val parts = relationshipLabels(org.relationshipTypesJson).toMutableList()
    if (parts.isEmpty()) parts += org.category.replaceFirstChar { it.uppercase() }
    return parts.joinToString(" · ")
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AddPersonSheet(onDismiss: () -> Unit, onCreate: (String, String) -> Unit) {
    val colors = LocalLifeOSColors.current
    var name by remember { mutableStateOf("") }
    var organization by remember { mutableStateOf("") }

    ModalBottomSheet(onDismissRequest = onDismiss, containerColor = colors.surfacePrimary) {
        Column(modifier = Modifier.fillMaxWidth().padding(horizontal = Spacing.xl).padding(bottom = Spacing.xl3)) {
            Text(
                "New Person", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.SemiBold,
                color = colors.textPrimary, modifier = Modifier.padding(bottom = Spacing.lg),
            )
            OutlinedTextField(value = name, onValueChange = { name = it }, placeholder = { Text("Name") }, singleLine = true, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(
                value = organization, onValueChange = { organization = it }, placeholder = { Text("Organization (optional)") }, singleLine = true,
                modifier = Modifier.fillMaxWidth().padding(top = Spacing.md),
            )
            PrimaryButton(
                text = "Add Person", enabled = name.isNotBlank(),
                onClick = { onCreate(name.trim(), organization.trim()); onDismiss() },
                modifier = Modifier.fillMaxWidth().padding(top = Spacing.xl),
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AddOrganizationSheet(onDismiss: () -> Unit, onCreate: (String, String) -> Unit) {
    val colors = LocalLifeOSColors.current
    var name by remember { mutableStateOf("") }

    ModalBottomSheet(onDismissRequest = onDismiss, containerColor = colors.surfacePrimary) {
        Column(modifier = Modifier.fillMaxWidth().padding(horizontal = Spacing.xl).padding(bottom = Spacing.xl3)) {
            Text(
                "New Organization", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.SemiBold,
                color = colors.textPrimary, modifier = Modifier.padding(bottom = Spacing.lg),
            )
            Text(
                "Heroku, a bank, a landlord company — anything you deal with financially that isn't a person.",
                style = MaterialTheme.typography.bodySmall, color = colors.textMuted, modifier = Modifier.padding(bottom = Spacing.md),
            )
            OutlinedTextField(value = name, onValueChange = { name = it }, placeholder = { Text("Name") }, singleLine = true, modifier = Modifier.fillMaxWidth())
            PrimaryButton(
                text = "Add Organization", enabled = name.isNotBlank(),
                onClick = { onCreate(name.trim(), "other"); onDismiss() },
                modifier = Modifier.fillMaxWidth().padding(top = Spacing.xl),
            )
        }
    }
}
