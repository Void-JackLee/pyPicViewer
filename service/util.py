import os
import rawpy
import imageio

from pathlib import Path
from PyQt5.QtGui import QImage

def calc_exif_number(fstr, number=1):
    fstr = str(fstr)
    idx = fstr.find('/')
    if idx == -1:
        return fstr
    a = fstr[:idx]
    b = fstr[idx+1:]
    return f'{float(a)/float(b):.{number}f}'

NORMAL_FORMAT = ['.png', '.jpg', '.jpeg', '.tif', '.bmp']
RAW_FORMAT = ['.cr2', '.cr3', '.nef', '.arw', '.orf', '.dng']

NORMAL_FORMAT_SET = set(NORMAL_FORMAT)

def read_image(file_path):
    if Path(file_path).suffix.lower() in NORMAL_FORMAT_SET:
        return QImage(file_path)
    # read raw
    print(f'read as raw of {os.path.basename(file_path)}')
    with rawpy.imread(file_path) as raw:
        thumb = raw.extract_thumb()
        if thumb.format == rawpy.ThumbFormat.JPEG:
            # JPEG 预览
            img = imageio.imread(thumb.data)
        elif thumb.format == rawpy.ThumbFormat.BITMAP:
            # BITMAP 预览，直接用 numpy 数组
            img = thumb.data
        else:
            # 没有预览图，用解码后的图片
            img = raw.postprocess()
    # numpy 数组转 QImage
    height, width, channel = img.shape
    bytes_per_line = channel * width
    return QImage(img.data, width, height, bytes_per_line, QImage.Format_RGB888).copy()