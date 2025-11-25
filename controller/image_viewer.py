from PyQt5.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsItem
)
from PyQt5.QtCore import Qt, QRectF, QSize, QEvent
from PyQt5.QtGui import QPixmap, QPainter, QWheelEvent

from typing import Union

class ImageViewer(QGraphicsView):
    """ 图片查看器 """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.zoomInFactors = 1.0
        self.maxZoomInFactors = 2.0
        self.keepRatioWhenSwitchImage = True

        # 创建场景
        self.graphicsScene = QGraphicsScene()

        # 图片
        self.pixmap = QPixmap()
        self.pixmapItem = QGraphicsPixmapItem(self.pixmap)
        self.displayedImageSize = QSize(0, 0)

        # 初始化小部件
        self.__initWidget()

    def __initWidget(self):
        """ 初始化小部件 """

        # 隐藏滚动条
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 以鼠标所在位置为锚点进行缩放
        self.setTransformationAnchor(self.AnchorUnderMouse)

        # 平滑缩放
        self.pixmapItem.setTransformationMode(Qt.SmoothTransformation)
        self.setRenderHints(QPainter.Antialiasing |
                            QPainter.SmoothPixmapTransform)

        # 设置场景
        self.graphicsScene.addItem(self.pixmapItem) # 一个场景能有多个item
        self.setScene(self.graphicsScene) # 设置舞台

        # 启用捏合手势
        self.grabGesture(Qt.PinchGesture)

    # 处理鼠标滚轮
    def wheelEvent(self, e: QWheelEvent):
        """ 滚动鼠标滚轮缩放图片 """
        ang = e.angleDelta().y()
        monument = ang / 500 + 1
        
        if ang > 2:
            self.zoomIn(factor=monument)
        elif ang < -2:
            self.zoomOut(factor=monument)

    # 处理捏合手势
    def event(self, event):    
        def gestureEvent(event):
            pinch = event.gesture(Qt.PinchGesture)
            if pinch:
                changeFlags = pinch.changeFlags()
                if changeFlags & pinch.ScaleFactorChanged:
                    factor = pinch.scaleFactor()
                    if factor > 1.0:
                        self.zoomIn(factor=factor)
                    else:
                        self.zoomOut(factor=factor)
                return True
            return False

        if event.type() == QEvent.Gesture:
            return gestureEvent(event)
        return super().event(event)

    def resizeEvent(self, e):
        """ 缩放图片 """
        super().resizeEvent(e)

        if self.zoomInFactors != 1.0:
            return

        # 调整图片大小
        ratio = self.__getScaleRatio()
        self.displayedImageSize = self.pixmap.size()*ratio
        if ratio < 1:
            self.fitInView(self.pixmapItem, Qt.KeepAspectRatio)
        else:
            self.resetTransform()

    def setImage(self, imagePath: Union[str, QPixmap]):
        """ 设置显示的图片 """
        # 刷新图片
        if isinstance(imagePath, str):
            self.pixmap = QPixmap(imagePath)
        else:
            self.pixmap = imagePath
        self.pixmapItem.setPixmap(self.pixmap)

        # 调整图片大小
        if not self.keepRatioWhenSwitchImage:
            self.resetTransform()
            self.setSceneRect(QRectF(self.pixmap.rect()))
            ratio = self.__getScaleRatio()
            self.displayedImageSize = self.pixmap.size()*ratio
            if ratio < 1:
                self.fitInView(self.pixmapItem, Qt.KeepAspectRatio)

    def resetTransform(self):
        """ 重置变换 """
        super().resetTransform()
        self.zoomInFactors = 1.0
        self.__setDragEnabled(False)

    def __isEnableDrag(self):
        """ 根据图片的尺寸决定是否启动拖拽功能 """
        v = self.verticalScrollBar().maximum() > 0
        h = self.horizontalScrollBar().maximum() > 0
        return v or h

    def __setDragEnabled(self, isEnabled: bool):
        """ 设置拖拽是否启动 """
        self.setDragMode(
            self.ScrollHandDrag if isEnabled else self.NoDrag)

    def __getScaleRatio(self):
        """ 获取显示的图像和原始图像的缩放比例 """
        if self.pixmap.isNull():
            return 1

        pw = self.pixmap.width()
        ph = self.pixmap.height()
        rw = min(1, self.width()/pw)
        rh = min(1, self.height()/ph)
        return min(rw, rh)

    def fitInView(self, item: QGraphicsItem, mode=Qt.KeepAspectRatio):
        """ 缩放场景使其适应窗口大小 """
        super().fitInView(item, mode)
        self.displayedImageSize = self.__getScaleRatio()*self.pixmap.size()
        self.zoomInFactors = 1.0

    def zoomIn(self, factor=1.1, viewAnchor=QGraphicsView.AnchorUnderMouse):
        """ 放大图像 """
        pw = self.pixmap.width()
        w = self.displayedImageSize.width() * self.zoomInFactors
        if w / pw >= self.maxZoomInFactors:
            return

        self.setTransformationAnchor(viewAnchor)

        self.zoomInFactors *= factor
        self.scale(factor, factor)
        self.__setDragEnabled(self.__isEnableDrag())

        # 还原 anchor
        self.setTransformationAnchor(self.AnchorUnderMouse)

    def zoomOut(self, factor=1/1.1, viewAnchor=QGraphicsView.AnchorUnderMouse):
        """ 缩小图像 """
        if self.zoomInFactors == 1.0 and not self.__isEnableDrag():
            return

        self.setTransformationAnchor(viewAnchor)

        self.zoomInFactors *= factor

        # 原始图像的大小
        pw = self.pixmap.width()
        ph = self.pixmap.height()

        # 实际显示的图像宽度
        w = self.displayedImageSize.width() * self.zoomInFactors
        h = self.displayedImageSize.height() * self.zoomInFactors

        if pw > self.width() or ph > self.height():
            # 在窗口尺寸小于原始图像时禁止继续缩小图像比窗口还小
            if w <= self.width() and h <= self.height():
                self.fitInView(self.pixmapItem)
            else:
                self.scale(factor, factor)
        else:
            # 在窗口尺寸大于图像时不允许缩小的比原始图像小
            if w <= pw:
                self.resetTransform()
            else:
                self.scale(factor, factor)

        self.__setDragEnabled(self.__isEnableDrag())

        # 还原 anchor
        self.setTransformationAnchor(self.AnchorUnderMouse)