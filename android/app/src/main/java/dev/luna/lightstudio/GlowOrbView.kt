package dev.luna.lightstudio

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.RadialGradient
import android.graphics.Shader
import android.view.View
import kotlin.math.min

/** Android counterpart to the desktop LUNA GlowOrb. */
class GlowOrbView(context: Context) : View(context) {
    private var colour = Color.rgb(149, 104, 255)
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)

    fun setColour(hex: String) {
        colour = try { Color.parseColor(hex) } catch (_: IllegalArgumentException) { colour }
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val cx = width / 2f
        val cy = height / 2f
        val radius = min(width, height) * 0.285f
        if (radius <= 0f) return
        val halo = radius * 1.78f
        paint.shader = RadialGradient(cx, cy, halo,
            intArrayOf(withAlpha(colour, 82), withAlpha(colour, 31), Color.TRANSPARENT),
            floatArrayOf(0f, 0.45f, 1f), Shader.TileMode.CLAMP)
        canvas.drawCircle(cx, cy, halo, paint)
        paint.shader = LinearGradient(cx - radius, cy - radius,
            cx + radius, cy + radius,
            intArrayOf(lighten(colour, 0.55f), colour, darken(colour, 0.40f)),
            floatArrayOf(0f, 0.58f, 1f), Shader.TileMode.CLAMP)
        canvas.drawCircle(cx, cy, radius, paint)
        paint.shader = null
        paint.color = Color.argb(72, 255, 255, 255)
        paint.style = Paint.Style.STROKE
        paint.strokeWidth = resources.displayMetrics.density * 1.5f
        canvas.drawCircle(cx, cy, radius, paint)
        paint.style = Paint.Style.FILL
        paint.color = Color.argb(47, 255, 255, 255)
        canvas.drawOval(cx - radius * .48f, cy - radius * .62f,
            cx - radius * .03f, cy - radius * .32f, paint)
    }

    private fun withAlpha(c: Int, a: Int): Int = Color.argb(a, Color.red(c), Color.green(c), Color.blue(c))
    private fun lighten(c: Int, factor: Float): Int = Color.rgb(
        (Color.red(c) + (255 - Color.red(c)) * factor).toInt(),
        (Color.green(c) + (255 - Color.green(c)) * factor).toInt(),
        (Color.blue(c) + (255 - Color.blue(c)) * factor).toInt())
    private fun darken(c: Int, factor: Float): Int = Color.rgb(
        (Color.red(c) * (1f - factor)).toInt(),
        (Color.green(c) * (1f - factor)).toInt(),
        (Color.blue(c) * (1f - factor)).toInt())
}
