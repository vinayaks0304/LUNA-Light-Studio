package dev.luna.lightstudio

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.bluetooth.BluetoothStatusCodes
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Context
import android.os.Build
import android.os.Handler
import android.os.Looper
import java.util.ArrayDeque
import java.util.UUID

/** A single BLE connection with serialised, acknowledged GATT writes.
 *  Does not write any saved settings on connection. */
class LedBluetooth(
    private val context: Context,
    private val onStatus: (String) -> Unit,
    private val onConnected: (Boolean) -> Unit
) {
    private val main = Handler(Looper.getMainLooper())
    private val manager = context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
    private val adapter: BluetoothAdapter? get() = manager.adapter
    private val serviceUuid = UUID.fromString("0000fff0-0000-1000-8000-00805f9b34fb")
    private val writeUuid = UUID.fromString("0000fff3-0000-1000-8000-00805f9b34fb")
    private val queue = ArrayDeque<ByteArray>()
    private var scanning = false
    private var gatt: BluetoothGatt? = null
    private var writeCharacteristic: BluetoothGattCharacteristic? = null
    private var writing = false
    var isConnected = false
        private set

    private fun status(message: String) = main.post { onStatus(message) }
    private fun connection(value: Boolean) = main.post {
        isConnected = value
        onConnected(value)
    }

    private val timeout = Runnable {
        if (scanning) {
            stopScan()
            status("GATT--DEMO not found. Check power and Bluetooth.")
        }
    }

    private val scanCallback = object : ScanCallback() {
        @SuppressLint("MissingPermission")
        override fun onScanResult(callbackType: Int, result: ScanResult) {
            val device = result.device
            val matches = device.name == "GATT--DEMO" ||
                result.scanRecord?.deviceName == "GATT--DEMO"
            if (!matches || !scanning) return
            stopScan()
            status("Connecting to GATT--DEMO…")
            gatt = device.connectGatt(context, false, callback, BluetoothDevice.TRANSPORT_LE)
        }
        override fun onScanFailed(errorCode: Int) {
            main.post { scanning = false; main.removeCallbacks(timeout) }
            status("Bluetooth scan failed ($errorCode)")
        }
    }

    @SuppressLint("MissingPermission")
    fun connect() {
        main.post {
            if (isConnected || scanning) return@post
            val bluetooth = adapter
            if (bluetooth == null || !bluetooth.isEnabled) {
                status("Enable Bluetooth before connecting")
                return@post
            }
            val scanner = bluetooth.bluetoothLeScanner
            if (scanner == null) { status("Bluetooth LE scanner unavailable"); return@post }
            scanning = true
            status("Searching for GATT--DEMO…")
            scanner.startScan(null, ScanSettings.Builder()
                .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY).build(), scanCallback)
            main.postDelayed(timeout, 12000)
        }
    }

    @SuppressLint("MissingPermission")
    private fun stopScan() {
        if (!scanning) return
        scanning = false
        main.removeCallbacks(timeout)
        try { adapter?.bluetoothLeScanner?.stopScan(scanCallback) } catch (_: Exception) { }
    }

    @SuppressLint("MissingPermission")
    fun disconnect() {
        main.post {
            stopScan()
            queue.clear()
            writing = false
            writeCharacteristic = null
            val old = gatt
            gatt = null
            try { old?.disconnect(); old?.close() } catch (_: Exception) { }
            connection(false)
            status("Disconnected")
        }
    }

    fun send(frame: ByteArray) = sendSequence(listOf(frame))

    fun sendSequence(frames: List<ByteArray>) {
        main.post {
            if (!isConnected || gatt == null || writeCharacteristic == null) {
                status("Connect to your LED strip first")
                return@post
            }
            frames.forEach { queue.add(it.copyOf()) }
            flush()
        }
    }

    @SuppressLint("MissingPermission")
    @Suppress("DEPRECATION")
    private fun flush() {
        if (writing || queue.isEmpty()) return
        val client = gatt ?: return
        val characteristic = writeCharacteristic ?: return
        val frame = queue.removeFirst()
        writing = true
        try {
            // FFF3 supports write-with-response. This serialises writes and avoids
            // the power ON/OFF overlap seen in early desktop LUNA versions.
            val accepted = if (Build.VERSION.SDK_INT >= 33) {
                client.writeCharacteristic(characteristic, frame,
                    BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT) == BluetoothStatusCodes.SUCCESS
            } else {
                characteristic.value = frame
                characteristic.writeType = BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT
                client.writeCharacteristic(characteristic)
            }
            if (!accepted) { writing = false; status("Bluetooth write rejected"); flush() }
        } catch (e: Exception) {
            writing = false
            status("Bluetooth write error: ${e.message}")
        }
    }

    private val callback = object : BluetoothGattCallback() {
        @SuppressLint("MissingPermission")
        override fun onConnectionStateChange(client: BluetoothGatt, statusCode: Int, newState: Int) {
            if (newState == BluetoothProfile.STATE_CONNECTED && statusCode == BluetoothGatt.GATT_SUCCESS) {
                status("Discovering LED controller services…")
                client.discoverServices()
            } else if (newState == BluetoothProfile.STATE_DISCONNECTED || statusCode != BluetoothGatt.GATT_SUCCESS) {
                main.post {
                    if (gatt === client) {
                        gatt = null
                        writeCharacteristic = null
                        queue.clear()
                        writing = false
                        connection(false)
                        status("Disconnected ($statusCode)")
                    }
                    client.close()
                }
            }
        }

        override fun onServicesDiscovered(client: BluetoothGatt, statusCode: Int) {
            main.post {
                if (gatt !== client) return@post
                if (statusCode != BluetoothGatt.GATT_SUCCESS) {
                    status("GATT discovery failed ($statusCode)")
                    return@post
                }
                writeCharacteristic = client.getService(serviceUuid)?.getCharacteristic(writeUuid)
                if (writeCharacteristic == null) {
                    status("FFF3 write characteristic not found")
                    return@post
                }
                connection(true)
                status("Connected to GATT--DEMO")
            }
        }

        override fun onCharacteristicWrite(client: BluetoothGatt,
                                           characteristic: BluetoothGattCharacteristic, statusCode: Int) {
            main.post {
                if (gatt !== client) return@post
                writing = false
                if (statusCode != BluetoothGatt.GATT_SUCCESS)
                    status("LED write failed ($statusCode)")
                flush()
            }
        }
    }
}
