package com.lifeos.app.study

import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import com.lifeos.app.LifeOSApplication
import com.lifeos.app.MainActivity
import com.lifeos.app.R
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * Keeps the focus-session notification alive and current while the app is
 * backgrounded or the screen is off (spec §56/§57). This service does NOT
 * own timing truth — Room's event log does (see StudyTimerEngine). If
 * Android kills this service under memory pressure, no time is lost: the
 * next tick after restart (or the next app launch) recomputes duration by
 * replaying events, exactly like a fresh page load on the backend.
 */
class StudyTimerService : Service() {
    private var job: Job? = null
    private val scope = CoroutineScope(Dispatchers.Default)

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val sessionId = intent?.getStringExtra(EXTRA_SESSION_ID)
        when (intent?.action) {
            ACTION_PAUSE -> { handlePause(sessionId); return START_STICKY }
            ACTION_RESUME_FROM_NOTIFICATION -> { handleResume(sessionId); return START_STICKY }
            ACTION_FINISH -> { handleFinish(sessionId); return START_STICKY }
            ACTION_STOP_SERVICE -> { stopSelf(); return START_NOT_STICKY }
        }

        if (sessionId == null) {
            stopSelf()
            return START_NOT_STICKY
        }

        startForegroundWithNotification(sessionId, "Starting…")
        observeAndTick(sessionId)
        return START_STICKY
    }

    private fun observeAndTick(sessionId: String) {
        job?.cancel()
        job = scope.launch {
            val app = application as LifeOSApplication
            while (true) {
                val session = app.studyRepository.getById(sessionId)
                if (session == null || session.status !in listOf("active", "paused")) {
                    stopSelf()
                    return@launch
                }
                val duration = app.studyRepository.durationSecondsFor(sessionId, System.currentTimeMillis())
                val label = formatClock(duration) + if (session.status == "paused") " · Paused" else ""
                updateNotification(sessionId, session.courseName ?: "Focus session", label, session.status == "paused")
                delay(1000)
            }
        }
    }

    private fun handlePause(sessionId: String?) {
        if (sessionId == null) return
        scope.launch {
            (application as LifeOSApplication).studyRepository.pauseSession(sessionId)
        }
    }

    private fun handleResume(sessionId: String?) {
        if (sessionId == null) return
        scope.launch {
            (application as LifeOSApplication).studyRepository.resumeSession(sessionId)
        }
    }

    private fun handleFinish(sessionId: String?) {
        if (sessionId == null) return
        scope.launch {
            (application as LifeOSApplication).studyRepository.finishSession(sessionId)
            stopSelf()
        }
    }

    private fun startForegroundWithNotification(sessionId: String, initialText: String) {
        val notification = buildNotification(sessionId, "Focus session", initialText, isPaused = false)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ServiceCompat.startForeground(this, NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun updateNotification(sessionId: String, title: String, text: String, isPaused: Boolean) {
        val notification = buildNotification(sessionId, title, text, isPaused)
        getSystemService(android.app.NotificationManager::class.java)?.notify(NOTIFICATION_ID, notification)
    }

    private fun buildNotification(sessionId: String, title: String, text: String, isPaused: Boolean): android.app.Notification {
        val contentIntent = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val pauseOrResumeAction = NotificationCompat.Action(
            0, if (isPaused) "Resume" else "Pause",
            serviceActionIntent(if (isPaused) ACTION_RESUME_FROM_NOTIFICATION else ACTION_PAUSE, sessionId, requestCode = 1),
        )
        val finishAction = NotificationCompat.Action(
            0, "Finish", serviceActionIntent(ACTION_FINISH, sessionId, requestCode = 2),
        )

        return NotificationCompat.Builder(this, LifeOSApplication.STUDY_CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification_timer)
            .setContentTitle(title)
            .setContentText(text)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setContentIntent(contentIntent)
            .addAction(pauseOrResumeAction)
            .addAction(finishAction)
            .build()
    }

    private fun serviceActionIntent(action: String, sessionId: String, requestCode: Int): PendingIntent {
        val intent = Intent(this, StudyTimerService::class.java).apply {
            this.action = action
            putExtra(EXTRA_SESSION_ID, sessionId)
        }
        return PendingIntent.getService(this, requestCode, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
    }

    override fun onDestroy() {
        job?.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        const val EXTRA_SESSION_ID = "session_id"
        const val ACTION_PAUSE = "com.lifeos.app.action.PAUSE"
        const val ACTION_RESUME_FROM_NOTIFICATION = "com.lifeos.app.action.RESUME"
        const val ACTION_FINISH = "com.lifeos.app.action.FINISH"
        const val ACTION_STOP_SERVICE = "com.lifeos.app.action.STOP_SERVICE"
        private const val NOTIFICATION_ID = 4201

        fun start(context: android.content.Context, sessionId: String) {
            val intent = Intent(context, StudyTimerService::class.java).putExtra(EXTRA_SESSION_ID, sessionId)
            context.startForegroundService(intent)
        }

        fun stop(context: android.content.Context) {
            context.startService(Intent(context, StudyTimerService::class.java).apply { action = ACTION_STOP_SERVICE })
        }
    }
}

private fun formatClock(totalSeconds: Long): String {
    val h = totalSeconds / 3600
    val m = (totalSeconds % 3600) / 60
    val s = totalSeconds % 60
    return if (h > 0) "%d:%02d:%02d".format(h, m, s) else "%d:%02d".format(m, s)
}
