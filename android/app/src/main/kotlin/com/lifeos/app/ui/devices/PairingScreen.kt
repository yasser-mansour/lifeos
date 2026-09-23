package com.lifeos.app.ui.devices

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.google.mlkit.vision.barcode.BarcodeScanner
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import com.lifeos.app.ui.components.PrimaryButton
import com.lifeos.app.ui.theme.LocalLifeOSColors

@Composable
fun PairingScreen(viewModel: DevicesViewModel, onPaired: () -> Unit, onEnterManually: () -> Unit = {}) {
    val context = LocalContext.current
    val colors = LocalLifeOSColors.current
    val pairingState by viewModel.pairingState.collectAsState()
    val screenState by viewModel.screenState.collectAsState()
    var hasCameraPermission by remember {
        mutableStateOf(ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED)
    }

    if (pairingState is PairingUiState.Success) {
        PairingSuccessScreen(macName = screenState.macName, onContinue = onPaired)
        return
    }

    if (!hasCameraPermission) {
        CameraPermissionRequest(onGranted = { hasCameraPermission = true })
        return
    }

    Box(modifier = Modifier.fillMaxSize()) {
        QrScannerPreview(enabled = pairingState is PairingUiState.Idle, onQrCodeScanned = viewModel::onQrCodeScanned)

        Column(modifier = Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Bottom) {
            when (val state = pairingState) {
                is PairingUiState.Pairing -> Row(verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(color = colors.accent)
                    Text("  Pairing…", color = Color.White, modifier = Modifier.padding(start = 8.dp))
                }
                is PairingUiState.Error -> Column {
                    Text(state.message, color = Color.White, style = MaterialTheme.typography.bodyMedium)
                    PrimaryButton(text = "Try Again", onClick = viewModel::resetPairingState, modifier = Modifier.padding(top = 8.dp))
                }
                else -> Column {
                    Text(
                        "Point your camera at the pairing code shown on your Mac.",
                        color = Color.White, style = MaterialTheme.typography.bodyMedium,
                    )
                    androidx.compose.material3.TextButton(onClick = onEnterManually) {
                        Text("Can't scan? Enter manually", color = Color.White)
                    }
                }
            }
        }
    }
}

@Composable
private fun CameraPermissionRequest(onGranted: () -> Unit) {
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) onGranted()
    }
    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text("LIFEOS needs camera access to scan the pairing code.", style = MaterialTheme.typography.bodyLarge)
        PrimaryButton(text = "Allow Camera", onClick = { launcher.launch(Manifest.permission.CAMERA) }, modifier = Modifier.padding(top = 16.dp))
    }
}

@Composable
private fun QrScannerPreview(enabled: Boolean, onQrCodeScanned: (String) -> Unit) {
    val lifecycleOwner = LocalLifecycleOwner.current
    val scanner = remember { BarcodeScanning.getClient() }

    AndroidView(
        modifier = Modifier.fillMaxSize(),
        factory = { ctx ->
            val previewView = PreviewView(ctx)
            val cameraProviderFuture = ProcessCameraProvider.getInstance(ctx)
            cameraProviderFuture.addListener({
                val cameraProvider = cameraProviderFuture.get()
                val preview = Preview.Builder().build().also { it.setSurfaceProvider(previewView.surfaceProvider) }

                val analysis = ImageAnalysis.Builder().setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST).build()
                analysis.setAnalyzer(ContextCompat.getMainExecutor(ctx)) { imageProxy ->
                    if (enabled) {
                        processImageProxy(scanner, imageProxy, onQrCodeScanned)
                    } else {
                        imageProxy.close()
                    }
                }

                try {
                    cameraProvider.unbindAll()
                    cameraProvider.bindToLifecycle(lifecycleOwner, CameraSelector.DEFAULT_BACK_CAMERA, preview, analysis)
                } catch (e: Exception) {
                    // Camera unavailable (e.g. emulator without camera support) — pairing
                    // simply stays unavailable and the user can retry from Devices.
                }
            }, ContextCompat.getMainExecutor(ctx))
            previewView
        },
    )

    DisposableEffect(Unit) {
        onDispose { scanner.close() }
    }
}

@androidx.annotation.OptIn(androidx.camera.core.ExperimentalGetImage::class)
private fun processImageProxy(scanner: BarcodeScanner, imageProxy: ImageProxy, onQrCodeScanned: (String) -> Unit) {
    val mediaImage = imageProxy.image
    if (mediaImage == null) {
        imageProxy.close()
        return
    }
    val image = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)
    scanner.process(image)
        .addOnSuccessListener { barcodes ->
            barcodes.firstOrNull { it.rawValue != null }?.rawValue?.let(onQrCodeScanned)
        }
        .addOnCompleteListener { imageProxy.close() }
}
