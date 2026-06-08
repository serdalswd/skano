from PySide6.QtCore import QThread, Signal
from PIL import Image
from core.dithering import process_image, process_gif


class ProcessWorker(QThread):
    finished = Signal(object)   # PIL Image or list of frames
    progress = Signal(int)
    error = Signal(str)

    def __init__(self, params: dict):
        super().__init__()
        self.params = params
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            p = self.params
            image = p['image']
            is_animated = getattr(image, 'n_frames', 1) > 1

            if is_animated:
                frames, durations = process_gif(
                    image,
                    algorithm=p['algorithm'],
                    scale=p['scale'],
                    palette=p['palette'],
                    contrast=p['contrast'],
                    brightness=p['brightness'],
                    midtones=p['midtones'],
                    blur=p['blur'],
                    invert=p['invert'],
                    progress_cb=lambda v: self.progress.emit(v),
                )
                if not self._cancelled:
                    self.finished.emit((frames, durations))
            else:
                result = process_image(
                    image,
                    algorithm=p['algorithm'],
                    scale=p['scale'],
                    palette=p['palette'],
                    contrast=p['contrast'],
                    brightness=p['brightness'],
                    midtones=p['midtones'],
                    blur=p['blur'],
                    invert=p['invert'],
                )
                if not self._cancelled:
                    self.progress.emit(100)
                    self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
