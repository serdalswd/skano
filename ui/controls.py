from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSlider,
    QCheckBox, QPushButton, QGroupBox, QScrollArea, QFrame, QSizePolicy,
    QSpinBox, QColorDialog
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QPainter, QBrush, QPen, QPixmap
from core.dithering import ALGORITHM_NAMES
from core.palette import BUILTIN_PALETTES


class ColorSwatch(QFrame):
    clicked = Signal(int)

    def __init__(self, index: int, color: tuple, parent=None):
        super().__init__(parent)
        self.index = index
        self.color = color
        self.setFixedSize(24, 24)
        self.setFrameShape(QFrame.Shape.Box)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

    def _update_style(self):
        r, g, b = self.color
        self.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); border: 1px solid #555; border-radius: 3px;"
        )

    def set_color(self, color: tuple):
        self.color = color
        self._update_style()

    def mousePressEvent(self, event):
        self.clicked.emit(self.index)


class PaletteWidget(QWidget):
    palette_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._palette = list(BUILTIN_PALETTES["Black & White"])
        self._swatches = []
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)

        # Preset selector
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Preset:"))
        self._preset_combo = QComboBox()
        self._preset_combo.addItems(list(BUILTIN_PALETTES.keys()) + ["Custom"])
        self._preset_combo.currentTextChanged.connect(self._on_preset_changed)
        preset_row.addWidget(self._preset_combo, 1)
        self._layout.addLayout(preset_row)

        # Swatches row
        self._swatches_container = QWidget()
        self._swatches_layout = QHBoxLayout(self._swatches_container)
        self._swatches_layout.setContentsMargins(0, 0, 0, 0)
        self._swatches_layout.setSpacing(4)
        self._swatches_layout.addStretch()
        self._layout.addWidget(self._swatches_container)

        # Action buttons
        btn_row = QHBoxLayout()
        self._add_btn = QPushButton("+")
        self._add_btn.setFixedSize(28, 28)
        self._add_btn.setToolTip("Add color")
        self._add_btn.clicked.connect(self._add_color)
        self._remove_btn = QPushButton("−")
        self._remove_btn.setFixedSize(28, 28)
        self._remove_btn.setToolTip("Remove last color")
        self._remove_btn.clicked.connect(self._remove_last)
        btn_row.addWidget(self._add_btn)
        btn_row.addWidget(self._remove_btn)
        btn_row.addStretch()
        self._layout.addLayout(btn_row)

        self._rebuild_swatches()

    def _rebuild_swatches(self):
        for s in self._swatches:
            s.setParent(None)
        self._swatches.clear()

        layout = self._swatches_layout
        while layout.count() > 1:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, color in enumerate(self._palette):
            swatch = ColorSwatch(i, color)
            swatch.clicked.connect(self._edit_color)
            self._swatches.append(swatch)
            layout.insertWidget(layout.count() - 1, swatch)

    def _on_preset_changed(self, name: str):
        if name in BUILTIN_PALETTES:
            self._palette = list(BUILTIN_PALETTES[name])
            self._rebuild_swatches()
            self.palette_changed.emit(self._palette)

    def _edit_color(self, index: int):
        r, g, b = self._palette[index]
        initial = QColor(r, g, b)
        color = QColorDialog.getColor(initial, self, "Pick Color")
        if color.isValid():
            self._palette[index] = (color.red(), color.green(), color.blue())
            self._swatches[index].set_color(self._palette[index])
            self._preset_combo.setCurrentText("Custom")
            self.palette_changed.emit(self._palette)

    def _add_color(self):
        color = QColorDialog.getColor(QColor(128, 128, 128), self, "Add Color")
        if color.isValid():
            self._palette.append((color.red(), color.green(), color.blue()))
            self._rebuild_swatches()
            self._preset_combo.setCurrentText("Custom")
            self.palette_changed.emit(self._palette)

    def _remove_last(self):
        if len(self._palette) > 1:
            self._palette.pop()
            self._rebuild_swatches()
            self.palette_changed.emit(self._palette)

    def get_palette(self) -> list:
        return list(self._palette)

    def set_palette(self, palette: list):
        self._palette = list(palette)
        self._rebuild_swatches()
        self._preset_combo.setCurrentText("Custom")


def _make_slider(min_val: int, max_val: int, default: int, step: int = 1) -> QSlider:
    s = QSlider(Qt.Orientation.Horizontal)
    s.setMinimum(min_val)
    s.setMaximum(max_val)
    s.setValue(default)
    s.setSingleStep(step)
    return s


def _make_section(title: str) -> QGroupBox:
    box = QGroupBox(title)
    box.setStyleSheet(
        "QGroupBox { font-weight: bold; border: 1px solid #3a3a3a; border-radius: 6px;"
        " margin-top: 8px; padding-top: 6px; color: #cccccc; }"
        "QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }"
    )
    return box


class ControlsPanel(QWidget):
    settings_changed = Signal()

    DEBOUNCE_MS = 250

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(260)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        vbox = QVBoxLayout(inner)
        vbox.setContentsMargins(10, 10, 10, 10)
        vbox.setSpacing(10)

        # --- Dithering section ---
        dith_box = _make_section("Dithering")
        dith_layout = QVBoxLayout(dith_box)
        dith_layout.setSpacing(6)

        dith_layout.addWidget(QLabel("Algorithm"))
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(ALGORITHM_NAMES)
        self.algo_combo.currentIndexChanged.connect(self._on_change)
        dith_layout.addWidget(self.algo_combo)

        scale_row = QHBoxLayout()
        scale_row.addWidget(QLabel("Scale"))
        self.scale_slider = _make_slider(1, 16, 1)
        self.scale_label = QLabel("1")
        self.scale_label.setFixedWidth(22)
        self.scale_slider.valueChanged.connect(lambda v: (
            self.scale_label.setText(str(v)), self._on_change()
        ))
        scale_row.addWidget(self.scale_slider, 1)
        scale_row.addWidget(self.scale_label)
        dith_layout.addLayout(scale_row)

        vbox.addWidget(dith_box)

        # --- Adjustments section ---
        adj_box = _make_section("Adjustments")
        adj_layout = QVBoxLayout(adj_box)
        adj_layout.setSpacing(6)

        self.contrast_slider = self._labeled_slider(adj_layout, "Contrast", 50, 200, 100, "%")
        self.brightness_slider = self._labeled_slider(adj_layout, "Brightness", 50, 200, 100, "%")
        self.midtones_slider = self._labeled_slider(adj_layout, "Midtones", -50, 50, 0, "")
        self.blur_slider = self._labeled_slider(adj_layout, "Blur", 0, 20, 0, "")

        reset_btn = QPushButton("Reset All")
        reset_btn.clicked.connect(self._reset_adjustments)
        adj_layout.addWidget(reset_btn)

        vbox.addWidget(adj_box)

        # --- Palette section ---
        pal_box = _make_section("Palette")
        pal_layout = QVBoxLayout(pal_box)
        self.palette_widget = PaletteWidget()
        self.palette_widget.palette_changed.connect(self._on_change)
        pal_layout.addWidget(self.palette_widget)
        vbox.addWidget(pal_box)

        # --- Output section ---
        out_box = _make_section("Output")
        out_layout = QVBoxLayout(out_box)

        self.invert_check = QCheckBox("Invert Output")
        self.invert_check.stateChanged.connect(self._on_change)
        out_layout.addWidget(self.invert_check)

        self.preview_check = QCheckBox("Live Preview")
        self.preview_check.setChecked(True)
        self.preview_check.stateChanged.connect(self._on_change)
        out_layout.addWidget(self.preview_check)

        vbox.addWidget(out_box)
        vbox.addStretch()

        scroll.setWidget(inner)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self.settings_changed)

    def _labeled_slider(self, layout, label: str, min_v: int, max_v: int,
                        default: int, unit: str) -> QSlider:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        slider = _make_slider(min_v, max_v, default)
        val_label = QLabel(str(default) + unit)
        val_label.setFixedWidth(36)
        slider.valueChanged.connect(lambda v: (
            val_label.setText(str(v) + unit), self._on_change()
        ))
        row.addWidget(slider, 1)
        row.addWidget(val_label)
        layout.addLayout(row)
        return slider

    def _on_change(self):
        self._debounce.start(self.DEBOUNCE_MS)

    def _reset_adjustments(self):
        for s, v in [
            (self.contrast_slider, 100),
            (self.brightness_slider, 100),
            (self.midtones_slider, 0),
            (self.blur_slider, 0),
        ]:
            s.blockSignals(True)
            s.setValue(v)
            s.blockSignals(False)
        self._on_change()

    def get_settings(self) -> dict:
        return {
            "algorithm": self.algo_combo.currentText(),
            "scale": self.scale_slider.value(),
            "palette": self.palette_widget.get_palette(),
            "contrast": self.contrast_slider.value() / 100.0,
            "brightness": self.brightness_slider.value() / 100.0,
            "midtones": self.midtones_slider.value() / 50.0,
            "blur": self.blur_slider.value() / 2.0,
            "invert": self.invert_check.isChecked(),
            "preview_enabled": self.preview_check.isChecked(),
        }
