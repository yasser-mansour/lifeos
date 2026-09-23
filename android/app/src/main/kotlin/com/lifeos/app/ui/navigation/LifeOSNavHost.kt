package com.lifeos.app.ui.navigation

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.MoreHoriz
import androidx.compose.material.icons.filled.PlayCircle
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.lifeos.app.LifeOSApplication
import com.lifeos.app.ui.LifeOSViewModelFactory
import com.lifeos.app.ui.calendar.AddEventScreen
import com.lifeos.app.ui.calendar.CalendarScreen
import com.lifeos.app.ui.calendar.CalendarViewModel
import com.lifeos.app.ui.devices.DevicesScreen
import com.lifeos.app.ui.devices.DevicesViewModel
import com.lifeos.app.ui.devices.ManualPairScreen
import com.lifeos.app.ui.devices.PairingScreen
import com.lifeos.app.ui.devices.SyncDiagnosticsScreen
import com.lifeos.app.ui.finance.AccountDetailScreen
import com.lifeos.app.ui.finance.AddTransactionScreen
import com.lifeos.app.ui.finance.AddTransferScreen
import com.lifeos.app.ui.finance.FinanceScreen
import com.lifeos.app.ui.finance.FinanceViewModel
import com.lifeos.app.ui.finance.FundDetailScreen
import com.lifeos.app.ui.finance.FundsScreen
import com.lifeos.app.ui.goals.AddGoalScreen
import com.lifeos.app.ui.goals.GoalsScreen
import com.lifeos.app.ui.goals.GoalsViewModel
import com.lifeos.app.ui.home.HomeScreen
import com.lifeos.app.ui.home.HomeViewModel
import com.lifeos.app.ui.journal.JournalEditorScreen
import com.lifeos.app.ui.journal.JournalScreen
import com.lifeos.app.ui.journal.JournalViewModel
import com.lifeos.app.ui.more.MoreScreen
import com.lifeos.app.ui.notes.NoteEditorScreen
import com.lifeos.app.ui.notes.NotesScreen
import com.lifeos.app.ui.notes.NotesViewModel
import com.lifeos.app.ui.people.OrganizationDetailScreen
import com.lifeos.app.ui.people.PeopleScreen
import com.lifeos.app.ui.people.PeopleViewModel
import com.lifeos.app.ui.people.PersonDetailScreen
import com.lifeos.app.ui.projects.ProjectDetailScreen
import com.lifeos.app.ui.projects.ProjectsScreen
import com.lifeos.app.ui.projects.ProjectsViewModel
import com.lifeos.app.ui.settings.SettingsScreen
import com.lifeos.app.ui.study.ActiveFocusScreen
import com.lifeos.app.ui.study.StartFocusScreen
import com.lifeos.app.ui.study.StudyOverviewScreen
import com.lifeos.app.ui.study.StudyViewModel
import com.lifeos.app.ui.tasks.TasksScreen
import com.lifeos.app.ui.tasks.TasksViewModel
import com.lifeos.app.ui.theme.LocalLifeOSColors

private val topLevelRoutes = bottomNavItems.map { it.destination.route }.toSet()

@Composable
fun LifeOSNavHost(app: LifeOSApplication) {
    val navController = rememberNavController()
    val factory = LifeOSViewModelFactory(app)
    val colors = LocalLifeOSColors.current

    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.hierarchy?.firstOrNull { it.route in topLevelRoutes }?.route

    Scaffold(
        containerColor = colors.bgPrimary,
        bottomBar = {
            if (currentRoute != null) {
                NavigationBar(containerColor = colors.bgSecondary) {
                    bottomNavItems.forEach { item ->
                        NavigationBarItem(
                            selected = currentRoute == item.destination.route,
                            onClick = {
                                navController.navigate(item.destination.route) {
                                    popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = { Icon(iconFor(item.destination.route), contentDescription = item.label) },
                            label = { androidx.compose.material3.Text(item.label) },
                            colors = androidx.compose.material3.NavigationBarItemDefaults.colors(
                                selectedIconColor = colors.accent, selectedTextColor = colors.accent,
                                unselectedIconColor = colors.textMuted, unselectedTextColor = colors.textMuted,
                                indicatorColor = colors.accentSoft,
                            ),
                        )
                    }
                }
            }
        },
    ) { padding ->
        NavHost(navController = navController, startDestination = Destination.Home.route, modifier = Modifier.padding(padding)) {
            composable(Destination.Home.route) {
                val vm: HomeViewModel = viewModel(factory = factory)
                HomeScreen(
                    viewModel = vm,
                    onStartFocus = { navController.navigate(Destination.StartFocus.buildRoute()) },
                    onOpenActiveSession = { navController.navigate(Destination.ActiveFocus.route) },
                    onShowAllTasks = { navController.navigate(Destination.Tasks.route) },
                )
            }

            composable(Destination.Study.route) {
                val vm: StudyViewModel = viewModel(factory = factory)
                StudyOverviewScreen(
                    viewModel = vm,
                    onStartFocus = { navController.navigate(Destination.StartFocus.buildRoute()) },
                    onActiveSession = { navController.navigate(Destination.ActiveFocus.route) },
                )
            }
            composable(
                Destination.StartFocus.route,
                arguments = listOf(
                    navArgument("domain") { type = NavType.StringType; nullable = true; defaultValue = null },
                    navArgument("projectId") { type = NavType.StringType; nullable = true; defaultValue = null },
                    navArgument("courseId") { type = NavType.StringType; nullable = true; defaultValue = null },
                ),
            ) { backStackEntry ->
                val vm: StudyViewModel = viewModel(factory = factory)
                StartFocusScreen(
                    viewModel = vm,
                    onStarted = { navController.navigate(Destination.ActiveFocus.route) { popUpTo(Destination.Study.route) } },
                    initialDomain = backStackEntry.arguments?.getString("domain") ?: "school",
                    initialProjectId = backStackEntry.arguments?.getString("projectId"),
                    initialCourseId = backStackEntry.arguments?.getString("courseId"),
                )
            }
            composable(Destination.ActiveFocus.route) {
                val vm: StudyViewModel = viewModel(factory = factory)
                // Plain popBackStack, not popBackStack(Study.route) — this
                // screen is also reached directly from Home's "Active
                // Session" button, a path where Study/Focus was never
                // pushed, so a route-targeted pop silently no-ops (Nav
                // Compose returns false rather than throwing) and leaves the
                // screen stuck showing nothing once the session ends.
                ActiveFocusScreen(viewModel = vm, onFinished = { navController.popBackStack() })
            }

            composable(Destination.Tasks.route) {
                val vm: TasksViewModel = viewModel(factory = factory)
                TasksScreen(
                    viewModel = vm,
                    onStartFocus = { domain, projectId, courseId ->
                        navController.navigate(Destination.StartFocus.buildRoute(domain, projectId, courseId))
                    },
                )
            }

            composable(Destination.Finance.route) {
                val vm: FinanceViewModel = viewModel(factory = factory)
                FinanceScreen(
                    viewModel = vm,
                    onAddTransaction = { navController.navigate(Destination.AddTransaction.buildRoute()) },
                    onAddTransfer = { navController.navigate(Destination.AddTransfer.buildRoute()) },
                    onOpenAccount = { accountId -> navController.navigate(Destination.AccountDetail.buildRoute(accountId)) },
                    onFunds = { navController.navigate(Destination.Funds.route) },
                )
            }
            composable(Destination.Funds.route) {
                val vm: FinanceViewModel = viewModel(factory = factory)
                FundsScreen(viewModel = vm, onOpenFund = { fundId -> navController.navigate(Destination.FundDetail.buildRoute(fundId)) })
            }
            composable(
                Destination.FundDetail.route,
                arguments = listOf(navArgument("fundId") { type = NavType.StringType }),
            ) { backStackEntry ->
                val vm: FinanceViewModel = viewModel(factory = factory)
                val fundId = backStackEntry.arguments?.getString("fundId").orEmpty()
                FundDetailScreen(
                    viewModel = vm, fundId = fundId,
                    onAddTransaction = { id -> navController.navigate(Destination.AddTransaction.buildRoute(fundId = id)) },
                )
            }
            composable(
                Destination.AddTransaction.route,
                arguments = listOf(
                    navArgument("accountId") { type = NavType.StringType; nullable = true; defaultValue = null },
                    navArgument("fundId") { type = NavType.StringType; nullable = true; defaultValue = null },
                ),
            ) { backStackEntry ->
                val vm: FinanceViewModel = viewModel(factory = factory)
                AddTransactionScreen(
                    viewModel = vm, onSaved = { navController.popBackStack() },
                    initialAccountId = backStackEntry.arguments?.getString("accountId"),
                    initialFundId = backStackEntry.arguments?.getString("fundId"),
                )
            }
            composable(
                Destination.AddTransfer.route,
                arguments = listOf(navArgument("accountId") { type = NavType.StringType; nullable = true; defaultValue = null }),
            ) { backStackEntry ->
                val vm: FinanceViewModel = viewModel(factory = factory)
                AddTransferScreen(viewModel = vm, onSaved = { navController.popBackStack() }, initialFromAccountId = backStackEntry.arguments?.getString("accountId"))
            }
            composable(
                Destination.AccountDetail.route,
                arguments = listOf(navArgument("accountId") { type = NavType.StringType }),
            ) { backStackEntry ->
                val vm: FinanceViewModel = viewModel(factory = factory)
                val accountId = backStackEntry.arguments?.getString("accountId").orEmpty()
                AccountDetailScreen(
                    viewModel = vm, accountId = accountId,
                    onAddTransaction = { navController.navigate(Destination.AddTransaction.buildRoute(accountId)) },
                    onAddTransfer = { navController.navigate(Destination.AddTransfer.buildRoute(accountId)) },
                )
            }

            composable(Destination.More.route) {
                MoreScreen(
                    onProjects = { navController.navigate(Destination.Projects.route) },
                    onPeople = { navController.navigate(Destination.People.route) },
                    onGoals = { navController.navigate(Destination.Goals.route) },
                    onCalendar = { navController.navigate(Destination.Calendar.route) },
                    onNotes = { navController.navigate(Destination.Notes.route) },
                    onJournal = { navController.navigate(Destination.Journal.route) },
                    onDevices = { navController.navigate(Destination.Devices.route) },
                    onSettings = { navController.navigate(Destination.Settings.route) },
                )
            }
            composable(Destination.Projects.route) {
                val vm: ProjectsViewModel = viewModel(factory = factory)
                ProjectsScreen(viewModel = vm, onOpenProject = { projectId -> navController.navigate(Destination.ProjectDetail.buildRoute(projectId)) })
            }
            composable(
                Destination.ProjectDetail.route,
                arguments = listOf(navArgument("projectId") { type = NavType.StringType }),
            ) { backStackEntry ->
                val vm: ProjectsViewModel = viewModel(factory = factory)
                val projectId = backStackEntry.arguments?.getString("projectId") ?: return@composable
                ProjectDetailScreen(
                    viewModel = vm, projectId = projectId,
                    // Same popUpTo/launchSingleTop/restoreState shape as an
                    // actual bottom-nav tap (see the NavigationBar wiring
                    // above) — this is a tab switch, not a forward push, so
                    // it should behave like one instead of stacking a second
                    // Tasks destination under Home/Projects/ProjectDetail.
                    onOpenTasks = {
                        navController.navigate(Destination.Tasks.route) {
                            popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                            launchSingleTop = true
                            restoreState = true
                        }
                    },
                )
            }
            composable(Destination.People.route) {
                val vm: PeopleViewModel = viewModel(factory = factory)
                PeopleScreen(
                    viewModel = vm,
                    onOpenPerson = { personId -> navController.navigate(Destination.PersonDetail.buildRoute(personId)) },
                    onOpenOrganization = { organizationId -> navController.navigate(Destination.OrganizationDetail.buildRoute(organizationId)) },
                )
            }
            composable(
                Destination.PersonDetail.route,
                arguments = listOf(navArgument("personId") { type = NavType.StringType }),
            ) { backStackEntry ->
                val vm: PeopleViewModel = viewModel(factory = factory)
                val personId = backStackEntry.arguments?.getString("personId") ?: return@composable
                PersonDetailScreen(viewModel = vm, personId = personId)
            }
            composable(
                Destination.OrganizationDetail.route,
                arguments = listOf(navArgument("organizationId") { type = NavType.StringType }),
            ) { backStackEntry ->
                val vm: PeopleViewModel = viewModel(factory = factory)
                val organizationId = backStackEntry.arguments?.getString("organizationId") ?: return@composable
                OrganizationDetailScreen(viewModel = vm, organizationId = organizationId)
            }
            composable(Destination.Goals.route) {
                val vm: GoalsViewModel = viewModel(factory = factory)
                GoalsScreen(viewModel = vm, onAddGoal = { navController.navigate(Destination.AddGoal.route) })
            }
            composable(Destination.AddGoal.route) {
                val vm: GoalsViewModel = viewModel(factory = factory)
                AddGoalScreen(viewModel = vm, onSaved = { navController.popBackStack() })
            }
            composable(Destination.Calendar.route) {
                val vm: CalendarViewModel = viewModel(factory = factory)
                CalendarScreen(viewModel = vm, onAddEvent = { navController.navigate(Destination.AddEvent.route) })
            }
            composable(Destination.AddEvent.route) {
                val vm: CalendarViewModel = viewModel(factory = factory)
                AddEventScreen(viewModel = vm, onSaved = { navController.popBackStack() })
            }
            composable(Destination.Notes.route) {
                val vm: NotesViewModel = viewModel(factory = factory)
                NotesScreen(viewModel = vm, onOpenNote = { id -> navController.navigate(Destination.NoteEditor.buildRoute(id)) })
            }
            composable(Destination.NoteEditor.route, arguments = listOf(navArgument("noteId") { type = NavType.StringType })) { backStackEntry ->
                val vm: NotesViewModel = viewModel(factory = factory)
                val noteId = backStackEntry.arguments?.getString("noteId").orEmpty()
                NoteEditorScreen(viewModel = vm, noteId = noteId)
            }
            composable(Destination.Journal.route) {
                val vm: JournalViewModel = viewModel(factory = factory)
                JournalScreen(viewModel = vm, onOpenEntry = { id -> navController.navigate(Destination.JournalEditor.buildRoute(id)) })
            }
            composable(Destination.JournalEditor.route, arguments = listOf(navArgument("entryId") { type = NavType.StringType })) { backStackEntry ->
                val vm: JournalViewModel = viewModel(factory = factory)
                val entryId = backStackEntry.arguments?.getString("entryId").orEmpty()
                JournalEditorScreen(viewModel = vm, entryId = entryId)
            }
            composable(Destination.Devices.route) {
                val vm: DevicesViewModel = viewModel(factory = factory)
                DevicesScreen(
                    viewModel = vm, onPairNewDevice = { navController.navigate(Destination.Pairing.route) },
                    onDiagnostics = { navController.navigate(Destination.SyncDiagnostics.route) },
                )
            }
            composable(Destination.SyncDiagnostics.route) {
                val vm: DevicesViewModel = viewModel(factory = factory)
                SyncDiagnosticsScreen(viewModel = vm, onResetPairing = { navController.navigate(Destination.Pairing.route) })
            }
            composable(Destination.Pairing.route) {
                val vm: DevicesViewModel = viewModel(factory = factory)
                PairingScreen(
                    viewModel = vm, onPaired = { navController.popBackStack() },
                    onEnterManually = { navController.navigate(Destination.ManualPair.route) },
                )
            }
            composable(Destination.ManualPair.route) {
                val vm: DevicesViewModel = viewModel(factory = factory)
                ManualPairScreen(viewModel = vm, onPaired = { navController.popBackStack(Destination.Devices.route, inclusive = false) })
            }
            composable(Destination.Settings.route) {
                SettingsScreen(deviceStore = app.deviceStore, onDevices = { navController.navigate(Destination.Devices.route) })
            }
        }
    }
}

private fun iconFor(route: String) = when (route) {
    Destination.Home.route -> Icons.Filled.Home
    Destination.Study.route -> Icons.Filled.PlayCircle
    Destination.Tasks.route -> Icons.Filled.CheckCircle
    Destination.Finance.route -> Icons.Filled.AccountBalanceWallet
    else -> Icons.Filled.MoreHoriz
}
