package dev.luna.lightstudio

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RadialGradient
import android.graphics.Shader
import android.graphics.SweepGradient
import android.view.MotionEvent
import android.view.View
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * A touch-sensitive HSV hue/saturation wheel. This is a genuine custom Android
 * view, not a bitmap or a simulated colour picker. Brightness is controlled by
 * the separate hardware brightness slider, just like desktop LUNA.
 *
 * The callback reports live previews while dragging and a final value on UP.
 * Only the final value should be transmitted to the BLE controller.
 */
class ColourWheelView(context: Context) : View(context) {
    var onColourChanged: ((hue: Float, saturation: Float, finished: Boolean) -> Unit)? = null

    private var hue = 260f
    private var saturation = 0.65f
    private var accent = Color.rgb(149, 104, 255)
    private var cx = 0f
    private var cy = 0f
    private var radius = 0f
    private val wheel = Paint(Paint.ANTI_ALIAS_FLAG)
    private val whiteOverlay = Paint(Paint.ANTI_ALIAS_FLAG)
    private val ring = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
    }
    private val thumb = Paint(Paint.ANTI_ALIAS_FLAG)

    init {
        contentDescription = "Colour wheel: drag to select hue and saturation"
        isClickable = true
        setLayerType(View.LAYER_TYPE_SOFTWARE, null)
    }

    fun setSelection(hue: Float, saturation: Float) {
        this.hue = ((hue % 360f) + 360f) % 360f
        this.saturation = saturation.coerceIn(0f, 1f)
        invalidate()
    }

    fun setAccent(colour: Int) {
        accent = colour
        invalidate()
    }

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        super.onSizeChanged(w, h, oldw, oldh)
        cx = w / 2f
        cy = h / 2f
        radius = min(w, h) * 0.415f
        wheel.shader = SweepGradient(cx, cy, intArrayOf(
            Color.RED, Color.YELLOW, Color.GREEN, Color.CYAN,
            Color.BLUE, Color.MAGENTA, Color.RED
        ), null)
        whiteOverlay.shader = RadialGradient(cx, cy, radius,
            intArrayOf(Color.WHITE, Color.TRANSPARENT),
            floatArrayOf(0f, 1f), Shader.TileMode.CLAMP)
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (radius <= 0f) return

        // Subtle outer halo and rim, matching LUNA's desktop GlowOrb.
        thumb.color = Color.argb(24, Color.red(accent), Color.green(accent), Color.blue(accent))
        canvas.drawCircle(cx, cy, radius * 1.095f, thumb)
        canvas.drawCircle(cx, cy, radius, wheel)
        canvas.drawCircle(cx, cy, radius, whiteOverlay)
        ring.color = Color.argb(58, 255, 255, 255)
        ring.strokeWidth = resources.displayMetrics.density * 1.5f
        canvas.drawCircle(cx, cy, radius, ring)

        val radians = Math.toRadians(hue.toDouble())
        val px = cx + (radius * saturation * cos(radians)).toFloat()
        val py = cy + (radius * saturation * sin(radians)).toFloat()
        val dotRadius = resources.displayMetrics.density * 11f
        thumb.shader = null
        thumb.color = Color.BLACK
        thumb.setShadowLayer(resources.displayMetrics.density * 6f, 0f, 0f, Color.argb(110, 0, 0, 0))
        canvas.drawCircle(px, py, dotRadius + resources.displayMetrics.density * 2f, thumb)
        thumb.clearShadowLayer()
        thumb.color = Color.WHITE
        canvas.drawCircle(px, py, dotRadius, thumb)
        thumb.color = Color.HSVToColor(floatArrayOf(hue, saturation, 1f))
        canvas.drawCircle(px, py, dotRadius - resources.displayMetrics.density * 3f, thumb)
    }

    // The surrounding page is a ScrollView. Once a drag begins on the wheel,
    // keep the entire gesture here rather than allowing the page to intercept it.
    private var activePointerId = MotionEvent.INVALID_POINTER_ID

    private fun releaseWheelGesture() {
        activePointerId = MotionEvent.INVALID_POINTER_ID
        parent?.requestDisallowInterceptTouchEvent(false)
    }

    private fun updateFromTouch(event: MotionEvent, pointerIndex: Int, finished: Boolean) {
        val dx = event.getX(pointerIndex) - cx
        val dy = event.getY(pointerIndex) - cy
        val distance = sqrt(dx * dx + dy * dy)
        hue = ((Math.toDegrees(atan2(dy.toDouble(), dx.toDouble())).toFloat() + 360f) % 360f)
        saturation = (distance / radius).coerceIn(0f, 1f)
        invalidate()
        onColourChanged?.invoke(hue, saturation, finished)
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                if (radius <= 0f) return false
                val dx = event.x - cx
                val dy = event.y - cy
                // Outside the actual wheel, let the page scroll normally.
                if (sqrt(dx * dx + dy * dy) > radius * 1.10f) return false
                activePointerId = event.getPointerId(0)
                parent?.requestDisallowInterceptTouchEvent(true)
                updateFromTouch(event, 0, false)
                return true
            }
            MotionEvent.ACTION_MOVE -> {
                if (activePointerId == MotionEvent.INVALID_POINTER_ID) return false
                val pointerIndex = event.findPointerIndex(activePointerId)
                if (pointerIndex < 0) {
                    releaseWheelGesture()
                    return true
                }
                updateFromTouch(event, pointerIndex, false)
                return true
            }
            MotionEvent.ACTION_POINTER_DOWN -> {
                // Ignore extra fingers: the first finger keeps control of the wheel.
                return activePointerId != MotionEvent.INVALID_POINTER_ID
            }
            MotionEvent.ACTION_POINTER_UP -> {
                if (activePointerId == MotionEvent.INVALID_POINTER_ID) return false
                if (event.getPointerId(event.actionIndex) == activePointerId) {
                    val pointerIndex = event.actionIndex
                    releaseWheelGesture()
                    updateFromTouch(event, pointerIndex, true)
                    performClick()
                }
                return true
            }
            MotionEvent.ACTION_UP -> {
                if (activePointerId == MotionEvent.INVALID_POINTER_ID) return false
                val pointerIndex = event.findPointerIndex(activePointerId)
                releaseWheelGesture()
                if (pointerIndex >= 0) {
                    updateFromTouch(event, pointerIndex, true)
                    performClick()
                }
                return true
            }
            MotionEvent.ACTION_CANCEL -> {
                // A cancelled drag must not send a final colour command.
                releaseWheelGesture()
                return true
            }
        }
        return super.onTouchEvent(event)
    }

    override fun onDetachedFromWindow() {
        releaseWheelGesture()
        super.onDetachedFromWindow()
    }

    override fun performClick(): Boolean {
        super.performClick()
        return true
    }
}
