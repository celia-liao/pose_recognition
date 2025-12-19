# -*- coding: utf-8 -*-
# Time : 2025/12/7 1:08
# User : l'r's
# Software: PyCharm
# File : main.py
"""
主程式入口 - Main Entry Point
啟動姿勢偵測應用程式
"""

import sys
from PyQt5.QtWidgets import QApplication
from ui_module import PostureDetectionApp


def main():
    """主函式"""
    app = QApplication(sys.argv)

    # 設定應用程式樣式
    app.setStyle('Fusion')

    # 建立並顯示主視窗
    window = PostureDetectionApp()
    window.show()

    # 執行應用程式
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
