package com.lifeos.app.ui.theme

import androidx.compose.ui.unit.dp

// Mirrors backend/static/css/tokens.css --space-* — see Color.kt for the
// same convention applied to the palette. Every screen should reach for one
// of these instead of a bare .dp literal.
object Spacing {
    val xs = 4.dp
    val sm = 8.dp
    val md = 12.dp
    val lg = 16.dp
    val xl = 20.dp
    val xl2 = 24.dp
    val xl3 = 32.dp
    val xl4 = 40.dp
    val xl5 = 48.dp
    val xl6 = 64.dp
}
