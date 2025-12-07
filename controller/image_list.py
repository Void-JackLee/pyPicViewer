import os
from pathlib import Path

from PyQt5 import uic
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QListWidget, QListWidgetItem, QWidget, QListView, 
)

from service.thumbnail_loader import ThumbnailLoader

from service.util import THUMBNAIL_DIR

# class ListItem(QWidget):
#     def __init__(self, img_path, img_name, parent=None):
#         super().__init__(parent=parent)
#         uic.loadUi('ui/image_list_item.ui', self)

#         self.imageName.setText(img_name)

class ImageList(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.THUMBNAIL_DIR = THUMBNAIL_DIR
        self.thumbnail_loader = ThumbnailLoader(self.THUMBNAIL_DIR)
        
    def set_list(self, dir_path, file_list):
        self.clear()
        self.setIconSize(QSize(150, 80))
        for i, img_name in enumerate(file_list):
            item = QListWidgetItem(self)
            item.setSizeHint(QSize(150, 100))  # 适当调整高度
            item.setData(Qt.UserRole, img_name)
            item.setText(img_name)
            self.set_thumbnail(dir_path, img_name, item)
            # widget = ListItem(os.path.join(dirPath, img_name), img_name)
            self.addItem(item)
            # self.setItemWidget(item, widget)
        # print('__done set')
    
    def set_thumbnail(self, dir_path: str, img_name: str, item):
        def set_icon(icon: QIcon):
            try: # 防止被删掉
                item.setIcon(icon)
            except:
                pass
        self.thumbnail_loader.request_thumbnail(os.path.join(dir_path, img_name), set_icon)
        