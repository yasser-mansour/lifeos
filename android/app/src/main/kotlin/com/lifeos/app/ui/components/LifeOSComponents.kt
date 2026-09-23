package com.lifeos.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Circle
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.PillShape
import com.lifeos.app.ui.theme.Spacing
import com.lifeos.app.ui.theme.monoFamily

@Composable
fun SectionLabel(text: String, modifier: Modifier = Modifier) {
    Text(
        text = text.uppercase(),
        style = MaterialTheme.typography.labelMedium,
        color = LocalLifeOSColors.current.textMuted,
        modifier = modifier.padding(bottom = Spacing.sm),
    )
}

/**
 * The header every top-level screen starts with: a title, and an optional
 * single trailing action (a button, an icon — whatever that screen's one
 * primary action is). Pulled out so "Home"/"Study"/"Finance" stop each
 * hand-rolling their own Row+Text+padding.
 */
@Composable
fun ScreenHeader(title: String, modifier: Modifier = Modifier, action: (@Composable () -> Unit)? = null) {
    Row(
        modifier = modifier.fillMaxWidth().padding(vertical = Spacing.xl),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(title, style = MaterialTheme.typography.headlineLarge, color = LocalLifeOSColors.current.textPrimary, fontWeight = FontWeight.SemiBold)
        action?.invoke()
    }
}

/**
 * A horizontal row of pill filters — used for the Focus domain filter
 * (All/School/Project/Business/…) and anywhere else a single-select set of
 * short labels beats a dropdown or a radio list. Unlike [RelationOptionRow]
 * (vertical, for a handful of longer entity names), this is for a small
 * fixed set of short labels people scan at a glance.
 */
@Composable
fun FilterChipRow(options: List<Pair<String, String>>, selected: String?, onSelect: (String?) -> Unit, modifier: Modifier = Modifier, allLabel: String? = "All") {
    LazyRow(modifier = modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        if (allLabel != null) {
            item { FilterChip(label = allLabel, active = selected == null, onClick = { onSelect(null) }) }
        }
        items(options) { (value, label) ->
            FilterChip(label = label, active = selected == value, onClick = { onSelect(value) })
        }
    }
}

@Composable
private fun FilterChip(label: String, active: Boolean, onClick: () -> Unit) {
    val colors = LocalLifeOSColors.current
    Box(
        modifier = Modifier
            .clip(PillShape)
            .background(if (active) colors.accent else colors.surfaceSecondary)
            .clickable(onClick = onClick)
            .padding(horizontal = Spacing.md, vertical = Spacing.sm),
    ) {
        Text(
            label,
            style = MaterialTheme.typography.labelLarge,
            color = if (active) Color.White else colors.textSecondary,
        )
    }
}

@Composable
fun LifeOSListRow(
    title: String,
    subtitle: String? = null,
    trailing: (@Composable () -> Unit)? = null,
    leading: (@Composable () -> Unit)? = null,
    onClick: (() -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .let { if (onClick != null) it.clickable(onClick = onClick) else it }
            .padding(vertical = Spacing.sm),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.md),
    ) {
        leading?.invoke()
        Column(modifier = Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.titleMedium, color = LocalLifeOSColors.current.textPrimary)
            if (subtitle != null) {
                Text(subtitle, style = MaterialTheme.typography.bodySmall, color = LocalLifeOSColors.current.textMuted)
            }
        }
        trailing?.invoke()
    }
}

@Composable
fun EmptyState(icon: androidx.compose.ui.graphics.vector.ImageVector, title: String, body: String, modifier: Modifier = Modifier, action: (@Composable () -> Unit)? = null) {
    Column(
        modifier = modifier.fillMaxWidth().padding(vertical = Spacing.xl5, horizontal = Spacing.xl2),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
    ) {
        Box(
            modifier = Modifier.size(44.dp).clip(MaterialTheme.shapes.medium).background(LocalLifeOSColors.current.surfaceSecondary),
            contentAlignment = Alignment.Center,
        ) {
            Icon(icon, contentDescription = null, tint = LocalLifeOSColors.current.textMuted)
        }
        Text(title, style = MaterialTheme.typography.titleLarge, color = LocalLifeOSColors.current.textPrimary)
        Text(body, style = MaterialTheme.typography.bodyMedium, color = LocalLifeOSColors.current.textMuted)
        action?.invoke()
    }
}

@Composable
fun PrimaryButton(text: String, onClick: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier,
        colors = ButtonDefaults.buttonColors(containerColor = LocalLifeOSColors.current.accent, contentColor = Color.White),
        shape = MaterialTheme.shapes.small,
    ) {
        Text(text, fontWeight = FontWeight.Medium)
    }
}

@Composable
fun StatusDot(color: Color, modifier: Modifier = Modifier) {
    Box(modifier = modifier.size(7.dp).clip(CircleShape).background(color))
}

@Composable
fun LifeOSBadge(text: String, color: Color, backgroundColor: Color, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier.clip(PillShape).background(backgroundColor).padding(horizontal = Spacing.sm, vertical = 3.dp),
    ) {
        Text(text, style = MaterialTheme.typography.labelSmall, color = color)
    }
}

@Composable
fun CheckToggle(checked: Boolean, onToggle: () -> Unit, modifier: Modifier = Modifier) {
    // The icon itself stays compact (matches the density of a task row);
    // the IconButton is left at its own default touch target instead of
    // being shrunk to the icon's size — a 28dp tap target on a
    // frequently-used row control was under Android's 48dp accessible
    // minimum (spec's "touch targets" pass).
    IconButton(onClick = onToggle, modifier = modifier) {
        if (checked) {
            Icon(Icons.Filled.CheckCircle, contentDescription = "Complete", tint = LocalLifeOSColors.current.success, modifier = Modifier.size(22.dp))
        } else {
            Icon(Icons.Filled.Circle, contentDescription = "Incomplete", tint = LocalLifeOSColors.current.borderStrong, modifier = Modifier.size(22.dp))
        }
    }
}

/**
 * One selectable row for a "pick a related entity" list (Project/Person/
 * Course/Goal/etc.) — the exact radio-row shape already used ad hoc in
 * StartFocusScreen and AddTransactionScreen, pulled out so every new
 * relationship picker (Task/Note/Goal/Event) looks and behaves the same
 * rather than each screen re-implementing it slightly differently.
 */
@Composable
fun RelationOptionRow(label: String, selected: Boolean, onSelect: () -> Unit, modifier: Modifier = Modifier) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .selectable(selected = selected, onClick = onSelect)
            .padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        RadioButton(selected = selected, onClick = null)
        Text(label, color = LocalLifeOSColors.current.textPrimary, modifier = Modifier.padding(start = 8.dp))
    }
}

/**
 * Renders a "None" row plus one [RelationOptionRow] per item inside an
 * existing LazyColumn — for an optional single-select relation field
 * (Task.project, Note.person, Goal.course, ...). [selectedId] is the
 * currently chosen id (null = none); [onSelect] receives null for "None".
 */
fun <T> LazyListScope.relationPicker(
    entities: List<T>,
    selectedId: String?,
    idOf: (T) -> String,
    labelOf: (T) -> String,
    onSelect: (String?) -> Unit,
) {
    item { RelationOptionRow(label = "None", selected = selectedId == null, onSelect = { onSelect(null) }) }
    items(entities, key = { idOf(it) }) { entity ->
        val id = idOf(entity)
        RelationOptionRow(label = labelOf(entity), selected = selectedId == id, onSelect = { onSelect(id) })
    }
}

/**
 * Amount-first entry (spec §26): a large, borderless, auto-focusing numeric
 * field that grabs the keyboard the moment the screen appears — logging a
 * transaction should never start with a tap to find the field first.
 */
@Composable
fun LifeOsAmountInput(value: String, onValueChange: (String) -> Unit, currency: String, modifier: Modifier = Modifier, autoFocus: Boolean = true) {
    val colors = LocalLifeOSColors.current
    val focusRequester = remember { FocusRequester() }

    Row(modifier = modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.Bottom) {
        TextField(
            value = value,
            onValueChange = { input -> onValueChange(input.filter { it.isDigit() || it == '.' }) },
            placeholder = {
                Text(
                    "0.00", style = TextStyle(fontFamily = monoFamily, fontWeight = FontWeight.SemiBold, fontSize = 52.sp, textAlign = TextAlign.Center),
                    color = colors.textMuted, modifier = Modifier.fillMaxWidth(),
                )
            },
            textStyle = TextStyle(fontFamily = monoFamily, fontWeight = FontWeight.SemiBold, fontSize = 52.sp, textAlign = TextAlign.Center, color = colors.textPrimary),
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
            colors = TextFieldDefaults.colors(
                unfocusedContainerColor = Color.Transparent, focusedContainerColor = Color.Transparent,
                unfocusedIndicatorColor = Color.Transparent, focusedIndicatorColor = Color.Transparent,
            ),
            modifier = Modifier.weight(1f, fill = false).focusRequester(focusRequester),
        )
        Text(
            currency, style = MaterialTheme.typography.titleMedium, color = colors.textMuted,
            modifier = Modifier.padding(bottom = Spacing.lg, start = Spacing.xs),
        )
    }

    if (autoFocus) {
        LaunchedEffect(Unit) { focusRequester.requestFocus() }
    }
}

/**
 * A native confirmation dialog styled with LIFEOS's own tokens instead of
 * the stock AlertDialog look (spec §32) — [destructive] renders the confirm
 * action in the danger color for anything that discards data.
 */
@Composable
fun ConfirmationDialog(
    title: String, message: String, confirmLabel: String, onConfirm: () -> Unit, onDismiss: () -> Unit,
    destructive: Boolean = true, dismissLabel: String = "Cancel",
) {
    val colors = LocalLifeOSColors.current
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title, fontWeight = FontWeight.SemiBold) },
        text = { Text(message, color = colors.textSecondary) },
        confirmButton = {
            TextButton(onClick = onConfirm) { Text(confirmLabel, color = if (destructive) colors.danger else colors.accent, fontWeight = FontWeight.Medium) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(dismissLabel, color = colors.textSecondary) } },
        containerColor = colors.surfacePrimary,
    )
}

enum class SyncState { SYNCED, SYNCING, OFFLINE_PENDING, ERROR }

/**
 * The one place sync state is ever shown (spec §45): small and quiet by
 * design — "boring is good" — never a banner. [pendingCount] is only read
 * when state is OFFLINE_PENDING.
 */
@Composable
fun SyncIndicator(state: SyncState, pendingCount: Int = 0, modifier: Modifier = Modifier) {
    val colors = LocalLifeOSColors.current
    val (label, dotColor) = when (state) {
        SyncState.SYNCED -> "Synced" to colors.success
        SyncState.SYNCING -> "Syncing…" to colors.accent
        SyncState.OFFLINE_PENDING -> (if (pendingCount > 0) "Offline · $pendingCount pending" else "Offline") to colors.warning
        SyncState.ERROR -> "Sync error" to colors.danger
    }
    Row(modifier = modifier, verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
        if (state == SyncState.SYNCING) {
            CircularProgressIndicator(modifier = Modifier.size(11.dp), strokeWidth = 1.5.dp, color = dotColor)
        } else {
            StatusDot(color = dotColor)
        }
        Text(label, style = MaterialTheme.typography.labelMedium, color = colors.textMuted)
    }
}

/** A label/value pair with a tabular-nums figure — recurring stat display
 * (Focus today, Study streak, account totals, …). */
@Composable
fun StatRow(label: String, value: String, modifier: Modifier = Modifier, valueColor: Color? = null) {
    val colors = LocalLifeOSColors.current
    Row(modifier = modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
        Text(label, style = MaterialTheme.typography.bodyMedium, color = colors.textSecondary)
        Text(
            value, style = MaterialTheme.typography.titleMedium.copy(fontFamily = monoFamily),
            color = valueColor ?: colors.textPrimary,
        )
    }
}
