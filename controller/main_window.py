import os
import shutil
import sys

from typing import Dict, Any
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QFileDialog, QLabel
)
from PyQt5.QtGui import QPixmap

from .image_viewer import ImageViewer
from .image_list import ImageList
from service.image_cache import ImageCache
from service.util import calc_exif_number

class MainWindow(QMainWindow):
    def __init__(self, dir_path=None):
        super().__init__()
        # define ui
        self.imageList: ImageList = None
        self.imageViewer: ImageViewer = None
        main_file = getattr(sys.modules['__main__'], '__file__', None)
        uic.loadUi(os.path.join(os.path.dirname(os.path.abspath(main_file)),'ui','main_window.ui'), self, package='controller')

        self.infoLabel = QLabel('')
        self.infoLabel.setAlignment(Qt.AlignCenter)
        self.statusBar().addPermanentWidget(self.infoLabel, 1)

        # connect signals
        self.actionOpen.triggered.connect(lambda: self.open())
        self.actionOpenPath.triggered.connect(lambda: self.open_path())
        self.actionOpenLast.triggered.connect(lambda: self.open_last())
        self.actionReloadPath.triggered.connect(lambda: self.reload_path())
        self.actionClose.triggered.connect(lambda: self._close())
        self.actionDelete.triggered.connect(lambda: self.delete())
        self.actionFit.triggered.connect(lambda: self.fit())
        self.actionRotateRight.triggered.connect(lambda: self.rotateRight())
        self.actionRotateLeft.triggered.connect(lambda: self.rotateLeft())
        self.actionNext.triggered.connect(lambda: self.nextImage())
        self.actionPrevious.triggered.connect(lambda: self.previousImage())
        self.actionLast.triggered.connect(lambda: self.lastImage())
        self.imageList.itemSelectionChanged.connect(self.selectChanged)
    
        # define consts
        self.APP_NAME = 'picv'
        self.VALID_FORMAT = ['.png', '.jpg', '.jpeg', '.tif', '.bmp']
        self.NUMBER_OF_CACHED_IMAGES = 10

        # define props
        self.cur_dir: str = None
        self.selected_image_name: str = None
        self.last_image_name = None
        self.image_name2idx: dict[str, int] = {}
        self.file_list: list[str] = []
        self.file_list_len = 0
        self.image_cache = ImageCache()

        # process dirPath
        if dir_path is not None:
            if os.path.isdir(dir_path):
                self.open_path(dir_path)
            elif os.path.isfile(dir_path):
                self.open(dir_path)
            else:
                print('file not exist!')
                pass
    
    ##### file process start #####
    def init_dir(self, dir_path):
        all_items = os.listdir(dir_path)
        valid_ext = set(self.VALID_FORMAT)
        file_list = [f for f in all_items if os.path.isfile(os.path.join(dir_path, f)) and os.path.splitext(f)[1].lower() in valid_ext]
        file_list.sort()

        self.image_name2idx = {}
        for i, file_name in enumerate(file_list):
            self.image_name2idx[file_name] = i

        self.cur_dir = dir_path
        self.file_list = file_list
        self.file_list_len = len(file_list)
        self.image_cache.init(dir_path)
        self.last_image_name = None

        # 缩略图
        self.imageList.set_list(dir_path, file_list)
        # resize at first image
        self.imageViewer.keepRatioWhenSwitchImage = False

    def open(self, file_path=None):
        if file_path is None:
            file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", f"Image Files ({' '.join([f'*{ext}' for ext in self.VALID_FORMAT])})")
            if file_path == '':
                return
        self.init_dir(os.path.dirname(file_path)) 

        self.select(os.path.basename(file_path))
        self.cache_files()

    def open_path(self, dir_path=None):
        if dir_path is None:
            dir_path = QFileDialog.getExistingDirectory(self, "Open Directory", "")
            if dir_path == '':
                return
        self.init_dir(dir_path)
        if self.file_list_len == 0:
            print('no valid image file found!')
            return
        
        self.select(self.file_list[0])
        self.cache_files()

    def open_last(self):
        with open(os.path.join(self.imageList.THUMBNAIL_DIR, 'last'), 'r', encoding='utf-8') as f:
            last = f.read()
        self.open(last)

    def reload_path(self):
        if self.selected_image_name is None:
            return
        self.open(os.path.join(self.cur_dir, self.selected_image_name))

    def delete(self):
        if self.selected_image_name not in self.image_name2idx:
            return
        cur_idx = self.image_name2idx[self.selected_image_name]

        # perform 'delete' on disk
        del_path = os.path.join(self.cur_dir, 'trash_pic')
        os.makedirs(del_path, exist_ok=True)
        shutil.move(os.path.join(self.cur_dir, self.selected_image_name),del_path)

        # delete cache and update indexs
        for i in range(cur_idx + 1, self.file_list_len):
            self.image_name2idx[self.file_list[i]] -= 1
        del self.image_name2idx[self.selected_image_name]
        del self.file_list[cur_idx]
        self.file_list_len -= 1
        self.imageList.takeItem(cur_idx)

        if self.file_list_len == 0: return
        if cur_idx >= self.file_list_len:
            cur_idx -= 1
        self.selected_image_name = None # 防止last读到空
        self.select(self.file_list[cur_idx])
    
    def _close(self):
        self.imageList.clear()
        self.imageViewer.pixmap = QPixmap()
        self.imageViewer.pixmapItem.setPixmap(self.imageViewer.pixmap)
        self.image_cache.clear_cache()
        self.cur_dir: str = None
        self.selected_image_name: str = None
        self.last_image_name = None
        self.image_name2idx: dict[str, int] = {}
        self.file_list: list[str] = []
        self.file_list_len = 0
        self.infoLabel.setText('')
        self.setWindowTitle('picv')


    ##### file process end #####

    ##### image process start #####
    def cache_files(self):
        cur_idx = self.image_name2idx[self.selected_image_name]
        valid_names = []

        # 不怕重复，因为后续会判断是否需要重新加载
        if self.last_image_name is not None: valid_names.append(self.last_image_name)

        i = cur_idx
        j = cur_idx + 1
        lower_bound = max(0,cur_idx - self.NUMBER_OF_CACHED_IMAGES)
        upper_bound = min(self.file_list_len,cur_idx + self.NUMBER_OF_CACHED_IMAGES + 1)

        while i >= lower_bound or j < upper_bound:
            if i >= lower_bound:
                valid_names.append(self.file_list[i])
            if j < upper_bound:
                valid_names.append(self.file_list[j])
            i -= 1
            j += 1

        self.image_cache.cache_files(valid_names)

    def select(self, image_name):
        self.imageList.item(self.image_name2idx[image_name]).setSelected(True)
        self.imageList.scrollToItem(self.imageList.selectedItems()[0])
        with open(os.path.join(self.imageList.THUMBNAIL_DIR, 'last'), 'w', encoding='utf-8') as f:
            f.write(os.path.join(self.cur_dir, self.selected_image_name))

    def selectChanged(self):
        if len(self.imageList.selectedItems()) == 0:
            return
        self.last_image_name = self.selected_image_name
        cur = self.imageList.selectedItems()[0].data(Qt.UserRole)
        self.selected_image_name = cur
        self.display_image(cur)
        self.cache_files()

    def display_image(self, image_name: str):
        def set_image(image: QPixmap, exif_tags: Dict[str, Any]):
            self.imageViewer.setImage(image)
            # keep current ratio
            self.imageViewer.keepRatioWhenSwitchImage = True

            self.setWindowTitle(f'{self.APP_NAME} - {self.selected_image_name}')
            self.infoLabel.setText(f"当前第{self.image_name2idx[self.selected_image_name] + 1}项，共{self.file_list_len}项; f{calc_exif_number(exif_tags['EXIF FNumber'])} {exif_tags['EXIF ExposureTime']}s iso{exif_tags['EXIF ISOSpeedRatings']} {calc_exif_number(exif_tags['EXIF FocalLength'],2)}mm")
        self.image_cache.request_image(image_name, set_image)
    ##### image process end #####

    ##### edit funtion start #####
    def fit(self):
        if self.selected_image_name is None:
            return
        self.imageViewer.resetAndFit()

    def rotateRight(self):
        if self.selected_image_name is None:
            return
        self.imageViewer.rotateRight()

    def rotateLeft(self):
        if self.selected_image_name is None:
            return
        self.imageViewer.rotateLeft()

    def nextImage(self):
        if self.selected_image_name not in self.image_name2idx:
            return
        idx = self.image_name2idx[self.selected_image_name]
        if idx + 1 < self.file_list_len:
            self.select(self.file_list[idx + 1])

    def previousImage(self):
        if self.selected_image_name not in self.image_name2idx:
            return
        idx = self.image_name2idx[self.selected_image_name]
        if idx - 1 >= 0:
            self.select(self.file_list[idx - 1])

    def lastImage(self):
        if self.last_image_name is None:
            return
        self.select(self.last_image_name)

    ##### edit funtion end #####