package com.lifeos.app.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

private val sansFamily = FontFamily.Default
val monoFamily = FontFamily.Monospace

val LifeOSTypography = Typography(
    displayLarge = TextStyle(fontFamily = sansFamily, fontWeight = FontWeight.SemiBold, fontSize = 40.sp, letterSpacing = (-0.5).sp),
    displayMedium = TextStyle(fontFamily = sansFamily, fontWeight = FontWeight.SemiBold, fontSize = 32.sp, letterSpacing = (-0.4).sp),
    headlineLarge = TextStyle(fontFamily = sansFamily, fontWeight = FontWeight.SemiBold, fontSize = 24.sp, letterSpacing = (-0.3).sp),
    headlineMedium = TextStyle(fontFamily = sansFamily, fontWeight = FontWeight.SemiBold, fontSize = 20.sp),
    titleLarge = TextStyle(fontFamily = sansFamily, fontWeight = FontWeight.SemiBold, fontSize = 17.sp),
    titleMedium = TextStyle(fontFamily = sansFamily, fontWeight = FontWeight.Medium, fontSize = 15.sp),
    bodyLarge = TextStyle(fontFamily = sansFamily, fontWeight = FontWeight.Normal, fontSize = 15.sp, lineHeight = 22.sp),
    bodyMedium = TextStyle(fontFamily = sansFamily, fontWeight = FontWeight.Normal, fontSize = 14.sp, lineHeight = 20.sp),
    bodySmall = TextStyle(fontFamily = sansFamily, fontWeight = FontWeight.Normal, fontSize = 13.sp, lineHeight = 18.sp),
    labelLarge = TextStyle(fontFamily = sansFamily, fontWeight = FontWeight.Medium, fontSize = 13.sp),
    labelMedium = TextStyle(fontFamily = sansFamily, fontWeight = FontWeight.SemiBold, fontSize = 11.sp, letterSpacing = 0.6.sp),
    labelSmall = TextStyle(fontFamily = sansFamily, fontWeight = FontWeight.Medium, fontSize = 11.sp),
)
