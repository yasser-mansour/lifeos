package com.lifeos.app.ui.navigation

sealed class Destination(val route: String) {
    data object Pairing : Destination("pairing")
    data object Home : Destination("home")
    data object Study : Destination("study")
    // Query params are only ever appended when present (never "key=" with an
    // empty value) so an absent arg resolves to its navArgument defaultValue
    // of null, instead of the empty-string-vs-null ambiguity NavType.String
    // has when a key is present but blank.
    data object StartFocus : Destination("start_focus?domain={domain}&projectId={projectId}&courseId={courseId}") {
        fun buildRoute(domain: String? = null, projectId: String? = null, courseId: String? = null): String {
            val params = buildList {
                domain?.let { add("domain=$it") }
                projectId?.let { add("projectId=$it") }
                courseId?.let { add("courseId=$it") }
            }
            return if (params.isEmpty()) "start_focus" else "start_focus?${params.joinToString("&")}"
        }
    }
    data object ActiveFocus : Destination("active_focus")
    data object Tasks : Destination("tasks")
    data object Finance : Destination("finance")
    data object AddTransaction : Destination("add_transaction?accountId={accountId}&fundId={fundId}") {
        fun buildRoute(accountId: String? = null, fundId: String? = null): String {
            val params = buildList {
                accountId?.let { add("accountId=$it") }
                fundId?.let { add("fundId=$it") }
            }
            return if (params.isEmpty()) "add_transaction" else "add_transaction?${params.joinToString("&")}"
        }
    }
    data object AddTransfer : Destination("add_transfer?accountId={accountId}") {
        fun buildRoute(accountId: String? = null) = if (accountId != null) "add_transfer?accountId=$accountId" else "add_transfer?accountId="
    }
    data object AccountDetail : Destination("account/{accountId}") {
        fun buildRoute(accountId: String) = "account/$accountId"
    }
    data object Funds : Destination("funds")
    data object FundDetail : Destination("fund/{fundId}") {
        fun buildRoute(fundId: String) = "fund/$fundId"
    }
    data object More : Destination("more")
    data object Projects : Destination("projects")
    data object ProjectDetail : Destination("project/{projectId}") {
        fun buildRoute(projectId: String) = "project/$projectId"
    }
    data object People : Destination("people")
    data object PersonDetail : Destination("person/{personId}") {
        fun buildRoute(personId: String) = "person/$personId"
    }
    data object OrganizationDetail : Destination("organization/{organizationId}") {
        fun buildRoute(organizationId: String) = "organization/$organizationId"
    }
    data object Journal : Destination("journal")
    data object JournalEditor : Destination("journal_editor/{entryId}") {
        fun buildRoute(entryId: String) = "journal_editor/$entryId"
    }
    data object Notes : Destination("notes")
    data object NoteEditor : Destination("note_editor/{noteId}") {
        fun buildRoute(noteId: String) = "note_editor/$noteId"
    }
    data object Goals : Destination("goals")
    data object AddGoal : Destination("add_goal")
    data object Calendar : Destination("calendar")
    data object AddEvent : Destination("add_event")
    data object Devices : Destination("devices")
    data object SyncDiagnostics : Destination("sync_diagnostics")
    data object ManualPair : Destination("manual_pair")
    data object Settings : Destination("settings")
}

data class BottomNavItem(val destination: Destination, val label: String)

val bottomNavItems = listOf(
    BottomNavItem(Destination.Home, "Home"),
    BottomNavItem(Destination.Study, "Focus"),
    BottomNavItem(Destination.Tasks, "Tasks"),
    BottomNavItem(Destination.Finance, "Finance"),
    BottomNavItem(Destination.More, "More"),
)
