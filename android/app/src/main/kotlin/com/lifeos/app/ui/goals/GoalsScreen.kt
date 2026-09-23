package com.lifeos.app.ui.goals

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Flag
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.lifeos.app.data.local.entities.GoalEntity
import com.lifeos.app.ui.components.EmptyState
import com.lifeos.app.ui.components.ScreenHeader
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.PillShape
import com.lifeos.app.ui.theme.Spacing

@Composable
fun GoalsScreen(viewModel: GoalsViewModel, onAddGoal: () -> Unit) {
    val goals by viewModel.goals.collectAsState()
    val colors = LocalLifeOSColors.current

    Scaffold(
        containerColor = colors.bgPrimary,
        floatingActionButton = {
            FloatingActionButton(onClick = onAddGoal, containerColor = colors.accent) {
                Icon(Icons.Filled.Add, contentDescription = "New Goal", tint = Color.White)
            }
        },
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(horizontal = Spacing.xl)) {
            ScreenHeader("Goals")
            if (goals.isEmpty()) {
                EmptyState(icon = Icons.Filled.Flag, title = "No goals yet", body = "Study 100 hours, save 5,000 MAD — track it here.")
            } else {
                LazyColumn(modifier = Modifier.fillMaxSize()) {
                    items(goals, key = { it.id }) { goal -> GoalRow(goal) }
                }
            }
        }
    }
}

@Composable
private fun GoalRow(goal: GoalEntity) {
    val colors = LocalLifeOSColors.current
    Column(modifier = Modifier.fillMaxWidth().padding(vertical = Spacing.sm)) {
        Text(goal.title, style = MaterialTheme.typography.titleMedium, color = colors.textPrimary)
        val target = goal.targetValue
        if (target != null) {
            Text(
                "${goal.currentValue} / $target ${goal.unit}".trim(),
                style = MaterialTheme.typography.bodySmall, color = colors.textMuted,
                modifier = Modifier.padding(top = 2.dp, bottom = Spacing.xs),
            )
            val fraction = (goal.progressPercent ?: 0).coerceIn(0, 100) / 100f
            Box(modifier = Modifier.fillMaxWidth().height(6.dp).clip(PillShape).background(colors.surfaceSecondary)) {
                Box(modifier = Modifier.fillMaxWidth(fraction).height(6.dp).clip(PillShape).background(colors.accent))
            }
        }
    }
}
