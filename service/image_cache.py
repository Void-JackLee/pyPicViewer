import os
import queue
import exifread
from typing import Callable, Dict, Any
from PyQt5.QtCore import QThread, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap

class CacheWorker(QObject):
    image_loaded = pyqtSignal(str, QImage, dict)
    before_load = pyqtSignal(str)  # 向主线程询问

    def __init__(self, file_queue: queue.Queue, do_cache_queue: queue.Queue):
        super().__init__()
        self.file_queue: queue.Queue = file_queue
        self.do_cache_queue = do_cache_queue
        self.running = True

    def run(self):
        while self.running:
            try:
                file_path = self.file_queue.get(timeout=1)  # 等待新任务
            except queue.Empty:
                continue

            # 向主线程询问是否需要加载
            self.before_load.emit(file_path)
            # 等待主线程返回结果
            need_load = self.do_cache_queue.get()

            if need_load:
                print('do cache:', file_path)
                image = QImage(file_path)
                # 读取exif
                with open(file_path, 'rb') as f:
                    tags = exifread.process_file(f)
                self.image_loaded.emit(file_path, image, tags)
            self.file_queue.task_done()

class ImageCache(QObject):
    def __init__(self):
        super().__init__()
        self.image_cache: dict[str, QImage] = {}
        self.exif_cache: dict[str, Dict[str, Any]] = {}
        self.cache_set: set = set([])
        self.requested_file: tuple[str, Callable[[QPixmap], None]] = None
        
        self.file_queue = queue.Queue()
        self.do_cache_queue = queue.Queue(maxsize=1)
        self.thread = QThread()
        self.worker = CacheWorker(self.file_queue, self.do_cache_queue)

        self.worker.moveToThread(self.thread)
        self.worker.before_load.connect(self._on_need_cache)
        self.worker.image_loaded.connect(self._on_cache_done)
        self.thread.started.connect(self.worker.run)
        
        self.thread.start()

    def init(self, cur_dir):
        self.clear_cache()
        self.cur_dir = cur_dir
        self.requested_file = None

    def clear_cache(self):
        self.cache_set = set([])
        del_names = list(self.image_cache.keys())
        for name in del_names:
            print('remove cache:', name)
            del self.image_cache[name]
            del self.exif_cache[name]
        self.image_cache = {}
        self.exif_cache = {}

    def cache_files(self, valid_names: list[str]):
        print(f'start caching...')
        
        _valid_names = set(valid_names)
        del_names = []
        for file_name in self.image_cache:
            if file_name not in _valid_names:
                del_names.append(file_name)
        for file_name in del_names:
            print('remove cache:', file_name)
            del self.image_cache[file_name]
            del self.exif_cache[file_name]

        # TODO: 避免重复加载
        cache_set = set([os.path.join(self.cur_dir, file_name) for file_name in valid_names])
        self.cache_set = cache_set

        for fileName in valid_names:
            self._cache_file(fileName)

    def _cache_file(self, file_name):
        if file_name in self.image_cache:
            return
        print(f'put {file_name}')
        self.file_queue.put(os.path.join(self.cur_dir, file_name))

    @pyqtSlot(str)
    def _on_need_cache(self, file_path: str):
        # 主线程判断是否需要加载
        need_load = file_path in self.cache_set and os.path.basename(file_path) not in self.image_cache
        # 返回结果给子线程
        self.do_cache_queue.put(need_load)

    def _on_cache_done(self, file_path: str, image: QImage, exif_tags: Dict[str, Any]):
        if file_path not in self.cache_set:
            return
        file_name = os.path.basename(file_path)
        if file_name in self.image_cache:
            return
        # print(f'get {file_name}')
        self.image_cache[file_name] = image
        self.exif_cache[file_name] = exif_tags
        if self.requested_file is not None:
            file_name = self.requested_file[0]
            if file_name in self.image_cache:
                print(f'done return {file_name}')
                self.requested_file[1](QPixmap.fromImage(self.image_cache[file_name]), self.exif_cache[file_name])
                self.requested_file = None

    def request_image(self, image_name: str, callback: Callable[[QPixmap, Dict[str, Any]], None]):
        if image_name in self.image_cache:
            print(f'directly return {image_name}')
            callback(QPixmap.fromImage(self.image_cache[image_name]), self.exif_cache[image_name])
        else:
            print(f'wait {image_name}')
            self.requested_file = (image_name, callback)