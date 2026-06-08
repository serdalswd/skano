import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QFileDialog, QStatusBar,
    QProgressBar, QSizePolicy, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QKeySequence, QShortcut
from PIL import Image

from ui.viewport import ImageViewport
from ui.controls import ControlsPanel
from core.processor import ProcessWorker


STYLESHEET = """
QMainWindow, QWidget {
    background-color: #1e1e1e;
    color: #dddddd;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 12px;
}
QScrollArea { background: transparent; border: none; }
QPushButton {
    background-color: #333333;
    border: none;
    padding: 6px 14px;
    border-radius: 6px;
    color: #dddddd;
}
QPushButton:hover { background-color: #444444; }
QPushButton:pressed { background-color: #555555; }
QPushButton:disabled { background-color: #2a2a2a; color: #666666; }
QPushButton#primary {
    background-color: #3a5fa0;
}
QPushButton#primary:hover { background-color: #4a70b8; }
QComboBox {
    background-color: #2c2c2c;
    border: 1px solid #3a3a3a;
    border-radius: 5px;
    padding: 4px 8px;
    color: #dddddd;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background-color: #2c2c2c;
    border: 1px solid #3a3a3a;
    selection-background-color: #3a5fa0;
    color: #dddddd;
}
QSlider::groove:horizontal {
    background: #3a3a3a;
    height: 3px;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #5e89ed;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #b0b0b0;
    border: 1px solid #555;
    width: 13px;
    height: 13px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover { background: #dddddd; }
QSlider::groove:horizontal:disabled { background: #2a2a2a; }
QSlider::sub-page:horizontal:disabled { background: #444444; }
QSlider::handle:horizontal:disabled { background: #444444; }
QLabel { color: #cccccc; }
QCheckBox { color: #cccccc; }
QCheckBox::indicator {
    width: 14px; height: 14px;
    background: #2c2c2c;
    border: 1px solid #555;
    border-radius: 3px;
}
QCheckBox::indicator:checked {
    background: #5e89ed;
    border-color: #5e89ed;
}
QScrollBar:vertical {
    background: transparent; width: 10px; margin: 0;
}
QScrollBar::handle:vertical {
    background: #444; border-radius: 5px; min-height: 20px; margin: 2px;
}
QScrollBar::handle:vertical:hover { background: #666; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: transparent; height: 10px; margin: 0;
}
QScrollBar::handle:horizontal {
    background: #444; border-radius: 5px; min-width: 20px; margin: 2px;
}
QScrollBar::handle:horizontal:hover { background: #666; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QProgressBar {
    background: #2c2c2c;
    border: none;
    border-radius: 3px;
    height: 4px;
}
QProgressBar::chunk {
    background: #5e89ed;
    border-radius: 3px;
}
QStatusBar { color: #888888; font-size: 11px; }
"""


class DropZone(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("Drop an image or GIF here\nor click  Open")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "color: #555555; font-size: 16px; border: 2px dashed #3a3a3a;"
            " border-radius: 12px; background: #1a1a1a;"
        )
        self.setMinimumSize(400, 300)


class MainWindow(QMainWindow):
    APP_NAME = "DitherApp"
    VERSION = "1.0.0"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{self.APP_NAME}  v{self.VERSION}")
        self.resize(1100, 700)
        self.setMinimumSize(700, 500)
        self.setAcceptDrops(True)
        self.setStyleSheet(STYLESHEET)

        self._source_image = None
        self._result_image = None
        self._result_frames = None
        self._result_durations = None
        self._worker = None
        self._is_animated = False

        self._build_ui()
        self._connect_signals()
        self._setup_shortcuts()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Left: viewport area
        left = QWidget()
        left.setStyleSheet("background: #1a1a1a;")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # Toolbar
        toolbar = QWidget()
        toolbar.setFixedHeight(44)
        toolbar.setStyleSheet("background: #252525; border-bottom: 1px solid #333;")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(10, 6, 10, 6)
        tb_layout.setSpacing(8)

        self.open_btn = QPushButton("Open")
        self.open_btn.setFixedHeight(30)
        self.export_btn = QPushButton("Export")
        self.export_btn.setObjectName("primary")
        self.export_btn.setFixedHeight(30)
        self.export_btn.setEnabled(False)

        self.fit_btn = QPushButton("Fit")
        self.fit_btn.setFixedSize(40, 30)
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setFixedSize(30, 30)
        self.zoom_out_btn = QPushButton("−")
        self.zoom_out_btn.setFixedSize(30, 30)

        title_lbl = QLabel(f"<b>{self.APP_NAME}</b>")
        title_lbl.setStyleSheet("color: #aaaaaa; font-size: 13px;")

        tb_layout.addWidget(self.open_btn)
        tb_layout.addWidget(self.export_btn)
        tb_layout.addSpacing(10)
        tb_layout.addWidget(self.zoom_out_btn)
        tb_layout.addWidget(self.fit_btn)
        tb_layout.addWidget(self.zoom_in_btn)
        tb_layout.addStretch()
        tb_layout.addWidget(title_lbl)

        left_layout.addWidget(toolbar)

        # Viewport stack (viewport + drop zone overlay)
        self._viewport_container = QWidget()
        vc_layout = QVBoxLayout(self._viewport_container)
        vc_layout.setContentsMargins(0, 0, 0, 0)

        self.viewport = ImageViewport()
        self._drop_zone = DropZone()

        vc_layout.addWidget(self.viewport)
        vc_layout.addWidget(self._drop_zone)

        self.viewport.hide()

        left_layout.addWidget(self._viewport_container, 1)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(4)
        self._progress.hide()
        left_layout.addWidget(self._progress)

        root.addWidget(left, 1)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setStyleSheet("color: #333333;")
        root.addWidget(divider)

        # Right: controls
        self.controls = ControlsPanel()
        root.addWidget(self.controls)

        # Status bar
        self._status = QStatusBar()
        self._status.showMessage("Ready — open an image to start")
        self.setStatusBar(self._status)

    def _connect_signals(self):
        self.open_btn.clicked.connect(self._open_file)
        self.export_btn.clicked.connect(self._export_file)
        self.fit_btn.clicked.connect(self.viewport.fit_in_view)
        self.zoom_in_btn.clicked.connect(self.viewport.zoom_in)
        self.zoom_out_btn.clicked.connect(self.viewport.zoom_out)
        self.controls.settings_changed.connect(self._trigger_process)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self._open_file)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._export_file)
        QShortcut(QKeySequence("Ctrl+Shift+E"), self).activated.connect(self._export_file)
        QShortcut(QKeySequence("F"), self).activated.connect(self.viewport.fit_in_view)
        QShortcut(QKeySequence("="), self).activated.connect(self.viewport.zoom_in)
        QShortcut(QKeySequence("-"), self).activated.connect(self.viewport.zoom_out)

    # --- Drag & Drop ---
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self._load_image(path)

    # --- File Operations ---
    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tiff *.tif);;All Files (*)"
        )
        if path:
            self._load_image(path)

    def _load_image(self, path: str):
        try:
            img = Image.open(path)
            img.load()
            self._source_image = img
            self._is_animated = getattr(img, 'n_frames', 1) > 1

            self._drop_zone.hide()
            self.viewport.show()

            self.export_btn.setEnabled(True)

            fname = os.path.basename(path)
            if self._is_animated:
                n = img.n_frames
                self._status.showMessage(f"{fname}  —  {img.size[0]}×{img.size[1]}  |  {n} frames (GIF)")
            else:
                self._status.showMessage(f"{fname}  —  {img.size[0]}×{img.size[1]}")

            # Show original immediately, then process
            preview = img.convert("RGB")
            if self._is_animated:
                img.seek(0)
                preview = img.copy().convert("RGB")
            self.viewport.set_image(preview)
            self._trigger_process()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open image:\n{e}")

    def _export_file(self):
        if self._result_image is None and self._result_frames is None:
            return

        if self._is_animated and self._result_frames:
            path, _ = QFileDialog.getSaveFileName(
                self, "Export GIF", "output.gif", "GIF (*.gif)"
            )
            if path:
                try:
                    frames = self._result_frames
                    durations = self._result_durations
                    frames[0].save(
                        path, save_all=True, append_images=frames[1:],
                        loop=0, duration=durations, optimize=False
                    )
                    self._status.showMessage(f"Saved: {os.path.basename(path)}")
                except Exception as e:
                    QMessageBox.critical(self, "Export Error", str(e))
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, "Export Image", "output.png",
                "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp);;All Files (*)"
            )
            if path:
                try:
                    self._result_image.save(path)
                    self._status.showMessage(f"Saved: {os.path.basename(path)}")
                except Exception as e:
                    QMessageBox.critical(self, "Export Error", str(e))

    # --- Processing ---
    def _trigger_process(self):
        if self._source_image is None:
            return
        settings = self.controls.get_settings()
        if not settings["preview_enabled"]:
            return
        self._start_worker(settings)

    def _start_worker(self, settings: dict):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(200)

        img = self._source_image.copy()

        # For preview performance: limit size when image is large
        if not self._is_animated:
            w, h = img.size
            max_dim = 800
            if max(w, h) > max_dim:
                ratio = max_dim / max(w, h)
                img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

        params = {
            "image": img,
            "algorithm": settings["algorithm"],
            "scale": settings["scale"],
            "palette": settings["palette"],
            "contrast": settings["contrast"],
            "brightness": settings["brightness"],
            "midtones": settings["midtones"],
            "blur": settings["blur"],
            "invert": settings["invert"],
        }

        self._worker = ProcessWorker(params)
        self._worker.finished.connect(self._on_process_done)
        self._worker.progress.connect(self._on_progress)
        self._worker.error.connect(self._on_process_error)
        self._progress.setValue(0)
        self._progress.show()
        self._worker.start()

    def _on_progress(self, value: int):
        self._progress.setValue(value)

    def _on_process_done(self, result):
        self._progress.hide()
        if isinstance(result, tuple):
            frames, durations = result
            self._result_frames = frames
            self._result_durations = durations
            self._result_image = None
            if frames:
                self.viewport.set_image(frames[0])
            self._status.showMessage(
                f"Done  —  {len(frames)} frames processed"
            )
        else:
            self._result_image = result
            self._result_frames = None
            self.viewport.set_image(result)
            w, h = result.size
            self._status.showMessage(f"Done  —  {w}×{h}")

    def _on_process_error(self, msg: str):
        self._progress.hide()
        self._status.showMessage(f"Error: {msg}")
