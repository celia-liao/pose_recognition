# -*- coding: utf-8 -*-
# Time : 2025/12/7 17:32 
# User : l'r's
# Software: PyCharm 
# File : config_module.py
"""
配置模块 - Configuration Module
存储所有配置参数和常量
"""


class Config:
    """配置类"""

    # 默认阈值
    DEFAULT_SIDE_NECK_THRESHOLD = 50
    DEFAULT_SIDE_TORSO_THRESHOLD = 20
    
    # 头部姿态检测阈值（脸部中心到肩膀中心的距离）
    DEFAULT_HEAD_DOWN_DISTANCE = 80   # 距离小于此值判断为勾头（低头）
    DEFAULT_HEAD_UP_DISTANCE = 150    # 距离大于此值判断为仰头
    
    # 报警时间阈值（秒）
    DEFAULT_WARNING_TIME = 2.0  # 异常持续超过此时间就立即发送警报

    # 久坐提醒（分钟）
    DEFAULT_SITTING_MINUTES = 30  # 连续坐姿/有人出现累计达到该时长则提醒

    # 默认检测参数
    DEFAULT_SKIP_FRAMES = 1
    DEFAULT_RESOLUTION = (640, 480)

    # 分辨率选项
    RESOLUTION_OPTIONS = ["320x240", "480x360", "640x480", "800x600", "1280x720"]

    # 颜色定义 (BGR格式)
    COLOR_BLUE = (255, 127, 0)
    COLOR_RED = (50, 50, 255)
    COLOR_GREEN = (127, 255, 0)
    COLOR_DARK_BLUE = (127, 20, 0)
    COLOR_LIGHT_GREEN = (127, 233, 100)
    COLOR_YELLOW = (0, 255, 255)
    COLOR_PINK = (255, 0, 255)

    # MediaPipe配置
    MP_MIN_DETECTION_CONFIDENCE = 0.8
    MP_MIN_TRACKING_CONFIDENCE = 0.6
    MP_MODEL_COMPLEXITY = 1

    # 视角判断阈值
    FRONT_VIEW_THRESHOLD = 100  # 肩膀距离大于此值为正面

    # UI配置
    WINDOW_WIDTH = 1400
    WINDOW_HEIGHT = 900
    TIMER_INTERVAL = 30  # 毫秒