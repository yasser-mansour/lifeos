package com.lifeos.app.ui.finance

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.lifeos.app.data.local.entities.TransactionEntity
import com.lifeos.app.ui.format.formatMoneySigned
import com.lifeos.app.ui.theme.LocalLifeOSColors
import com.lifeos.app.ui.theme.Spacing
import com.lifeos.app.ui.theme.monoFamily

/**
 * The one compact transaction row every "everything tagged with X" section
 * uses — Project detail, Person detail, Organization detail, Fund detail.
 * Pulled out here the moment a fourth screen needed the identical
 * description/category/signed-amount layout, the same DRY trigger as
 * ui/format/Money.kt and friends.
 */
@Composable
fun TransactionRow(txn: TransactionEntity) {
    val colors = LocalLifeOSColors.current
    Row(modifier = Modifier.fillMaxWidth().padding(vertical = Spacing.sm), horizontalArrangement = Arrangement.SpaceBetween) {
        Column {
            Text(txn.description.ifBlank { txn.type.replaceFirstChar { it.uppercase() } }, color = colors.textPrimary)
            Text(txn.categoryName ?: txn.type, color = colors.textMuted, style = MaterialTheme.typography.bodySmall)
        }
        Text(
            formatMoneySigned(txn.signedAmountDecimal(), txn.currency),
            style = MaterialTheme.typography.bodyLarge.copy(fontFamily = monoFamily),
            color = if (txn.direction == "in") colors.success else colors.textPrimary,
        )
    }
}
