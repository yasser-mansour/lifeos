package com.lifeos.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

data class LifeOSColors(
    val bgPrimary: Color,
    val bgSecondary: Color,
    val surfacePrimary: Color,
    val surfaceSecondary: Color,
    val borderSubtle: Color,
    val borderStrong: Color,
    val textPrimary: Color,
    val textSecondary: Color,
    val textMuted: Color,
    val accent: Color,
    val accentSoft: Color,
    val success: Color,
    val successSoft: Color,
    val warning: Color,
    val warningSoft: Color,
    val danger: Color,
    val dangerSoft: Color,
)

private fun LightPalette.toLifeOSColors() = LifeOSColors(
    bgPrimary, bgSecondary, surfacePrimary, surfaceSecondary, borderSubtle, borderStrong,
    textPrimary, textSecondary, textMuted, accent, accentSoft, success, successSoft, warning, warningSoft, danger, dangerSoft,
)

private fun DarkPalette.toLifeOSColors() = LifeOSColors(
    bgPrimary, bgSecondary, surfacePrimary, surfaceSecondary, borderSubtle, borderStrong,
    textPrimary, textSecondary, textMuted, accent, accentSoft, success, successSoft, warning, warningSoft, danger, dangerSoft,
)

val LocalLifeOSColors = staticCompositionLocalOf { LightPalette.toLifeOSColors() }

@Composable
fun LifeOSTheme(darkTheme: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    val lifeOSColors = if (darkTheme) DarkPalette.toLifeOSColors() else LightPalette.toLifeOSColors()

    val materialScheme = if (darkTheme) {
        darkColorScheme(
            primary = lifeOSColors.accent, onPrimary = Color.White,
            primaryContainer = lifeOSColors.accentSoft, onPrimaryContainer = lifeOSColors.accent,
            secondaryContainer = lifeOSColors.surfaceSecondary, onSecondaryContainer = lifeOSColors.textPrimary,
            background = lifeOSColors.bgPrimary, onBackground = lifeOSColors.textPrimary,
            surface = lifeOSColors.surfacePrimary, onSurface = lifeOSColors.textPrimary,
            surfaceVariant = lifeOSColors.surfaceSecondary, onSurfaceVariant = lifeOSColors.textSecondary,
            outline = lifeOSColors.borderStrong, outlineVariant = lifeOSColors.borderSubtle,
            error = lifeOSColors.danger, errorContainer = lifeOSColors.dangerSoft, onErrorContainer = lifeOSColors.danger,
        )
    } else {
        lightColorScheme(
            primary = lifeOSColors.accent, onPrimary = Color.White,
            primaryContainer = lifeOSColors.accentSoft, onPrimaryContainer = lifeOSColors.accent,
            secondaryContainer = lifeOSColors.surfaceSecondary, onSecondaryContainer = lifeOSColors.textPrimary,
            background = lifeOSColors.bgPrimary, onBackground = lifeOSColors.textPrimary,
            surface = lifeOSColors.surfacePrimary, onSurface = lifeOSColors.textPrimary,
            surfaceVariant = lifeOSColors.surfaceSecondary, onSurfaceVariant = lifeOSColors.textSecondary,
            outline = lifeOSColors.borderStrong, outlineVariant = lifeOSColors.borderSubtle,
            error = lifeOSColors.danger, errorContainer = lifeOSColors.dangerSoft, onErrorContainer = lifeOSColors.danger,
        )
    }

    CompositionLocalProvider(LocalLifeOSColors provides lifeOSColors) {
        MaterialTheme(colorScheme = materialScheme, typography = LifeOSTypography, shapes = LifeOSShapes, content = content)
    }
}
