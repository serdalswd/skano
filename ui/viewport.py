from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QSizePolicy
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPixmap, QImage, QColor, QBrush, QWheelEvent, QMouseEvent
from PIL import Image
import numpy as np


def pil_to_qpixmap(image: Image.Image) -> QPixmap:
    img_rgb = image.convert("RGBA")
    data = img_rgb.tobytes("raw", "RGBA")
    qimg = QImage(data, img_rgb.width, img_rgb.height, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg)


class ImageViewport(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item = QGraphicsPixmapItem()
        self._scene.addItem(self._pixmap_item)

        from PySide6.QtGui import QPainter
        self.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setBackgroundBrush(QBrush(QColor(31, 31, 31)))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(400, 300)

        self._zoom_level = 1.0
        self._has_image = False

        self._init_placeholder()

    def _init_placeholder(self):
        self._scene.setSceneRect(QRectF(0, 0, 600, 400))
        self._pixmap_item.setVisible(False)

    def set_image(self, image: Image.Image):
        pixmap = pil_to_qpixmap(image)
        self._pixmap_item.setPixmap(pixmap)
        self._pixmap_item.setVisible(True)
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        if not self._has_image:
            self._has_image = True
            self.fit_in_view()

    def clear_image(self):
        self._pixmap_item.setVisible(False)
        self._has_image = False
        self._init_placeholder()

    def fit_in_view(self):
        if self._pixmap_item.isVisible():
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
            self._zoom_level = self.transform().m11()

    def zoom_in(self):
        self._zoom(1.25)

    def zoom_out(self):
        self._zoom(0.8)

    def zoom_reset(self):
        self.resetTransform()
        self._zoom_level = 1.0

    def _zoom(self, factor: float):
        new_zoom = self._zoom_level * factor
        if 0.05 <= new_zoom <= 50.0:
            self.scale(factor, factor)
            self._zoom_level = new_zoom

    def wheelEvent(self, event: QWheelEvent):
        factor = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
        self._zoom(factor)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._has_image and self._zoom_level == 1.0:
            self.fit_in_view()
