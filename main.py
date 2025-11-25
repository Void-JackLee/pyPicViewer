import argparse
import sys

from PyQt5.QtWidgets import QApplication

from controller.main_window import MainWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)

    parser = argparse.ArgumentParser(description='Open pic viewer')
    parser.add_argument("dir", help="image file or image dir", default=None, nargs='?')
    args = parser.parse_args()

    win = MainWindow(args.dir)
    win.show()
    sys.exit(app.exec_())