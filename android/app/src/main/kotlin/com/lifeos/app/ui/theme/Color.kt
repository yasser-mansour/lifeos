package com.lifeos.app.ui.theme

import androidx.compose.ui.graphics.Color

// Mirrors backend/static/css/tokens.css — see docs/UI_DESIGN.md. Keep the
// two in sync by hand; there are only a handful of tokens.

object LightPalette {
    val bgPrimary = Color(0xFFFAFAF9)
    val bgSecondary = Color(0xFFF1F1EF)
    val surfacePrimary = Color(0xFFFFFFFF)
    val surfaceSecondary = Color(0xFFF6F6F5)
    val borderSubtle = Color(0x17181B18)
    val borderStrong = Color(0x2E181B2E)
    val textPrimary = Color(0xFF1C1C1F)
    val textSecondary = Color(0xFF5B5B63)
    val textMuted = Color(0xFF94949C)
    val accent = Color(0xFF4954E0)
    val accentSoft = Color(0x1A4954E0)
    val success = Color(0xFF17875A)
    val successSoft = Color(0x1C17875A)
    val warning = Color(0xFFA3660F)
    val warningSoft = Color(0x1FA3660F)
    val danger = Color(0xFFC2403D)
    val dangerSoft = Color(0x1CC2403D)
}

object DarkPalette {
    val bgPrimary = Color(0xFF0E0E10)
    val bgSecondary = Color(0xFF141416)
    val surfacePrimary = Color(0xFF1A1A1D)
    val surfaceSecondary = Color(0xFF202023)
    val borderSubtle = Color(0x14FFFFFF)
    val borderStrong = Color(0x29FFFFFF)
    val textPrimary = Color(0xFFF1F1F3)
    val textSecondary = Color(0xFFA6A6AD)
    val textMuted = Color(0xFF717178)
    val accent = Color(0xFF8B93F5)
    val accentSoft = Color(0x298B93F5)
    val success = Color(0xFF3FCE94)
    val successSoft = Color(0x243FCE94)
    val warning = Color(0xFFE3A83B)
    val warningSoft = Color(0x24E3A83B)
    val danger = Color(0xFFE27573)
    val dangerSoft = Color(0x24E27573)
}
