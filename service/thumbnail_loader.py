import os
import queue
from typing import Callable

from PyQt5.QtCore import Qt, QObject, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QImage, QPixmap

class ThumbnailWorker(QThread):
    loaded = pyqtSignal(str, QImage)

    def __init__(self, queue: queue.Queue):
        super().__init__()
        self.queue = queue
        self.running = True

    def run(self):
        while self.running:
            try:
                image_path, thumbnail_path = self.queue.get(timeout=1)  # 等待新任务
            except queue.Empty:
                continue
            
            self.thumbnail(image_path, thumbnail_path)
            self.queue.task_done()

    def thumbnail(self, image_path: str, thumbnail_path: str):
        # print(f'____tstart {image_path}')
        thumbnail = QImage(image_path).scaledToHeight(80, Qt.SmoothTransformation)
        thumbnail.save(thumbnail_path)
        self.loaded.emit(thumbnail_path, thumbnail)


class ThumbnailLoader(QObject):
    def __init__(self, thumbnail_dir: str):
        super().__init__()
        self.thumbnail_dir = thumbnail_dir
        self.pending_dict: dict[str, Callable[[QIcon], None]] = {}

        self.worker_queue = queue.Queue()
        self.worker = ThumbnailWorker(self.worker_queue)
        self.worker.loaded.connect(self.on_thumbnailed)
        self.worker.start()
    
    def request_thumbnail(self, image_path: str, callback: Callable[[QIcon], None]):
        thumbnail_path = os.path.join(self.thumbnail_dir, image_path.replace('_','-').replace(os.sep,'_'))
        if os.path.exists(thumbnail_path):
            callback(QIcon(thumbnail_path))
        else:
            self.pending_dict[thumbnail_path] = callback
            self.worker_queue.put((image_path, thumbnail_path))

    
    def on_thumbnailed(self, thumbnail_path: str, thumbnail: QImage):
        # print(f'____tget {thumbnail_path}')
        if self.pending_dict[thumbnail_path] is None:
            return
        self.pending_dict[thumbnail_path](QIcon(QPixmap.fromImage(thumbnail)))
        del self.pending_dict[thumbnail_path]