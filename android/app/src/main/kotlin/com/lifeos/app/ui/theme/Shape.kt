package com.lifeos.app.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Shapes
import androidx.compose.ui.unit.dp

// Mirrors backend/static/css/tokens.css --radius-* (sm/md/lg/xl/full). Card-
// sized surfaces use `medium`; small controls (badges, chips) use `small`;
// nothing in this app should hardcode its own RoundedCornerShape anymore.
val LifeOSShapes = Shapes(
    extraSmall = RoundedCornerShape(6.dp),
    small = RoundedCornerShape(10.dp),
    medium = RoundedCornerShape(14.dp),
    large = RoundedCornerShape(18.dp),
    extraLarge = RoundedCornerShape(24.dp),
)

val PillShape = RoundedCornerShape(50)
