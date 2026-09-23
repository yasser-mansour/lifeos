package com.lifeos.app.ui.devices

import android.os.Build
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.gson.Gson
import com.lifeos.app.LifeOSApplication
import com.lifeos.app.data.prefs.DeviceStore
import com.lifeos.app.data.remote.ClaimDeviceRequest
import com.lifeos.app.data.remote.NetworkModule
import com.lifeos.app.sync.SyncScheduler
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class PairingQrPayload(val lifeos_pairing: Int, val token: String, val host: String, val port: Int)

sealed class PairingUiState {
    data object Idle : PairingUiState()
    data object Pairing : PairingUiState()
    data object Success : PairingUiState()
    data class Error(val message: String) : PairingUiState()
}

/** What "connected to the Mac" means for the Devices screen (spec §49) — a
 * live health-check from this phone right now, not a possibly-stale
 * server-side "last seen" flag (which updates on ANY device's request). */
sealed class ConnectionState {
    data object Checking : ConnectionState()
    data object Online : ConnectionState()
    data object Unreachable : ConnectionState()
}

data class DeviceScreenState(
    val isPaired: Boolean = false,
    val macName: String = "your Mac",
    val connection: ConnectionState = ConnectionState.Checking,
    val lastSyncAtEpochMs: Long? = null,
    val lastSyncError: String? = null,
    val pendingCount: Int = 0,
)

class DevicesViewModel(private val deviceStore: DeviceStore, private val app: LifeOSApplication) : ViewModel() {
    private val gson = Gson()

    val isPaired: StateFlow<Boolean> = deviceStore.isPairedFlow
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), false)

    private val _connection = MutableStateFlow<ConnectionState>(ConnectionState.Checking)
    private val _macName = MutableStateFlow("your Mac")

    private data class SyncPart(val lastSyncAtEpochMs: Long?, val lastSyncError: String?, val pendingCount: Int)

    private val syncPart = combine(
        deviceStore.lastSyncAtEpochMsFlow, deviceStore.lastSyncErrorFlow, app.database.syncQueueDao().observePendingCount(),
    ) { lastSync, error, pending -> SyncPart(lastSync, error, pending) }

    val screenState: StateFlow<DeviceScreenState> = combine(
        deviceStore.isPairedFlow, _connection, _macName, syncPart,
    ) { isPaired, connection, macName, sync ->
        DeviceScreenState(
            isPaired = isPaired, connection = connection, macName = macName,
            lastSyncAtEpochMs = sync.lastSyncAtEpochMs, lastSyncError = sync.lastSyncError, pendingCount = sync.pendingCount,
        )
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), DeviceScreenState())

    private val _pairingState = MutableStateFlow<PairingUiState>(PairingUiState.Idle)
    val pairingState: StateFlow<PairingUiState> = _pairingState

    private var isClaiming = false

    init {
        refreshConnection()
    }

    /** A real request against the stored base URL — the only trustworthy
     * answer to "can this phone reach the Mac right now". */
    fun refreshConnection() {
        viewModelScope.launch {
            if (deviceStore.currentToken().isNullOrBlank()) return@launch
            _connection.value = ConnectionState.Checking
            _connection.value = try {
                if (app.api.health().isSuccessful) ConnectionState.Online else ConnectionState.Unreachable
            } catch (e: Exception) {
                ConnectionState.Unreachable
            }
            runCatching {
                val devices = app.api.getDevices().body()?.results.orEmpty()
                devices.firstOrNull { it.platform == "macos" }?.let { _macName.value = it.name }
            }
        }
    }

    fun syncNow() {
        SyncScheduler.syncNow(app)
        refreshConnection()
    }

    suspend fun currentBaseUrl(): String? = deviceStore.currentBaseUrl()
    suspend fun currentDeviceId(): String? = deviceStore.currentDeviceId()
    suspend fun checkServerHealth(): Boolean = runCatching { app.api.health().isSuccessful }.getOrDefault(false)

    fun onQrCodeScanned(rawValue: String) {
        if (isClaiming) return
        val payload = runCatching { gson.fromJson(rawValue, PairingQrPayload::class.java) }.getOrNull()
        if (payload == null || payload.lifeos_pairing != 1) return

        isClaiming = true
        _pairingState.value = PairingUiState.Pairing
        viewModelScope.launch {
            try {
                val baseUrl = "http://${payload.host}:${payload.port}/"
                // Temporarily point the store at the candidate Mac before the
                // claim call, since NetworkModule reads the base URL from it.
                deviceStore.savePairing(baseUrl, deviceId = "", deviceToken = "", deviceName = "")
                val api = NetworkModule.create(deviceStore)
                val response = api.claimDevice(
                    ClaimDeviceRequest(
                        pairingToken = payload.token,
                        deviceName = Build.MODEL ?: "Android Device",
                        model = Build.MODEL ?: "unknown",
                        appVersion = "0.1.0",
                    )
                )
                val body = response.body()
                if (response.isSuccessful && body != null) {
                    deviceStore.savePairing(baseUrl, body.deviceId, body.deviceToken, Build.MODEL ?: "Android Device")
                    SyncScheduler.syncNow(app)
                    _pairingState.value = PairingUiState.Success
                    refreshConnection()
                } else {
                    deviceStore.clearPairing()
                    _pairingState.value = PairingUiState.Error("This pairing code is invalid or has expired.")
                }
            } catch (e: Exception) {
                deviceStore.clearPairing()
                _pairingState.value = PairingUiState.Error("Couldn't reach the Mac. Make sure both devices are on the same network.")
            } finally {
                isClaiming = false
            }
        }
    }

    /** Fallback for when the camera can't scan the QR (spec §73: "provide
     * fallback manual IP/endpoint if discovery fails") — same claim flow as
     * [onQrCodeScanned], just built from typed host/port/code instead of a
     * decoded QR payload. Health-checks the candidate Mac first so a typo'd
     * address fails fast with a clear message rather than a raw network error. */
    fun onManualPairSubmitted(host: String, port: String, code: String) {
        if (isClaiming) return
        val trimmedHost = host.trim()
        val trimmedCode = code.trim()
        val portNumber = port.trim().toIntOrNull()
        if (trimmedHost.isEmpty() || trimmedCode.isEmpty() || portNumber == null) {
            _pairingState.value = PairingUiState.Error("Enter a host, port, and code.")
            return
        }

        isClaiming = true
        _pairingState.value = PairingUiState.Pairing
        viewModelScope.launch {
            try {
                val baseUrl = "http://$trimmedHost:$portNumber/"
                deviceStore.savePairing(baseUrl, deviceId = "", deviceToken = "", deviceName = "")
                val api = NetworkModule.create(deviceStore)

                val healthResponse = api.health()
                if (!healthResponse.isSuccessful) {
                    deviceStore.clearPairing()
                    _pairingState.value = PairingUiState.Error("Couldn't reach LIFEOS at $trimmedHost:$portNumber. Check the address and that both devices are on the same network.")
                    return@launch
                }

                val response = api.claimDevice(
                    ClaimDeviceRequest(
                        pairingToken = trimmedCode,
                        deviceName = Build.MODEL ?: "Android Device",
                        model = Build.MODEL ?: "unknown",
                        appVersion = "0.1.0",
                    )
                )
                val body = response.body()
                if (response.isSuccessful && body != null) {
                    deviceStore.savePairing(baseUrl, body.deviceId, body.deviceToken, Build.MODEL ?: "Android Device")
                    SyncScheduler.syncNow(app)
                    _pairingState.value = PairingUiState.Success
                    refreshConnection()
                } else {
                    deviceStore.clearPairing()
                    _pairingState.value = PairingUiState.Error("This code is invalid or has expired.")
                }
            } catch (e: Exception) {
                deviceStore.clearPairing()
                _pairingState.value = PairingUiState.Error("Couldn't reach the Mac. Make sure both devices are on the same network.")
            } finally {
                isClaiming = false
            }
        }
    }

    fun resetPairingState() {
        _pairingState.value = PairingUiState.Idle
    }

    fun unpair() {
        viewModelScope.launch { deviceStore.clearPairing() }
    }
}
