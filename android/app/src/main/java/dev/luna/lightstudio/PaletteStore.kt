package dev.luna.lightstudio

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

data class SavedColour(val name: String, val hex: String)

class PaletteStore(context: Context) {
    private val preferences = context.getSharedPreferences("luna", Context.MODE_PRIVATE)

    fun string(key: String, default: String) = preferences.getString(key, default) ?: default
    fun integer(key: String, default: Int) = preferences.getInt(key, default)
    fun boolean(key: String, default: Boolean) = preferences.getBoolean(key, default)
    fun set(key: String, value: String) { preferences.edit().putString(key, value).apply() }
    fun set(key: String, value: Int) { preferences.edit().putInt(key, value).apply() }
    fun set(key: String, value: Boolean) { preferences.edit().putBoolean(key, value).apply() }

    fun colours(): MutableList<SavedColour> {
        val result = mutableListOf<SavedColour>()
        val seen = mutableSetOf<String>()
        try {
            val array = JSONArray(string("saved_colours_v1", "[]"))
            for (i in 0 until array.length()) {
                val item = array.optJSONObject(i) ?: continue
                val hex = canonicalHex(item.optString("hex")) ?: continue
                if (!seen.add(hex)) continue
                val name = item.optString("name").trim().take(36).ifEmpty { hex }
                result.add(SavedColour(name, hex))
            }
        } catch (_: Exception) { /* Ignore corrupted preferences */ }
        return result
    }

    fun saveColours(colours: List<SavedColour>) {
        val array = JSONArray()
        colours.distinctBy { it.hex }.forEach {
            array.put(JSONObject().put("name", it.name).put("hex", it.hex))
        }
        set("saved_colours_v1", array.toString())
    }

    companion object {
        fun canonicalHex(value: String): String? {
            val clean = value.trim().removePrefix("#")
            return if (Regex("[0-9a-fA-F]{6}").matches(clean)) "#${clean.uppercase()}" else null
        }
    }
}
