package com.lifeos.app

import android.Manifest
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import com.lifeos.app.sync.SyncScheduler
import com.lifeos.app.ui.navigation.LifeOSNavHost
import com.lifeos.app.ui.theme.LifeOSTheme
import com.lifeos.app.ui.theme.LocalLifeOSColors

class MainActivity : ComponentActivity() {
    private val notificationPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { /* no-op either way */ }

    // Best-effort sync the moment the app comes back to the foreground
    // (spec §47) — WorkManager's ExistingWorkPolicy.REPLACE (see
    // SyncScheduler.syncNow) makes this safe to call on every resume: it
    // just supersedes whatever sync was already queued, and no-ops
    // instantly if unpaired or offline.
    override fun onResume() {
        super.onResume()
        SyncScheduler.syncNow(this)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }

        val app = application as LifeOSApplication

        setContent {
            val storedTheme by app.deviceStore.themeFlow.collectAsState(initial = "system")
            val darkTheme = when (storedTheme) {
                "light" -> false
                "dark" -> true
                else -> isSystemInDarkTheme()
            }

            LifeOSTheme(darkTheme = darkTheme) {
                Surface(modifier = Modifier.fillMaxSize(), color = LocalLifeOSColors.current.bgPrimary) {
                    LifeOSNavHost(app = app)
                }
            }
        }
    }
}
