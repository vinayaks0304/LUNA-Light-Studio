import asyncio
import colorsys
import threading
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QObject, QTimer, QSettings, QTime, QUrl
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QLinearGradient
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QFrame, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QGridLayout, QStackedWidget, QLineEdit, QColorDialog,
    QSlider, QSpinBox, QComboBox, QMessageBox, QSizePolicy, QScrollArea,
    QCheckBox, QTimeEdit, QFileDialog, QListWidget, QProgressBar, QInputDialog, QDialog
)
try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
except (ImportError, OSError):
    QMediaPlayer = None
    QAudioOutput = None
from .ble import Controller
from . import protocol
from .effects import EFFECTS, EFFECT_IDS
from .audio import AudioCapture, input_devices
from .palette import clean_name, dump_palette, load_palette, normalise_hex
from .theme import theme_for_colour, stylesheet


class Signals(QObject):
    status = Signal(str)
    error = Signal(str)
    connection = Signal(bool)
    notification = Signal(bytes)
    audio = Signal(float, float)


class GlowOrb(QWidget):
    def __init__(self):
        super().__init__()
        self.colour = QColor('#9568ff')
        self.setMinimumSize(230, 230)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_colour(self, colour):
        self.colour = QColor(colour)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        radius = min(self.width(), self.height()) * .33
        for factor, alpha in [(1.47, 9), (1.32, 14), (1.17, 23), (1.06, 34)]:
            c = QColor(self.colour); c.setAlpha(alpha)
            p.setPen(Qt.NoPen); p.setBrush(c)
            p.drawEllipse(int(cx-radius*factor), int(cy-radius*factor), int(2*radius*factor), int(2*radius*factor))
        grad = QLinearGradient(cx-radius, cy-radius, cx+radius, cy+radius)
        light = self.colour.lighter(155)
        grad.setColorAt(0, light)
        grad.setColorAt(.55, self.colour)
        grad.setColorAt(1, self.colour.darker(170))
        p.setBrush(QBrush(grad)); p.setPen(QPen(QColor(255,255,255,60), 1.5))
        p.drawEllipse(int(cx-radius), int(cy-radius), int(radius*2), int(radius*2))
        p.setBrush(QColor(255,255,255,38)); p.setPen(Qt.NoPen)
        p.drawEllipse(int(cx-radius*.49), int(cy-radius*.62), int(radius*.48), int(radius*.3))


def text(value, style='body'):
    l = QLabel(value)
    l.setObjectName(style)
    l.setWordWrap(True)
    return l


def card(layout=None):
    frame = QFrame(); frame.setObjectName('card')
    if layout is None:
        layout = QVBoxLayout()
    layout.setContentsMargins(23, 22, 23, 22)
    layout.setSpacing(14)
    frame.setLayout(layout)
    return frame


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('LUNA — Light Studio')
        self.resize(1170, 760)
        self.setMinimumSize(850, 620)
        self.settings = QSettings('LUNA Light Studio', 'LUNA')
        self.colour = self.settings.value('colour', '#9568ff')
        if not QColor(self.colour).isValid():
            self.colour = '#9568ff'
        self.last_brightness = max(0, min(1000, self.settings.value('brightness', 800, type=int)))
        # Stored beside LUNA's other preferences, outside the project directory.
        self.saved_colours = load_palette(self.settings.value('saved_colours_v1', '[]'))
        self.power_on = True  # UI's last command, not a hardware readback
        self._timer_read_pending = set()
        self.audio_capture = AudioCapture(lambda level, freq: self.signals.audio.emit(level, freq))
        self.is_connected = False
        self.loop = asyncio.new_event_loop()
        self.worker = threading.Thread(target=self._run_loop, daemon=True)
        self.worker.start()
        self.signals = Signals()
        self.signals.status.connect(self._status)
        self.signals.error.connect(self._error)
        self.signals.connection.connect(self._connection_changed)
        self.signals.notification.connect(self._timer_notification)
        self.signals.audio.connect(self._audio_frame)
        self.controller = Controller(self.signals.status.emit,
                                     self.signals.notification.emit,
                                     lambda: self.signals.connection.emit(False))
        self.brightness_timer = QTimer(self)
        self.brightness_timer.setSingleShot(True)
        self.brightness_timer.setInterval(140)
        self.brightness_timer.timeout.connect(lambda: self._send(protocol.brightness_frame(self.last_brightness)))
        self.speed_timer = QTimer(self)
        self.speed_timer.setSingleShot(True)
        self.speed_timer.setInterval(220)
        self.speed_timer.timeout.connect(self._apply_speed)
        # Debounce colour-dialog previews so restyling a large Effects page
        # never interferes with the Bluetooth worker or floods the UI.
        self.theme_preview_timer = QTimer(self)
        self.theme_preview_timer.setSingleShot(True)
        self.theme_preview_timer.setInterval(60)
        self.theme_preview_timer.timeout.connect(self._flush_theme_preview)
        self._pending_theme_colour = self.colour
        self._last_theme_colour = None
        self._build()
        self._display_colour(self.colour)
        self._apply_theme(self.colour)

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def _submit(self, coro, success=None):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        def done(f):
            try:
                result = f.result()
                if success and result is not False:
                    self.signals.status.emit(success)
            except Exception as exc:
                self.signals.error.emit(str(exc))
        future.add_done_callback(done)

    def _send(self, frame, message=None, drop_if_busy=False):
        if not self.is_connected:
            self._status('Connect to your LED strip first')
            return False
        self._submit(self.controller.send(frame, drop_if_busy=drop_if_busy), message)
        return True

    def _send_many(self, frames, message=None):
        if not self.is_connected:
            self._status('Connect to your LED strip first')
            return False
        self._submit(self.controller.send_many(frames), message)
        return True

    async def _connect(self):
        await self.controller.connect()
        self.signals.connection.emit(True)

    async def _disconnect(self):
        await self.controller.disconnect()
        self.signals.connection.emit(False)

    def _build(self):
        root = QWidget(); outer = QHBoxLayout(root); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        sidebar = QFrame(); sidebar.setObjectName('sidebar'); sidebar.setFixedWidth(220)
        navlayout = QVBoxLayout(sidebar); navlayout.setContentsMargins(19,30,19,24); navlayout.setSpacing(7)
        brandrow = QHBoxLayout(); brandrow.addWidget(text('◐', 'value')); brandrow.addWidget(text('LUNA','brand')); brandrow.addStretch()
        navlayout.addLayout(brandrow)
        navlayout.addWidget(text('YOUR LIGHT, YOUR SPACE', 'eyebrow'))
        navlayout.addSpacing(39)
        self.stack = QStackedWidget()
        self.navbuttons = []
        for i, (icon, name) in enumerate([('◈','Dashboard'),('◉','Colours'),('✦','Effects'),('♫','Music'),('◷','Timer'),('⚙','Settings')]):
            b = QPushButton(f'{icon}    {name}'); b.setObjectName('nav'); b.setProperty('active', i == 0)
            b.clicked.connect(lambda checked=False, n=i: self._navigate(n))
            self.navbuttons.append(b); navlayout.addWidget(b)
        navlayout.addStretch()
        navlayout.addWidget(text('COLOUR-SYNCED THEME', 'eyebrow'))
        theme_row = QHBoxLayout(); theme_row.setSpacing(9)
        self.theme_chip = QFrame(); self.theme_chip.setObjectName('themeChip')
        self.theme_chip.setFixedSize(15, 15)
        theme_row.addWidget(self.theme_chip)
        self.theme_hex = text(self.colour.upper(), 'muted')
        theme_row.addWidget(self.theme_hex)
        theme_row.addStretch()
        navlayout.addLayout(theme_row)
        navlayout.addSpacing(18)
        navlayout.addWidget(text('DEVICE STATUS', 'eyebrow'))
        self.side_status = text('●  Disconnected', 'muted'); navlayout.addWidget(self.side_status)
        navlayout.addSpacing(8)
        navlayout.addWidget(text('GATT--DEMO  •  Bluetooth LE', 'muted'))
        outer.addWidget(sidebar)
        main = QWidget(); ml = QVBoxLayout(main); ml.setContentsMargins(33,25,33,24); ml.setSpacing(23)
        header = QHBoxLayout(); titles = QVBoxLayout(); titles.setSpacing(4)
        titles.addWidget(text('LIGHT CONTROL CENTRE','eyebrow'))
        self.page_title = text('Welcome to LUNA','heading'); titles.addWidget(self.page_title)
        header.addLayout(titles); header.addStretch()
        self.connection_button = QPushButton('Connect device'); self.connection_button.setObjectName('primary')
        self.connection_button.clicked.connect(self._toggle_connection)
        header.addWidget(self.connection_button)
        ml.addLayout(header)
        self.stack.addWidget(self._dashboard())
        self.stack.addWidget(self._colours())
        self.stack.addWidget(self._effects())
        self.stack.addWidget(self._music())
        self.stack.addWidget(self._timer())
        self.stack.addWidget(self._settings())
        ml.addWidget(self.stack,1)
        self.footer = text('Ready to connect', 'muted'); ml.addWidget(self.footer)
        outer.addWidget(main,1); self.setCentralWidget(root)
        self._navigate(0)

    def _navigate(self, n):
        if n != 3 and self.audio_capture.active:
            self._stop_audio()
        self.stack.setCurrentIndex(n)
        self.page_title.setText(['Welcome to LUNA','Colour studio','Light effects','Music & rhythm','Sleep timer','Device settings'][n])
        for i,b in enumerate(self.navbuttons):
            b.setProperty('active', i==n)
            b.style().unpolish(b); b.style().polish(b)

    def _scroll(self, widget):
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(widget)
        return scroll

    def _dashboard(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(0,0,0,0); layout.setSpacing(18)
        hero = card(QHBoxLayout()); hero.layout().setSpacing(15)
        left = QVBoxLayout(); left.setSpacing(15)
        left.addWidget(text('YOUR AMBIENCE, REIMAGINED','eyebrow'))
        left.addWidget(text('Set the mood.\nOwn the moment.','heading'))
        left.addWidget(text('An effortless space to control your lights, fine-tune your colour and make every moment feel different.','muted'))
        left.addStretch()
        start = QPushButton('Open colour studio  →'); start.setObjectName('primary'); start.clicked.connect(lambda: self._navigate(1))
        left.addWidget(start, alignment=Qt.AlignLeft)
        hero.layout().addLayout(left, 5)
        self.orb = GlowOrb(); hero.layout().addWidget(self.orb, 5)
        layout.addWidget(hero, 4)
        row = QHBoxLayout(); row.setSpacing(18)
        status_card = card(); status_card.layout().addWidget(text('CONNECTED DEVICE','eyebrow'))
        status_card.layout().addWidget(text('GATT--DEMO','section'))
        self.device_status = text('Offline  •  Waiting for connection','muted'); status_card.layout().addWidget(self.device_status)
        row.addWidget(status_card,1)
        power_card = card(); power_card.layout().addWidget(text('POWER','eyebrow'))
        self.power_button = QPushButton('Turn lights off'); self.power_button.clicked.connect(self._toggle_power)
        power_card.layout().addWidget(self.power_button); power_card.layout().addWidget(text('Toggle your strip instantly','muted'))
        row.addWidget(power_card,1)
        layout.addLayout(row,2)
        favourites = card()
        shortcut_header = QHBoxLayout()
        shortcut_header.addWidget(text('SAVED COLOURS', 'eyebrow'))
        shortcut_header.addStretch()
        view_all = QPushButton('Manage palette  →')
        view_all.clicked.connect(lambda: self._navigate(1))
        shortcut_header.addWidget(view_all)
        favourites.layout().addLayout(shortcut_header)
        self.dashboard_palette_grid = QGridLayout()
        self.dashboard_palette_grid.setSpacing(9)
        favourites.layout().addLayout(self.dashboard_palette_grid)
        self.dashboard_palette_empty = text('Save a colour in Colour Studio to see it here for one-click access.', 'muted')
        favourites.layout().addWidget(self.dashboard_palette_empty)
        layout.addWidget(favourites, 2)
        return self._scroll(page)

    def _colours(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(0,0,0,0); layout.setSpacing(18)
        top = QHBoxLayout(); top.setSpacing(18)
        preview = card(); preview.layout().addWidget(text('LIVE COLOUR PREVIEW','eyebrow'))
        self.colour_orb = GlowOrb(); preview.layout().addWidget(self.colour_orb,1)
        self.current_hex = text(self.colour.upper(),'value'); self.current_hex.setAlignment(Qt.AlignCenter)
        preview.layout().addWidget(self.current_hex)
        top.addWidget(preview,5)
        controls = card(); controls.layout().addWidget(text('PICK YOUR COLOUR','eyebrow'))
        controls.layout().addWidget(text('A shade for every mood','section'))
        controls.layout().addWidget(text('Choose a colour or enter a HEX value.','muted'))
        hexrow = QHBoxLayout(); self.hex_field = QLineEdit(self.colour); hexrow.addWidget(self.hex_field)
        apply = QPushButton('Apply'); apply.setObjectName('primary'); apply.clicked.connect(self._apply_hex); hexrow.addWidget(apply)
        controls.layout().addLayout(hexrow)
        pickrow = QHBoxLayout()
        picker = QPushButton('◉   Colour picker'); picker.clicked.connect(self._pick_colour)
        pickrow.addWidget(picker, 1)
        save_current = QPushButton('＋  Save colour'); save_current.setObjectName('primary')
        save_current.setToolTip('Save the currently selected colour for future LUNA sessions')
        save_current.clicked.connect(self._save_current_colour)
        pickrow.addWidget(save_current, 1)
        controls.layout().addLayout(pickrow)
        controls.layout().addSpacing(8)
        controls.layout().addWidget(text('QUICK PALETTE','eyebrow'))
        grid = QGridLayout(); grid.setSpacing(10)
        swatches = ['#ff5c78','#ffad61','#ffe078','#8de6a3','#63d5e9','#6795ff','#9568ff','#e181e9','#ffffff','#ff3649','#38a8ff','#22cf9e']
        for i,c in enumerate(swatches):
            b = QPushButton(''); b.setObjectName('swatch'); b.setToolTip(c.upper())
            b.setStyleSheet(f'QPushButton#swatch {{ background:{c}; border:2px solid #ffffff30; border-radius:13px; min-height:38px; }} QPushButton#swatch:hover {{ border:3px solid white; }}')
            b.clicked.connect(lambda checked=False, colour=c: self._set_colour(colour))
            grid.addWidget(b,i//6,i%6)
        controls.layout().addLayout(grid); controls.layout().addStretch()
        top.addWidget(controls,6); layout.addLayout(top,5)
        saved = card()
        saved.layout().addWidget(text('MY SAVED COLOURS', 'eyebrow'))
        saved.layout().addWidget(text('Your personal palette', 'section'))
        saved.layout().addWidget(text('Click a colour to apply it. Saved colours remain available after restarting LUNA.', 'muted'))
        self.saved_colours_grid = QGridLayout()
        self.saved_colours_grid.setSpacing(10)
        saved.layout().addLayout(self.saved_colours_grid)
        self.saved_colours_empty = text('No saved colours yet. Choose a shade above and press Save colour.', 'muted')
        saved.layout().addWidget(self.saved_colours_empty)
        self._render_saved_colours()
        layout.addWidget(saved, 2)
        bright = card(); line = QHBoxLayout(); line.addWidget(text('Brightness','section')); line.addStretch()
        self.brightness_value = text('80%','value'); line.addWidget(self.brightness_value)
        bright.layout().addLayout(line)
        self.brightness_slider = QSlider(Qt.Horizontal); self.brightness_slider.setRange(0,1000)
        self.brightness_slider.setValue(self.last_brightness); self.brightness_slider.valueChanged.connect(self._brightness_changed)
        self.brightness_value.setText(f'{round(self.last_brightness/10)}%')
        bright.layout().addWidget(self.brightness_slider)
        bright.layout().addWidget(text('Slide to set the perfect intensity','muted'))
        layout.addWidget(bright,2)
        return self._scroll(page)

    def _effects(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(0,0,0,0); layout.setSpacing(18)
        intro = card(); intro.layout().addWidget(text('ANIMATED LIGHTING', 'eyebrow'))
        intro.layout().addWidget(text('58 effects. Six collections.', 'section'))
        intro.layout().addWidget(text('Presets and identifiers come from Mr Star. Choose an effect to send its command; simply browsing does not change your strip.', 'muted'))
        layout.addWidget(intro)
        controls = card(); filterrow = QHBoxLayout()
        self.effect_category = QComboBox(); self.effect_category.addItems(['All collections', *EFFECT_IDS.keys()])
        self.effect_search = QLineEdit(); self.effect_search.setPlaceholderText('Search animations…')
        filterrow.addWidget(self.effect_category, 1); filterrow.addWidget(self.effect_search, 2)
        controls.layout().addLayout(filterrow)
        self.effect_count = text('58 effects', 'muted'); controls.layout().addWidget(self.effect_count)
        controls.layout().addSpacing(5)
        speedrow = QHBoxLayout(); speedrow.addWidget(text('Animation speed', 'body')); speedrow.addStretch()
        self.speed_value = text('50%', 'value'); speedrow.addWidget(self.speed_value)
        controls.layout().addLayout(speedrow)
        self.effect_speed = QSlider(Qt.Horizontal); self.effect_speed.setRange(1, 100)
        self.effect_speed.setValue(max(1, min(100, self.settings.value('effect_speed', 50, type=int))))
        self.speed_value.setText(f'{self.effect_speed.value()}%')
        self.effect_speed.valueChanged.connect(self._speed_changed)
        self.effect_speed.sliderReleased.connect(self._apply_speed)
        controls.layout().addWidget(self.effect_speed)
        directionrow = QHBoxLayout()
        self.direction_box = QCheckBox('Forward animation direction')
        self.direction_box.setChecked(self.settings.value('effect_forward', True, type=bool))
        directionrow.addWidget(self.direction_box)
        set_direction = QPushButton('Apply direction'); set_direction.clicked.connect(self._apply_direction)
        directionrow.addWidget(set_direction)
        controls.layout().addLayout(directionrow)
        layout.addWidget(controls)
        self.effects_container = QWidget()
        self.effects_grid = QGridLayout(self.effects_container)
        self.effects_grid.setContentsMargins(0, 0, 0, 0)
        self.effects_grid.setSpacing(12)
        layout.addWidget(self.effects_container)
        self.effect_category.currentIndexChanged.connect(self._render_effects)
        self.effect_search.textChanged.connect(self._render_effects)
        self._render_effects()
        return self._scroll(page)

    def _render_effects(self, *_):
        while self.effects_grid.count():
            item = self.effects_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        category = self.effect_category.currentText()
        search = self.effect_search.text().strip().lower()
        matches = [e for e in EFFECTS
                   if (category == 'All collections' or e.category == category)
                   and (search in e.name.lower() or search == str(e.id))]
        self.effect_count.setText(f'{len(matches)} of {len(EFFECTS)} animations')
        for idx, effect in enumerate(matches):
            panel = card(QHBoxLayout()); panel.layout().setContentsMargins(16, 14, 16, 14)
            details = QVBoxLayout(); details.setSpacing(5)
            details.addWidget(text(effect.name, 'body'))
            details.addWidget(text(f'{effect.category}  •  Effect {effect.id:02d}', 'muted'))
            panel.layout().addLayout(details, 1)
            activate = QPushButton('Play'); activate.setObjectName('primary')
            activate.clicked.connect(lambda checked=False, e=effect: self._activate_effect(e))
            panel.layout().addWidget(activate)
            self.effects_grid.addWidget(panel, idx // 2, idx % 2)
        self.effects_grid.setColumnStretch(0, 1); self.effects_grid.setColumnStretch(1, 1)

    def _activate_effect(self, effect):
        if self._send(protocol.effect_frame(effect.id), f'Effect {effect.id} sent: {effect.name}'):
            self.settings.setValue('last_effect_id', effect.id)

    def _speed_changed(self, value):
        self.speed_value.setText(f'{value}%')
        self.settings.setValue('effect_speed', value)
        if self.is_connected:
            self.speed_timer.start()

    def _apply_speed(self):
        self.speed_timer.stop()
        value = self.effect_speed.value()
        self.settings.setValue('effect_speed', value)
        self._send(protocol.effect_speed_frame(value), 'Animation speed sent')

    def _apply_direction(self):
        forward = self.direction_box.isChecked()
        self.settings.setValue('effect_forward', forward)
        self._send(protocol.effect_direction_frame(forward), 'Animation direction sent')

    def _music(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(0,0,0,0); layout.setSpacing(18)
        info = card(); info.layout().addWidget(text('MUSIC & RHYTHM', 'eyebrow'))
        info.layout().addWidget(text('Make light respond to sound', 'section'))
        info.layout().addWidget(text('Use the controller’s built-in microphone, or stream colour changes from a PC microphone / PipeWire monitor. Music playback is local to your PC.', 'muted'))
        layout.addWidget(info)

        mic = card(); mic.layout().addWidget(text('DEVICE MICROPHONE', 'eyebrow'))
        mic.layout().addWidget(text('Built-in rhythm modes', 'section'))
        mr = QHBoxLayout(); self.mic_mode = QComboBox()
        self.mic_mode.addItems(list(protocol.MICROPHONE_MODES))
        saved_mode = self.settings.value('mic_mode', 'Classic')
        self.mic_mode.setCurrentText(saved_mode if saved_mode in protocol.MICROPHONE_MODES else 'Classic')
        mr.addWidget(self.mic_mode, 1)
        mic_apply = QPushButton('Activate device mic'); mic_apply.setObjectName('primary')
        mic_apply.clicked.connect(self._activate_device_mic)
        mr.addWidget(mic_apply); mic.layout().addLayout(mr)
        ms = QHBoxLayout(); ms.addWidget(text('Microphone sensitivity', 'body')); ms.addStretch()
        self.mic_sensitivity_label = text('100%', 'value'); ms.addWidget(self.mic_sensitivity_label)
        mic.layout().addLayout(ms)
        self.mic_sensitivity = QSlider(Qt.Horizontal); self.mic_sensitivity.setRange(0,100)
        self.mic_sensitivity.setValue(max(0, min(100, self.settings.value('mic_sensitivity', 100, type=int))))
        self.mic_sensitivity_label.setText(f'{self.mic_sensitivity.value()}%')
        self.mic_sensitivity.valueChanged.connect(lambda v: self.mic_sensitivity_label.setText(f'{v}%'))
        mic.layout().addWidget(self.mic_sensitivity)
        sensitivity_apply = QPushButton('Apply sensitivity'); sensitivity_apply.clicked.connect(self._apply_mic_sensitivity)
        mic.layout().addWidget(sensitivity_apply, alignment=Qt.AlignLeft)
        layout.addWidget(mic)

        host = card(); host.layout().addWidget(text('PC AUDIO REACTIVE', 'eyebrow'))
        host.layout().addWidget(text('Microphone or system audio', 'section'))
        host.layout().addWidget(text('For music playing on your PC, select a monitor/loopback input if one is available. This mode changes the whole active strip colour, not individual LEDs.', 'muted'))
        inputrow = QHBoxLayout(); self.audio_source = QComboBox()
        self.audio_source.setMinimumWidth(170)
        inputrow.addWidget(self.audio_source, 1)
        refresh = QPushButton('Refresh inputs'); refresh.clicked.connect(self._refresh_audio_inputs)
        inputrow.addWidget(refresh); host.layout().addLayout(inputrow)
        thresholdrow = QHBoxLayout(); thresholdrow.addWidget(text('Response threshold', 'body')); thresholdrow.addStretch()
        self.audio_threshold = QSlider(Qt.Horizontal); self.audio_threshold.setRange(1, 80)
        self.audio_threshold.setValue(max(1, min(80, self.settings.value('audio_threshold', 12, type=int))))
        self.audio_threshold.valueChanged.connect(lambda v: self.settings.setValue('audio_threshold', v))
        thresholdrow.addWidget(self.audio_threshold, 1)
        host.layout().addLayout(thresholdrow)
        self.audio_level = QProgressBar(); self.audio_level.setRange(0,100); self.audio_level.setValue(0)
        host.layout().addWidget(self.audio_level)
        host_buttons = QHBoxLayout()
        self.audio_start = QPushButton('Start reacting'); self.audio_start.setObjectName('primary')
        self.audio_start.clicked.connect(self._start_audio)
        self.audio_stop = QPushButton('Stop'); self.audio_stop.setEnabled(False)
        self.audio_stop.clicked.connect(self._stop_audio)
        host_buttons.addWidget(self.audio_start); host_buttons.addWidget(self.audio_stop); host_buttons.addStretch()
        host.layout().addLayout(host_buttons)
        layout.addWidget(host)

        music = card(); music.layout().addWidget(text('LOCAL MUSIC PLAYER', 'eyebrow'))
        music.layout().addWidget(text('Your tracks, your ambience', 'section'))
        music.layout().addWidget(text('Playback uses Qt Multimedia. To make lights follow the music, start PC audio reactive mode with a system monitor input.', 'muted'))
        add_tracks = QPushButton('Add audio files'); add_tracks.clicked.connect(self._add_tracks)
        music.layout().addWidget(add_tracks, alignment=Qt.AlignLeft)
        self.track_list = QListWidget(); self.track_list.setMinimumHeight(115)
        self.track_list.itemDoubleClicked.connect(lambda item: self._play_index(self.track_list.row(item)))
        music.layout().addWidget(self.track_list)
        self.track_paths = []
        playback = QHBoxLayout()
        self.previous_track = QPushButton('Previous'); self.previous_track.clicked.connect(lambda: self._step_track(-1))
        self.play_pause = QPushButton('Play / pause'); self.play_pause.setObjectName('primary')
        self.play_pause.clicked.connect(self._toggle_playback)
        self.next_track = QPushButton('Next'); self.next_track.clicked.connect(lambda: self._step_track(1))
        playback.addWidget(self.previous_track); playback.addWidget(self.play_pause); playback.addWidget(self.next_track)
        music.layout().addLayout(playback)
        self.track_progress = QSlider(Qt.Horizontal); self.track_progress.setRange(0,0)
        self.track_progress.sliderReleased.connect(self._seek_track)
        music.layout().addWidget(self.track_progress)
        self.track_time = text('00:00 / 00:00', 'muted'); music.layout().addWidget(self.track_time)
        self.player = None
        if QMediaPlayer and QAudioOutput:
            self.player = QMediaPlayer(self)
            self.player_output = QAudioOutput(self); self.player_output.setVolume(0.7)
            self.player.setAudioOutput(self.player_output)
            self.player.positionChanged.connect(self._player_position)
            self.player.durationChanged.connect(self._player_duration)
            self.player.mediaStatusChanged.connect(self._player_media_status)
            self.player.errorOccurred.connect(lambda *_: self._status('Audio playback error: ' + self.player.errorString()))
        else:
            music.layout().addWidget(text('Qt Multimedia unavailable in this installation.', 'muted'))
        layout.addWidget(music)
        self._refresh_audio_inputs()
        return self._scroll(page)

    def _refresh_audio_inputs(self):
        current = self.audio_source.currentData()
        self.audio_source.clear()
        try:
            devices = input_devices()
        except Exception as exc:
            self._status(f'Audio device enumeration failed: {exc}')
            devices = []
        for index, name in devices:
            self.audio_source.addItem(name, index)
        if not devices:
            self.audio_source.addItem('No audio inputs found', None)
        elif current is not None:
            pos = self.audio_source.findData(current)
            if pos >= 0:
                self.audio_source.setCurrentIndex(pos)

    def _activate_device_mic(self):
        mode = self.mic_mode.currentText()
        self.settings.setValue('mic_mode', mode)
        if self.audio_capture.active:
            self._stop_audio()
        self._send_many([protocol.microphone_source_frame(True),
                         protocol.microphone_mode_frame(mode),
                         protocol.microphone_sensitivity_frame(self.mic_sensitivity.value())],
                        f'Device microphone: {mode} mode sent')

    def _apply_mic_sensitivity(self):
        value = self.mic_sensitivity.value()
        self.settings.setValue('mic_sensitivity', value)
        self._send(protocol.microphone_sensitivity_frame(value), 'Microphone sensitivity sent')

    def _start_audio(self):
        if not self.is_connected:
            self._status('Connect to your LED strip first')
            return
        device = self.audio_source.currentData()
        if device is None:
            self._status('No available PC audio input. Check sounddevice / PortAudio.')
            return
        try:
            self.audio_capture.start(device)
        except Exception as exc:
            QMessageBox.warning(self, 'LUNA — Audio input', str(exc))
            return
        self.audio_start.setEnabled(False); self.audio_stop.setEnabled(True)
        self._send(protocol.microphone_source_frame(False), 'PC microphone mode enabled')

    def _stop_audio(self):
        try:
            self.audio_capture.stop()
        except Exception as exc:
            self._status(f'Audio stop error: {exc}')
        self.audio_start.setEnabled(True); self.audio_stop.setEnabled(False)
        self.audio_level.setValue(0)
        # Do not change power, brightness, or microphone mode when stopping.

    def _audio_frame(self, rms, frequency):
        if not self.audio_capture.active or not self.is_connected:
            return
        self.audio_level.setValue(min(100, round(rms * 1800)))
        if rms < self.audio_threshold.value() / 2500 or frequency <= 0:
            return
        # Inspired by Android's frequency-driven palette; not a per-pixel command.
        hue = ((frequency / 5.0) % 360) / 360
        r, g, b = colorsys.hsv_to_rgb(hue, 0.95, 1.0)
        colour = '#%02x%02x%02x' % (int(r * 255), int(g * 255), int(b * 255))
        self._send(protocol.microphone_colour_frame(colour), drop_if_busy=True)

    def _add_tracks(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Add music', str(Path.home()),
                                               'Audio files (*.mp3 *.flac *.wav *.ogg *.m4a);;All files (*)')
        for path in paths:
            if path not in self.track_paths:
                self.track_paths.append(path)
                self.track_list.addItem(Path(path).name)
        if self.track_paths and self.track_list.currentRow() < 0:
            self.track_list.setCurrentRow(0)

    def _play_index(self, index):
        if not self.player or not 0 <= index < len(self.track_paths):
            return
        self.track_list.setCurrentRow(index)
        self.player.setSource(QUrl.fromLocalFile(self.track_paths[index]))
        self.player.play()

    def _step_track(self, step):
        if not self.track_paths:
            return
        current = self.track_list.currentRow()
        self._play_index((current + step) % len(self.track_paths))

    def _toggle_playback(self):
        if not self.player:
            self._status('Qt Multimedia unavailable')
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        elif self.player.source().isEmpty():
            self._play_index(max(0, self.track_list.currentRow()))
        else:
            self.player.play()

    def _player_position(self, position):
        if not self.track_progress.isSliderDown():
            self.track_progress.setValue(position)
        self.track_time.setText(f'{self._time_text(position)} / {self._time_text(self.track_progress.maximum())}')

    def _player_duration(self, duration):
        self.track_progress.setRange(0, max(0, duration))

    def _seek_track(self):
        if self.player:
            self.player.setPosition(self.track_progress.value())

    def _player_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia and self.track_paths:
            self._step_track(1)

    @staticmethod
    def _time_text(milliseconds):
        seconds = max(0, int(milliseconds) // 1000)
        return f'{seconds // 60:02d}:{seconds % 60:02d}'

    def _timer(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(0,0,0,0); layout.setSpacing(18)
        info = card(); info.layout().addWidget(text('DEVICE SCHEDULE', 'eyebrow'))
        info.layout().addWidget(text('Lights on your time', 'section'))
        info.layout().addWidget(text('These are controller-side schedules, not timers that require LUNA to remain open. Saving a schedule also synchronises the controller clock. Readback depends on firmware notifications.', 'muted'))
        layout.addWidget(info)
        top = card(QHBoxLayout())
        sync = QPushButton('Sync device clock'); sync.clicked.connect(self._sync_clock)
        read = QPushButton('Read device schedules'); read.setObjectName('primary'); read.clicked.connect(self._read_schedules)
        top.layout().addWidget(sync); top.layout().addWidget(read)
        layout.addWidget(top)
        self.schedule_widgets = {}
        for kind, title, default_time in [('on','Automatic ON','07:00'), ('off','Automatic OFF','23:00')]:
            panel = card(); panel.layout().addWidget(text(title.upper(), 'eyebrow'))
            row = QHBoxLayout()
            enabled = QCheckBox('Enabled'); enabled.setChecked(self.settings.value(f'timer_{kind}_enabled', False, type=bool))
            time_input = QTimeEdit(); time_input.setDisplayFormat('HH:mm')
            stored_time = self.settings.value(f'timer_{kind}_time', default_time)
            parsed_time = QTime.fromString(stored_time, 'HH:mm')
            time_input.setTime(parsed_time if parsed_time.isValid() else QTime.fromString(default_time, 'HH:mm'))
            row.addWidget(enabled); row.addStretch(); row.addWidget(time_input)
            panel.layout().addLayout(row)
            panel.layout().addWidget(text('Repeat on', 'muted'))
            weekdays = []
            dayrow = QHBoxLayout()
            saved_days = self.settings.value(f'timer_{kind}_days', '0000000')
            if not isinstance(saved_days, str) or len(saved_days) != 7:
                saved_days = '0000000'
            for i, label in enumerate(('Mon','Tue','Wed','Thu','Fri','Sat','Sun')):
                day = QCheckBox(label); day.setChecked(saved_days[i] == '1')
                weekdays.append(day); dayrow.addWidget(day)
            panel.layout().addLayout(dayrow)
            save = QPushButton(f'Save {kind.upper()} schedule'); save.setObjectName('primary')
            save.clicked.connect(lambda checked=False, k=kind: self._save_schedule(k))
            panel.layout().addWidget(save, alignment=Qt.AlignLeft)
            self.schedule_widgets[kind] = (enabled, time_input, weekdays)
            layout.addWidget(panel)
        self.timer_status = text('No schedule read from the controller yet.', 'muted')
        layout.addWidget(self.timer_status)
        layout.addStretch()
        return self._scroll(page)

    def _sync_clock(self):
        self._send(protocol.clock_frame(datetime.now()), 'Controller clock synchronisation sent')

    def _read_schedules(self):
        if not self.is_connected:
            self._status('Connect to your LED strip first')
            return
        self._timer_read_pending = {'on','off'}
        self.timer_status.setText('Waiting for controller schedule notifications…')
        self._send(protocol.timer_read_frame(), 'Schedule read request sent')
        QTimer.singleShot(4500, self._finish_timer_read)

    def _finish_timer_read(self):
        if self._timer_read_pending:
            missing = ', '.join(sorted(self._timer_read_pending))
            self.timer_status.setText(f'No valid readback for: {missing}. The controller may not return both schedules.')
            self._timer_read_pending.clear()

    def _timer_notification(self, data):
        state = protocol.parse_timer_notification(data)
        if not state or state.kind not in self._timer_read_pending:
            return
        enabled, time_input, days = self.schedule_widgets[state.kind]
        enabled.setChecked(state.enabled)
        time_input.setTime(QTime(state.hour, state.minute))
        for checkbox, selected in zip(days, state.weekdays):
            checkbox.setChecked(selected)
        self._persist_schedule(state.kind)
        self._timer_read_pending.discard(state.kind)
        self.timer_status.setText('Controller schedule received: ' + state.kind.upper() +
                                  (' (both received)' if not self._timer_read_pending else ''))

    def _persist_schedule(self, kind):
        enabled, time_input, days = self.schedule_widgets[kind]
        self.settings.setValue(f'timer_{kind}_enabled', enabled.isChecked())
        self.settings.setValue(f'timer_{kind}_time', time_input.time().toString('HH:mm'))
        self.settings.setValue(f'timer_{kind}_days', ''.join('1' if d.isChecked() else '0' for d in days))

    def _save_schedule(self, kind):
        enabled, time_input, days = self.schedule_widgets[kind]
        selected = [d.isChecked() for d in days]
        if enabled.isChecked() and not any(selected):
            QMessageBox.warning(self, 'Select weekdays', 'Select at least one weekday for an enabled schedule.')
            return
        t = time_input.time()
        frame = protocol.timer_frame(kind, enabled.isChecked(), selected, t.hour(), t.minute())
        if self._send_many([protocol.clock_frame(datetime.now()), frame],
                           f'{kind.upper()} schedule command sent (hardware confirmation pending)'):
            self._persist_schedule(kind)
            self.timer_status.setText(f'{kind.upper()} schedule sent. Use Read device schedules to verify if supported.')

    def _settings(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(0,0,0,0); layout.setSpacing(18)
        panel = card(); panel.layout().addWidget(text('STRIP CONFIGURATION','eyebrow'))
        panel.layout().addWidget(text('Fine-tune your hardware','section'))
        panel.layout().addWidget(text('These settings are only transmitted when you press Apply. LUNA never overwrites them on connection.', 'muted'))
        panel.layout().addSpacing(10)
        panel.layout().addWidget(text('LED pixel count','body'))
        row = QHBoxLayout(); self.pixel_count = QSpinBox(); self.pixel_count.setRange(8,300)
        self.pixel_count.setValue(max(8, min(300, self.settings.value('pixel_count', 60, type=int))))
        row.addWidget(self.pixel_count,1); set_pixels = QPushButton('Apply pixel count'); set_pixels.setObjectName('primary')
        set_pixels.clicked.connect(self._apply_pixels)
        row.addWidget(set_pixels); panel.layout().addLayout(row)
        panel.layout().addSpacing(10); panel.layout().addWidget(text('Channel order','body'))
        row2 = QHBoxLayout(); self.channel_order = QComboBox(); self.channel_order.addItems(['RGB','RBG','GRB','GBR','BRG','BGR'])
        self.channel_order.setCurrentIndex(max(0, min(5, self.settings.value('channel_order', 0, type=int))))
        row2.addWidget(self.channel_order,1); set_order = QPushButton('Apply channel order'); set_order.setObjectName('primary')
        set_order.clicked.connect(self._apply_order)
        row2.addWidget(set_order); panel.layout().addLayout(row2)
        layout.addWidget(panel)
        note = card(); note.layout().addWidget(text('ABOUT YOUR CONTROLLER','eyebrow'))
        note.layout().addWidget(text('GATT--DEMO  •  Service FFF0  •  Write FFF3','body'))
        note.layout().addWidget(text('Independent pixel colour control has not been confirmed. Pixel count controls the active strip length, not independently coloured zones.', 'muted'))
        layout.addWidget(note); layout.addStretch()
        return self._scroll(page)

    def _apply_pixels(self):
        if self._send(protocol.pixel_count_frame(self.pixel_count.value()), 'Pixel-count command sent'):
            self.settings.setValue('pixel_count', self.pixel_count.value())

    def _apply_order(self):
        if self._send(protocol.channel_order_frame(self.channel_order.currentIndex()), 'Channel-order command sent'):
            self.settings.setValue('channel_order', self.channel_order.currentIndex())

    def _render_saved_colours(self):
        # Rebuild only this small palette; no existing device settings are touched.
        while self.saved_colours_grid.count():
            item = self.saved_colours_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.saved_colours_empty.setVisible(not self.saved_colours)
        for index, entry in enumerate(self.saved_colours):
            name, colour = entry['name'], entry['hex']
            panel = QFrame(); panel.setObjectName('savedColour')
            line = QHBoxLayout(panel)
            line.setContentsMargins(10, 8, 8, 8); line.setSpacing(7)
            swatch = QPushButton('')
            swatch.setFixedSize(38, 38)
            swatch.setToolTip(f'Apply {name} ({colour})')
            swatch.setStyleSheet(f'background:{colour}; border:2px solid #ffffff50; border-radius:11px; padding:0;')
            swatch.clicked.connect(lambda checked=False, c=colour: self._set_colour(c))
            line.addWidget(swatch)
            apply = QPushButton(f'{name}\n{colour}')
            apply.setObjectName('savedColourApply')
            apply.setToolTip(f'Apply {name} ({colour})')
            apply.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            apply.clicked.connect(lambda checked=False, c=colour: self._set_colour(c))
            line.addWidget(apply, 1)
            rename = QPushButton('✎'); rename.setObjectName('savedColourAction')
            rename.setToolTip(f'Rename {name}')
            rename.clicked.connect(lambda checked=False, i=index: self._rename_saved_colour(i))
            line.addWidget(rename)
            remove = QPushButton('×'); remove.setObjectName('savedColourAction')
            remove.setToolTip(f'Delete {name}')
            remove.clicked.connect(lambda checked=False, i=index: self._delete_saved_colour(i))
            line.addWidget(remove)
            self.saved_colours_grid.addWidget(panel, index // 2, index % 2)
        self.saved_colours_grid.setColumnStretch(0, 1)
        self.saved_colours_grid.setColumnStretch(1, 1)
        self._render_dashboard_palette()

    def _render_dashboard_palette(self):
        while self.dashboard_palette_grid.count():
            item = self.dashboard_palette_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.dashboard_palette_empty.setVisible(not self.saved_colours)
        for index, entry in enumerate(self.saved_colours[:6]):
            colour = entry['hex']
            button = QPushButton(entry['name'])
            button.setToolTip(f'Apply {entry["name"]} ({colour})')
            button.setStyleSheet(
                f'QPushButton {{ background:#222537; border:2px solid {colour}; '
                'border-radius:11px; padding:11px 8px; color:#f3f0ff; }} '
                'QPushButton:hover { background:#36364d; }'
            )
            button.clicked.connect(lambda checked=False, c=colour: self._set_colour(c))
            self.dashboard_palette_grid.addWidget(button, index // 3, index % 3)
        for col in range(3):
            self.dashboard_palette_grid.setColumnStretch(col, 1)

    def _persist_saved_colours(self, updated):
        # QSettings uses the same organisation/app identifiers as v0.3.
        # Do not alter colour, brightness, pixel count or any other key.
        self.settings.setValue('saved_colours_v1', dump_palette(updated))
        self.settings.sync()
        if self.settings.status() != QSettings.Status.NoError:
            QMessageBox.warning(self, 'Unable to save colours',
                                'LUNA could not write your saved palette to its settings file. '
                                'Please check the permissions of your user configuration directory.')
            return False
        self.saved_colours = load_palette(self.settings.value('saved_colours_v1', '[]'))
        self._render_saved_colours()
        return True

    def _save_current_colour(self):
        colour = normalise_hex(self.colour)
        if not colour:
            return
        existing = next((e for e in self.saved_colours if e['hex'] == colour), None)
        if existing:
            QMessageBox.information(self, 'Already saved',
                                    f'{colour} is already saved as "{existing["name"]}". '
                                    'Use the pencil button to rename it.')
            return
        name, ok = QInputDialog.getText(self, 'Save colour',
                                        f'Name for {colour}:', text='My colour')
        if not ok:
            return
        name = clean_name(name, colour)
        if self._persist_saved_colours([*self.saved_colours, {'name': name, 'hex': colour}]):
            self._status(f'Saved {name} ({colour}) to your personal palette')

    def _rename_saved_colour(self, index):
        if not 0 <= index < len(self.saved_colours):
            return
        original = self.saved_colours[index]
        name, ok = QInputDialog.getText(self, 'Rename saved colour',
                                        f'Name for {original["hex"]}:', text=original['name'])
        if not ok:
            return
        updated = [dict(entry) for entry in self.saved_colours]
        updated[index]['name'] = clean_name(name, original['hex'])
        if self._persist_saved_colours(updated):
            self._status('Saved colour renamed')

    def _delete_saved_colour(self, index):
        if not 0 <= index < len(self.saved_colours):
            return
        entry = self.saved_colours[index]
        answer = QMessageBox.question(self, 'Delete saved colour',
                                      f'Remove "{entry["name"]}" ({entry["hex"]}) from your saved colours?',
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        if self._persist_saved_colours([entry for i, entry in enumerate(self.saved_colours) if i != index]):
            self._status('Saved colour deleted (LED colour unchanged)')

    def _apply_theme(self, colour):
        theme = theme_for_colour(colour)
        if theme.selected == self._last_theme_colour:
            return
        self.setStyleSheet(stylesheet(theme))
        self.theme_hex.setText(theme.selected)
        self._last_theme_colour = theme.selected

    def _flush_theme_preview(self):
        self._apply_theme(self._pending_theme_colour)

    def _display_colour(self, colour):
        """Preview without saving settings or sending any Bluetooth commands."""
        self.hex_field.setText(colour)
        self.current_hex.setText(colour.upper())
        self.colour_orb.set_colour(colour)
        self.orb.set_colour(colour)

    def _preview_colour(self, colour):
        if not colour.isValid():
            return
        self._pending_theme_colour = colour.name()
        self._display_colour(self._pending_theme_colour)
        self.theme_preview_timer.start()

    def _set_colour(self, colour):
        value = QColor(colour)
        if not value.isValid():
            return
        self.colour = value.name()
        self.settings.setValue('colour', self.colour)
        self.theme_preview_timer.stop()
        self._display_colour(self.colour)
        self._apply_theme(self.colour)
        # Preserve the existing single colour packet. No extra BLE commands
        # are generated by the adaptive UI theme.
        self._send(protocol.colour_frame(self.colour))

    def _apply_hex(self):
        raw = self.hex_field.text().strip()
        if len(raw.lstrip('#')) != 6 or not QColor(raw).isValid():
            QMessageBox.warning(self,'Invalid colour','Enter a six-digit HEX colour, for example #9568FF.')
            return
        self._set_colour(raw)

    def _pick_colour(self):
        # A non-native dialog allows the UI theme/orbs to preview the shade as
        # it changes. Only pressing OK applies the colour to the strip.
        dialog = QColorDialog(QColor(self.colour), self)
        dialog.setWindowTitle('Choose a colour')
        dialog.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
        dialog.currentColorChanged.connect(self._preview_colour)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._set_colour(dialog.currentColor().name())
        else:
            self.theme_preview_timer.stop()
            self._display_colour(self.colour)
            self._apply_theme(self.colour)

    def _brightness_changed(self, value):
        self.last_brightness = value
        self.settings.setValue('brightness', value)
        self.brightness_value.setText(f'{round(value/10)}%')
        if self.is_connected and self.power_on:
            self.brightness_timer.start()

    def _toggle_power(self):
        if not self.is_connected:
            self._status('Connect to your LED strip first')
            return
        self.power_on = not self.power_on
        self.power_button.setText('Turn lights off' if self.power_on else 'Turn lights on')
        # Power is a single, standalone packet; do not race it with brightness.
        self.brightness_timer.stop()
        self.speed_timer.stop()
        if not self.power_on and self.audio_capture.active:
            self._stop_audio()
        self._send(protocol.power_frame(self.power_on))

    def _toggle_connection(self):
        self.connection_button.setEnabled(False)
        if self.is_connected:
            self._submit(self._disconnect())
        else:
            self._submit(self._connect())

    def _connection_changed(self, connected):
        self.is_connected = connected
        if not connected and self.audio_capture.active:
            self._stop_audio()
        self.connection_button.setEnabled(True)
        self.connection_button.setText('Disconnect' if connected else 'Connect device')
        self.side_status.setText('●  Connected' if connected else '●  Disconnected')
        self.device_status.setText('Online  •  Bluetooth LE' if connected else 'Offline  •  Waiting for connection')
        # Do not alter the strip state merely because LUNA connected.

    def _status(self, message):
        self.footer.setText(message)
        if 'Searching' in message:
            self.side_status.setText('●  Searching…')

    def _error(self, message):
        self.connection_button.setEnabled(True)
        self._status('Error: ' + message)
        QMessageBox.warning(self,'LUNA — Bluetooth',message)

    def closeEvent(self, event):
        self.brightness_timer.stop()
        self.speed_timer.stop()
        if self.audio_capture.active:
            self._stop_audio()
        if self.player:
            self.player.stop()
        if self.controller.connected:
            future = asyncio.run_coroutine_threadsafe(self.controller.disconnect(),self.loop)
            try:
                future.result(timeout=2)
            except Exception:
                pass
        self.loop.call_soon_threadsafe(self.loop.stop)
        event.accept()
