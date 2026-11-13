package dev.luna.lightstudio

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.app.TimePickerDialog
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.SeekBar
import android.widget.Spinner
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast
import org.json.JSONArray
import java.util.Locale

private data class EffectItem(val id: Int, val category: String, val name: String) {
    override fun toString(): String = "$category · $name"
}

/**
 * LUNA Android — native mobile adaptation of the desktop Light Studio.
 * The visual layer is intentionally separate from Protocol and LedBluetooth.
 * All persisted keys and existing BLE commands remain compatible with v0.1.
 */
class MainActivity : Activity() {
    private lateinit var preferences: PaletteStore
    private lateinit var bluetooth: LedBluetooth
    private var selectedHex = "#9568FF"
    private var page = 0
    private var isConnected = false
    private var lastPower = true
    private var connectionMessage = "Not connected"
    private var accent = Color.rgb(149, 104, 255)
    private var background = Color.rgb(13, 17, 28)
    private var panel = Color.rgb(26, 31, 45)
    private var raised = Color.rgb(37, 43, 61)
    private var outline = Color.rgb(53, 61, 80)
    private val textColour = Color.rgb(245, 246, 252)
    private val muted = Color.rgb(166, 176, 196)
    private var effects: List<EffectItem> = emptyList()
    private val pages = listOf("Home", "Colours", "Effects", "Mic", "Timer", "Settings", "Music", "More")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        preferences = PaletteStore(this)
        selectedHex = PaletteStore.canonicalHex(preferences.string("colour", "#9568FF")) ?: "#9568FF"
        effects = loadEffects()
        bluetooth = LedBluetooth(this,
            onStatus = { message -> connectionMessage = message; showStatus() },
            onConnected = { value -> isConnected = value; render() })
        page = savedInstanceState?.getInt("luna_page") ?: 0
        render()
    }

    override fun onSaveInstanceState(outState: Bundle) {
        outState.putInt("luna_page", page)
        super.onSaveInstanceState(outState)
    }

    override fun onDestroy() {
        bluetooth.disconnect()
        super.onDestroy()
    }

    private fun loadEffects(): List<EffectItem> {
        return try {
            val json = assets.open("effects.json").bufferedReader().use { it.readText() }
            val array = JSONArray(json)
            (0 until array.length()).map { i ->
                val item = array.getJSONObject(i)
                EffectItem(item.getInt("id"), item.getString("category"), item.getString("name"))
            }
        } catch (_: Exception) { emptyList() }
    }

    private fun requiredPermissions(): Array<String> = if (Build.VERSION.SDK_INT >= 31) {
        arrayOf(Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_CONNECT)
    } else {
        arrayOf(Manifest.permission.ACCESS_FINE_LOCATION)
    }

    private fun connect() {
        if (isConnected) { bluetooth.disconnect(); return }
        val missing = requiredPermissions().filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }
        if (missing.isNotEmpty()) requestPermissions(missing.toTypedArray(), 42)
        else bluetooth.connect()
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 42) {
            if (grantResults.isNotEmpty() && grantResults.all { it == PackageManager.PERMISSION_GRANTED })
                bluetooth.connect()
            else toast("Bluetooth permissions are required to connect")
        }
    }

    private fun toast(message: String) = Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
    private fun showStatus() {
        findViewById<TextView>(777)?.apply {
            text = connectionMessage
            setTextColor(if (isConnected) accent else muted)
        }
    }

    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()

    private fun blend(a: Int, b: Int, amount: Float): Int {
        val t = amount.coerceIn(0f, 1f)
        return Color.rgb(
            (Color.red(a) * (1f - t) + Color.red(b) * t).toInt(),
            (Color.green(a) * (1f - t) + Color.green(b) * t).toInt(),
            (Color.blue(a) * (1f - t) + Color.blue(b) * t).toInt())
    }

    private fun shape(colour: Int, radius: Int = 18, stroke: Int? = null): GradientDrawable =
        GradientDrawable().apply {
            setColor(colour)
            cornerRadius = dp(radius).toFloat()
            if (stroke != null) setStroke(dp(1), stroke)
        }

    private fun contrastAccent(hex: String): Int {
        val hsv = FloatArray(3)
        Color.colorToHSV(Color.parseColor(hex), hsv)
        if (hsv[1] < 0.10f) {
            // White, grey and black should yield a neutral accent, not red/purple.
            hsv[0] = 216f
            hsv[1] = 0.03f
            hsv[2] = (0.72f + hsv[2] * 0.22f).coerceIn(0.72f, 0.94f)
        } else {
            hsv[1] = (hsv[1] * 0.88f).coerceIn(0.48f, 0.89f)
            hsv[2] = (hsv[2] * 0.83f + 0.23f).coerceIn(0.72f, 0.96f)
        }
        val adjusted = Color.HSVToColor(hsv)
        return if (hsv[0] in 205f..255f && hsv[1] > 0.5f) blend(adjusted, Color.WHITE, 0.14f)
        else adjusted
    }

    private fun updatePalette() {
        val raw = Color.parseColor(selectedHex)
        accent = contrastAccent(selectedHex)
        background = blend(Color.rgb(12, 16, 26), raw, .055f)
        panel = blend(Color.rgb(25, 30, 43), raw, .075f)
        raised = blend(Color.rgb(40, 46, 63), raw, .095f)
        outline = blend(Color.rgb(63, 70, 91), raw, .13f)
    }

    private fun label(value: String, size: Float = 15f, colour: Int = textColour, bold: Boolean = false): TextView =
        TextView(this).apply {
            text = value
            textSize = size
            setTextColor(colour)
            if (bold) typeface = Typeface.create("sans-serif-medium", Typeface.BOLD)
            setPadding(0, dp(3), 0, dp(5))
        }

    private fun eyebrow(value: String) = label(value.uppercase(Locale.ROOT), 10f, accent, true).apply {
        letterSpacing = .17f
    }

    private fun column(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
    }

    private fun row(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.HORIZONTAL
        gravity = Gravity.CENTER_VERTICAL
        layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
    }

    private fun gap(parent: LinearLayout, height: Int = 12) {
        parent.addView(View(this), LinearLayout.LayoutParams(1, dp(height)))
    }

    private fun card(parent: LinearLayout, heading: String, description: String? = null): LinearLayout {
        val box = column().apply {
            background = shape(panel, 22, outline)
            setPadding(dp(19), dp(17), dp(19), dp(19))
            layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                bottomMargin = dp(14)
            }
        }
        box.addView(label(heading, 19f, textColour, true))
        if (description != null) box.addView(label(description, 12.5f, muted))
        parent.addView(box)
        return box
    }

    private fun button(title: String, filled: Boolean = true, onClick: () -> Unit): Button =
        Button(this).apply {
            text = title
            isAllCaps = false
            setTextColor(if (filled) Color.rgb(15, 18, 27) else textColour)
            textSize = 13.5f
            typeface = Typeface.create("sans-serif-medium", Typeface.BOLD)
            backgroundTintList = null
            stateListAnimator = null
            background = shape(if (filled) accent else raised, 13, if (filled) null else outline)
            setPadding(dp(12), dp(8), dp(12), dp(8))
            minHeight = dp(45)
            setOnClickListener { onClick() }
        }

    private fun edit(value: String, hint: String = "", numeric: Boolean = false): EditText =
        EditText(this).apply {
            setText(value)
            this.hint = hint
            setSingleLine(true)
            setTextColor(textColour)
            setHintTextColor(muted)
            textSize = 15f
            backgroundTintList = android.content.res.ColorStateList.valueOf(accent)
            if (numeric) inputType = InputType.TYPE_CLASS_NUMBER
        }

    private fun dropdown(values: List<String>, selection: Int = 0): Spinner = Spinner(this).apply {
        val adapter = object : ArrayAdapter<String>(this@MainActivity, android.R.layout.simple_spinner_item, values) {
            override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
                val view = super.getView(position, convertView, parent) as TextView
                view.setTextColor(textColour)
                view.setPadding(dp(12), dp(13), dp(8), dp(13))
                return view
            }
            override fun getDropDownView(position: Int, convertView: View?, parent: ViewGroup): View {
                val view = super.getDropDownView(position, convertView, parent) as TextView
                view.setTextColor(Color.rgb(20, 24, 34))
                view.setPadding(dp(12), dp(12), dp(8), dp(12))
                return view
            }
        }
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        this.adapter = adapter
        background = shape(raised, 13, outline)
        if (values.isNotEmpty()) setSelection(selection.coerceIn(0, values.size - 1))
    }

    private fun slider(value: Int, maximum: Int, changed: (Int) -> Unit): SeekBar = SeekBar(this).apply {
        max = maximum
        progress = value.coerceIn(0, maximum)
        progressTintList = android.content.res.ColorStateList.valueOf(accent)
        thumbTintList = android.content.res.ColorStateList.valueOf(accent)
        setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(bar: SeekBar, value: Int, fromUser: Boolean) {}
            override fun onStartTrackingTouch(bar: SeekBar) {}
            override fun onStopTrackingTouch(bar: SeekBar) { changed(bar.progress) }
        })
    }

    private fun navigate(destination: Int) {
        page = destination
        render()
    }

    private fun render() {
        updatePalette()
        window.statusBarColor = background
        window.navigationBarColor = background
        window.decorView.systemUiVisibility = 0 // light status icons on the dark theme
        val root = column().apply {
            setBackgroundColor(this@MainActivity.background)
            setPadding(dp(17), dp(12), dp(17), dp(9))
        }
        val brand = row()
        val logo = label("◐", 30f, accent, true)
        brand.addView(logo)
        brand.addView(label(" LUNA", 23f, textColour, true), LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        brand.addView(button(if (isConnected) "Disconnect" else "Connect", !isConnected) { connect() })
        root.addView(brand)

        val statusRow = row()
        statusRow.addView(label(if (isConnected) "●" else "○", 15f, if (isConnected) accent else muted))
        statusRow.addView(label("  $connectionMessage", 11.5f, if (isConnected) accent else muted).apply { id = 777 })
        root.addView(statusRow)
        gap(root, 12)
        root.addView(eyebrow("Light control centre"))
        root.addView(label(when (page) {
            0 -> "Welcome to LUNA"
            1 -> "Colour studio"
            2 -> "Light effects"
            3 -> "Microphone modes"
            4 -> "Schedules"
            5 -> "Device settings"
            6 -> "Music & rhythm"
            else -> "More controls"
        }, 25f, textColour, true))
        gap(root, 7)

        val scroll = ScrollView(this).apply {
            isFillViewport = true
            isVerticalScrollBarEnabled = false
            clipToPadding = false
        }
        val body = column().apply { setPadding(0, dp(8), 0, dp(12)) }
        when (page) {
            0 -> home(body)
            1 -> colours(body)
            2 -> effects(body)
            3 -> microphone(body)
            4 -> timers(body)
            5 -> settings(body)
            6 -> music(body)
            else -> more(body)
        }
        scroll.addView(body)
        root.addView(scroll, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
        root.addView(bottomNavigation())
        setContentView(root)
    }

    private fun bottomNavigation(): View {
        val dock = row().apply {
            background = shape(panel, 22, outline)
            setPadding(dp(4), dp(5), dp(4), dp(5))
        }
        val items = listOf(
            Triple(0, "⌂", "Home"),
            Triple(1, "◉", "Colours"),
            Triple(2, "✦", "Effects"),
            Triple(6, "♫", "Music"),
            Triple(7, "☷", "More")
        )
        items.forEach { (index, symbol, title) ->
            val active = page == index || (index == 7 && page in 3..5)
            val item = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                gravity = Gravity.CENTER
                setPadding(0, dp(5), 0, dp(4))
                background = shape(if (active) raised else panel, 16)
                isClickable = true
                isFocusable = true
                contentDescription = "Open $title"
                setOnClickListener { navigate(index) }
            }
            val icon = label(symbol, 22f, if (active) accent else muted)
            icon.gravity = Gravity.CENTER
            item.addView(icon)
            val name = label(title, 10f, if (active) textColour else muted, active)
            name.gravity = Gravity.CENTER
            item.addView(name)
            dock.addView(item, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        }
        return dock
    }

    private fun applyColour(hex: String) {
        val clean = PaletteStore.canonicalHex(hex)
        if (clean == null) { toast("Enter a valid #RRGGBB colour"); return }
        selectedHex = clean
        preferences.set("colour", clean)
        bluetooth.send(Protocol.colour(clean))
        render()
    }

    private fun colourChip(hex: String, size: Int = 30): View = View(this).apply {
        background = shape(Color.parseColor(hex), size / 2)
        layoutParams = LinearLayout.LayoutParams(dp(size), dp(size))
    }

    private fun savedColourRow(entry: SavedColour, compact: Boolean = false): View {
        val line = row().apply {
            background = shape(raised, 15, outline)
            setPadding(dp(11), dp(9), dp(11), dp(9))
            isClickable = true
            isFocusable = true
            contentDescription = "Apply ${entry.name} colour"
            setOnClickListener { applyColour(entry.hex) }
            setOnLongClickListener { manageColour(entry); true }
        }
        line.addView(colourChip(entry.hex, if (compact) 25 else 33))
        val textColumn = column().apply { setPadding(dp(12), 0, 0, 0) }
        textColumn.addView(label(entry.name, 13.5f, textColour, true))
        if (!compact) textColumn.addView(label(entry.hex, 11f, muted))
        line.addView(textColumn, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        line.addView(label("›", 23f, muted))
        return line
    }

    private fun home(body: LinearLayout) {
        val hero = card(body, "Set the mood. Own the moment.", "YOUR AMBIENCE, REIMAGINED")
        val orb = GlowOrbView(this).apply {
            setColour(selectedHex)
            layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(194))
        }
        hero.addView(orb)
        val colourLine = row()
        colourLine.addView(colourChip(selectedHex, 29))
        colourLine.addView(label("  $selectedHex", 17f, textColour, true), LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        colourLine.addView(button("Choose colour  →", false) { navigate(1) })
        hero.addView(colourLine)

        val power = card(body, "Power", "Single BLE command · no brightness reset")
        power.addView(button(if (lastPower) "Turn lights off" else "Turn lights on") {
            lastPower = !lastPower
            bluetooth.send(Protocol.power(lastPower))
            render()
        })

        val level = preferences.integer("brightness", 800).coerceIn(0, 1000)
        val bright = card(body, "Brightness")
        val brightText = label("${level / 10}%", 21f, accent, true)
        bright.addView(brightText)
        bright.addView(slider(level, 1000) { n ->
            preferences.set("brightness", n)
            bluetooth.send(Protocol.brightness(n))
            brightText.text = "${n / 10}%"
        })

        val saved = preferences.colours()
        if (saved.isNotEmpty()) {
            val quick = card(body, "Saved colours", "Tap a shade to apply it instantly")
            saved.take(6).forEachIndexed { index, entry ->
                if (index > 0) gap(quick, 8)
                quick.addView(savedColourRow(entry, true))
            }
            gap(quick, 10)
            quick.addView(button("Open my palette", false) { navigate(1) })
        }
    }

    private fun colours(body: LinearLayout) {
        val editor = card(body, "Find your colour", "Drag the wheel to select hue and saturation. Release to apply.")
        val hsv = FloatArray(3)
        Color.colorToHSV(Color.parseColor(selectedHex), hsv)
        val wheel = ColourWheelView(this).apply {
            setSelection(hsv[0], hsv[1])
            setAccent(accent)
            layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(285))
        }
        editor.addView(wheel)
        val selectedRow = row()
        val swatch = colourChip(selectedHex, 38)
        selectedRow.addView(swatch)
        val hexLabel = label(selectedHex, 21f, textColour, true)
        selectedRow.addView(hexLabel, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply { leftMargin = dp(12) })
        editor.addView(selectedRow)
        gap(editor, 10)
        val field = edit(selectedHex, "#RRGGBB")
        editor.addView(field)
        gap(editor, 8)
        wheel.onColourChanged = { h, s, finished ->
            hsv[0] = h
            hsv[1] = s
            // The controller uses hue/saturation; physical brightness has its own command.
            hsv[2] = 1f
            val hex = String.format(Locale.US, "#%06X", Color.HSVToColor(hsv) and 0xFFFFFF)
            field.setText(hex)
            hexLabel.text = hex
            swatch.background = shape(Color.parseColor(hex), 19)
            if (finished) applyColour(hex)
        }
        editor.addView(button("Apply HEX colour") { applyColour(field.text.toString()) })
        gap(editor, 8)
        editor.addView(button("Save current colour", false) { saveColour(field.text.toString()) })
        editor.addView(label("Tip: the wheel sets hue and saturation. The brightness slider below controls the LED intensity separately.", 12f, muted))

        val presets = card(body, "Quick palette", "Twelve ready-to-use colours from desktop LUNA")
        val swatches = listOf("#FF5C78", "#FFAD61", "#FFE078", "#8DE6A3", "#63D5E9", "#6795FF",
            "#9568FF", "#E181E9", "#FFFFFF", "#FF3649", "#38A8FF", "#22CF9E")
        swatches.chunked(6).forEachIndexed { rowIndex, group ->
            if (rowIndex > 0) gap(presets, 9)
            val strip = row()
            group.forEach { hex ->
                val tile = View(this).apply {
                    background = shape(Color.parseColor(hex), 11, Color.argb(65, 255, 255, 255))
                    isClickable = true
                    isFocusable = true
                    contentDescription = "Apply $hex"
                    setOnClickListener { applyColour(hex) }
                }
                strip.addView(tile, LinearLayout.LayoutParams(0, dp(40), 1f).apply {
                    leftMargin = dp(3); rightMargin = dp(3)
                })
            }
            presets.addView(strip)
        }

        val level = preferences.integer("brightness", 800).coerceIn(0, 1000)
        val brightnessCard = card(body, "Brightness", "Adjust the intensity without changing your hue")
        val brightnessLabel = label("${level / 10}%", 19f, accent, true)
        brightnessCard.addView(brightnessLabel)
        brightnessCard.addView(slider(level, 1000) { n ->
            preferences.set("brightness", n)
            bluetooth.send(Protocol.brightness(n))
            brightnessLabel.text = "${n / 10}%"
        })

        val saved = preferences.colours()
        val palette = card(body, "My saved colours", "Tap to apply · long-press to rename or delete")
        if (saved.isEmpty()) palette.addView(label("Your palette is empty. Choose a colour and save it above.", 13f, muted))
        saved.forEachIndexed { index, entry ->
            if (index > 0) gap(palette, 8)
            palette.addView(savedColourRow(entry))
        }
    }

    private fun saveColour(value: String) {
        val hex = PaletteStore.canonicalHex(value)
        if (hex == null) { toast("Choose a valid HEX colour first"); return }
        val name = edit("", "Name, e.g. Midnight Blue")
        AlertDialog.Builder(this).setTitle("Save $hex").setView(name)
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Save") { _, _ ->
                val entries = preferences.colours()
                if (entries.any { it.hex == hex }) { toast("This colour is already saved"); return@setPositiveButton }
                entries.add(SavedColour(name.text.toString().trim().take(36).ifEmpty { hex }, hex))
                preferences.saveColours(entries)
                render()
            }.show()
    }

    private fun manageColour(entry: SavedColour) {
        AlertDialog.Builder(this).setTitle(entry.name)
            .setItems(arrayOf("Rename", "Delete")) { _, which ->
                if (which == 0) {
                    val name = edit(entry.name)
                    AlertDialog.Builder(this).setTitle("Rename colour").setView(name)
                        .setNegativeButton("Cancel", null)
                        .setPositiveButton("Save") { _, _ ->
                            val updated = preferences.colours().map {
                                if (it.hex == entry.hex) it.copy(name = name.text.toString().trim().take(36).ifEmpty { it.hex }) else it
                            }
                            preferences.saveColours(updated); render()
                        }.show()
                } else {
                    AlertDialog.Builder(this).setTitle("Delete ${entry.name}?")
                        .setNegativeButton("Cancel", null)
                        .setPositiveButton("Delete") { _, _ ->
                            preferences.saveColours(preferences.colours().filterNot { it.hex == entry.hex }); render()
                        }.show()
                }
            }.show()
    }

    private fun effects(body: LinearLayout) {
        val box = card(body, "58 built-in animations", "Predefined controller effects recovered from Mr Star")
        if (effects.isEmpty()) { box.addView(label("Effect catalogue unavailable")); return }
        val selectedId = preferences.integer("effect_id", effects.first().id)
        val picker = dropdown(effects.map { it.toString() }, effects.indexOfFirst { it.id == selectedId }.coerceAtLeast(0))
        box.addView(picker)
        box.addView(button("Play selected effect") {
            val chosen = effects[picker.selectedItemPosition]
            preferences.set("effect_id", chosen.id)
            bluetooth.send(Protocol.effect(chosen.id))
        })
        val speed = preferences.integer("effect_speed", 50).coerceIn(1, 100)
        box.addView(label("Speed: $speed", 13f, muted))
        box.addView(slider(speed, 100) { n ->
            val adjusted = n.coerceAtLeast(1)
            preferences.set("effect_speed", adjusted)
            bluetooth.send(Protocol.effectSpeed(adjusted))
            render()
        })
        val direction = Switch(this).apply {
            text = "Forward direction"
            setTextColor(textColour)
            isChecked = preferences.boolean("effect_forward", true)
            setOnCheckedChangeListener { _, checked ->
                preferences.set("effect_forward", checked)
                bluetooth.send(Protocol.effectDirection(checked))
            }
        }
        box.addView(direction)
    }

    private fun microphone(body: LinearLayout) {
        val box = card(body, "Controller microphone", "These commands use the LED controller's own microphone, if fitted.")
        val modes = listOf("Classic", "Soft", "Dynamic", "Disco")
        val picker = dropdown(modes, preferences.integer("mic_mode", 0))
        box.addView(picker)
        box.addView(button("Activate microphone mode") {
            preferences.set("mic_mode", picker.selectedItemPosition)
            bluetooth.sendSequence(listOf(Protocol.microphoneSource(true),
                Protocol.microphoneMode(picker.selectedItemPosition)))
        })
        val sensitivity = preferences.integer("mic_sensitivity", 50).coerceIn(0, 100)
        box.addView(label("Sensitivity: $sensitivity", 13f, muted))
        box.addView(slider(sensitivity, 100) { n ->
            preferences.set("mic_sensitivity", n)
            bluetooth.send(Protocol.microphoneSensitivity(n))
            render()
        })
        box.addView(label("Android phone-microphone audio analysis is not implemented in this initial port.", 12f, muted))
    }

    private fun timers(body: LinearLayout) {
        card(body, "Controller schedules", "These are experimental device-side schedules. Test a short schedule before relying on one.")
        scheduleCard(body, true)
        scheduleCard(body, false)
    }

    private fun scheduleCard(body: LinearLayout, on: Boolean) {
        val prefix = if (on) "timer_on" else "timer_off"
        val box = card(body, if (on) "Automatic ON" else "Automatic OFF")
        val enabled = Switch(this).apply {
            text = "Schedule enabled"
            setTextColor(textColour)
            isChecked = preferences.boolean("${prefix}_enabled", false)
        }
        box.addView(enabled)
        var hour = preferences.integer("${prefix}_hour", if (on) 18 else 23).coerceIn(0, 23)
        var minute = preferences.integer("${prefix}_minute", 0).coerceIn(0, 59)
        val time = button(String.format("Time: %02d:%02d", hour, minute), false) {
            TimePickerDialog(this, { _, h, m ->
                hour = h; minute = m
                preferences.set("${prefix}_hour", h)
                preferences.set("${prefix}_minute", m)
                render()
            }, hour, minute, true).show()
        }
        box.addView(time)
        val weekdays = listOf("M", "T", "W", "T", "F", "S", "S")
        val dayRow = row()
        val checks = weekdays.mapIndexed { i, title ->
            CheckBox(this).apply {
                text = title
                textSize = 12f
                setTextColor(textColour)
                isChecked = preferences.boolean("${prefix}_day_$i", true)
                buttonTintList = android.content.res.ColorStateList.valueOf(accent)
                val lp = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
                dayRow.addView(this, lp)
            }
        }
        box.addView(label("Days (Mon–Sun)", 12f, muted))
        box.addView(dayRow)
        box.addView(button("Save ${if (on) "ON" else "OFF"} schedule") {
            val selectedDays = checks.map { it.isChecked }
            preferences.set("${prefix}_enabled", enabled.isChecked)
            selectedDays.forEachIndexed { i, checked -> preferences.set("${prefix}_day_$i", checked) }
            // Clock and timer frames are sent in order; no automatic schedule writes on connection.
            bluetooth.sendSequence(listOf(Protocol.clock(),
                Protocol.timer(on, enabled.isChecked, selectedDays, hour, minute)))
            toast("Schedule command queued. Verify on hardware.")
        })
    }

    private fun settings(body: LinearLayout) {
        val box = card(body, "Strip configuration", "Only change these settings if you know your strip's wiring.")
        val count = edit(preferences.integer("pixel_count", 150).toString(), "8–300", true)
        box.addView(label("Active LED count (8–300)", 13f, muted))
        box.addView(count)
        box.addView(button("Apply pixel count") {
            val number = count.text.toString().toIntOrNull()
            if (number == null || number !in 8..300) { toast("Enter 8–300"); return@button }
            preferences.set("pixel_count", number)
            bluetooth.send(Protocol.pixelCount(number))
        })
        val orders = listOf("RGB", "RBG", "GRB", "GBR", "BRG", "BGR")
        val picker = dropdown(orders, preferences.integer("channel_order", 0))
        box.addView(label("Channel order", 13f, muted))
        box.addView(picker)
        box.addView(button("Apply channel order", false) {
            preferences.set("channel_order", picker.selectedItemPosition)
            bluetooth.send(Protocol.channelOrder(picker.selectedItemPosition))
        })
        box.addView(label("Saved preferences do not overwrite the controller on connection. Individual LED/segment colour control is not available with the known protocol.", 12f, muted))
    }

    private fun music(body: LinearLayout) {
        val box = card(body, "Music", "Not yet ported to Android")
        box.addView(label("Desktop LUNA's local music player and host-audio reactive mode require separate Android audio and media implementations. They are intentionally not shown as working features here.", 14f, muted))
        box.addView(label("The controller microphone modes are available on the Mic page.", 13f, accent))
    }

    private fun more(body: LinearLayout) {
        val intro = card(body, "Explore LUNA", "More ways to control your light strip")
        intro.addView(label("The same controller features as desktop LUNA, arranged for a smaller screen.", 13f, muted))
        val mic = card(body, "Microphone modes", "Classic, Soft, Dynamic and Disco")
        mic.addView(button("Open microphone controls  →") { navigate(3) })
        val timer = card(body, "Schedules", "Automatic ON/OFF times and weekday selection")
        timer.addView(button("Open schedules  →", false) { navigate(4) })
        val settings = card(body, "Device settings", "LED count, colour order and controller configuration")
        settings.addView(button("Open device settings  →", false) { navigate(5) })
        card(body, "LUNA for Android", "Adaptive theme · Bluetooth LE · Saved colours").addView(
            label("Individual LED colour addressing is not supported by the known controller commands.", 12f, muted))
    }
}
