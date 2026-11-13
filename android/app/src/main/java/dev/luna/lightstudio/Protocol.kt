package dev.luna.lightstudio

import java.time.LocalDateTime
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/** Same wire formats as LUNA v0.5.1's mrstar/protocol.py. No BLE side effects. */
object Protocol {
    private fun packet(vararg data: Int): ByteArray = data.map { it.toByte() }.toByteArray()

    fun power(on: Boolean): ByteArray = packet(0xBC, 0x01, 0x01, if (on) 1 else 0, 0x55)

    fun colour(hex: String, microphone: Boolean = false): ByteArray {
        val clean = hex.trim().removePrefix("#")
        require(Regex("[0-9a-fA-F]{6}").matches(clean)) { "Use a six-digit HEX colour" }
        val r = clean.substring(0, 2).toInt(16) / 255.0
        val g = clean.substring(2, 4).toInt(16) / 255.0
        val b = clean.substring(4, 6).toInt(16) / 255.0
        val maximum = max(r, max(g, b))
        val minimum = min(r, min(g, b))
        val delta = maximum - minimum
        val saturation = if (maximum == 0.0) 0.0 else delta / maximum
        val hue = when {
            delta == 0.0 -> 0.0
            maximum == r -> 60.0 * (((g - b) / delta) % 6.0)
            maximum == g -> 60.0 * (((b - r) / delta) + 2.0)
            else -> 60.0 * (((r - g) / delta) + 4.0)
        }
        val h = (((hue + 360.0) % 360.0).roundToInt()) % 360
        val s = (saturation * 1000.0).roundToInt()
        return packet(0xBC, if (microphone) 0x09 else 0x04, 0x06,
            h shr 8, h and 255, s shr 8, s and 255, 0, 0, 0x55)
    }

    fun brightness(value: Int): ByteArray {
        val n = value.coerceIn(0, 1000)
        return packet(0xBC, 0x05, 0x06, n shr 8, n and 255, 0, 0, 0, 0, 0x55)
    }

    fun pixelCount(value: Int): ByteArray {
        val n = value.coerceIn(8, 300)
        return packet(0xBC, 0x03, 0x02, n shr 8, n and 255, 0x55)
    }

    fun channelOrder(index: Int): ByteArray {
        require(index in 0..5)
        return packet(0xBC, 0x02, 0x01, index + 1, 0x55)
    }

    fun effect(id: Int): ByteArray {
        require(id in 1..65534)
        // Decompiled Mr Star ModeFragment uses divisor 255 (not 256).
        return packet(0xBC, 0x06, 0x02, id / 255, id % 255, 0x55)
    }

    fun effectSpeed(speed: Int): ByteArray = packet(0xBC, 0x08, 0x01, speed.coerceIn(1, 100), 0x55)
    fun effectDirection(forward: Boolean): ByteArray = packet(0xBC, 0x07, 0x01, if (forward) 0 else 1, 0x55)
    fun microphoneSource(deviceMicrophone: Boolean): ByteArray = packet(0xBC, 0x0F, 0x01, if (deviceMicrophone) 1 else 0, 0x55)
    fun microphoneMode(modeIndex: Int): ByteArray = packet(0xBC, 0x11, 0x01, modeIndex.coerceIn(0, 3) + 1, 0x55)
    fun microphoneSensitivity(value: Int): ByteArray = packet(0xBC, 0x12, 0x01, value.coerceIn(0, 100), 0x55)

    fun clock(now: LocalDateTime = LocalDateTime.now()): ByteArray = packet(
        0xBC, 0x0B, 0x07, now.year shr 8, now.year and 255,
        now.monthValue, now.dayOfMonth, now.hour, now.minute, now.second,
        0x55, now.dayOfWeek.value
    )

    fun timer(on: Boolean, enabled: Boolean, days: List<Boolean>, hour: Int, minute: Int): ByteArray {
        require(days.size == 7 && hour in 0..23 && minute in 0..59)
        var mask = 0
        days.forEachIndexed { i, selected -> if (selected) mask = mask or (1 shl i) }
        if (!enabled) mask = mask or 0x80
        return packet(0xBC, 0x0D, 0x06, 0x01, if (on) 1 else 0,
            if (enabled) 1 else 0, mask, hour, minute, 0x55)
    }
}
