# -*- coding: utf-8 -*-
# Time : 2025/12/7 17:32
# User : l'r's
# Software: PyCharm
# File : ui_module.py
"""
介面模組 - UI Module
處理所有 PyQt5 介面相關的程式碼（繁體中文／台灣用語）
"""

import cv2
import time
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGroupBox, QComboBox,
    QLineEdit, QFileDialog, QSpinBox, QDoubleSpinBox, QMessageBox
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap, QFont

from config_module import Config
from detector_module import PostureDetector
from config_manager import ConfigManager


class PostureDetectionApp(QMainWindow):
    """姿勢偵測應用程式主視窗"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("智慧坐姿偵測系統 - Posture Detection System")
        self.setGeometry(100, 100, Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT)

        # 初始化變數
        self.cap = None
        self.detector = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.is_running = False

        # 偵測參數
        self.skip_frames = Config.DEFAULT_SKIP_FRAMES
        self.resolution = Config.DEFAULT_RESOLUTION

        # 久坐提醒參數/狀態
        self.sitting_minutes = Config.DEFAULT_SITTING_MINUTES
        self._sit_seconds = 0.0
        self._sit_last_ts = None
        self._no_person_streak = 0
        self._sit_reminder_played = False

        # 設定管理
        self.config_manager = ConfigManager()

        # 建立 UI（先建立元件，再載入設定，避免屬性不存在）
        self.init_ui()

        # 載入設定（會更新元件的值）
        self.load_config()

        # 初始化偵測器（使用載入的設定）
        self.init_detector()

    def init_ui(self):
        """初始化使用者介面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # ===================== 左側 - 影像顯示與控制區 =====================
        left_layout = QVBoxLayout()

        # 影像顯示區
        self.video_label = QLabel()
        self.video_label.setMinimumSize(800, 600)
        self.video_label.setMaximumSize(1000, 750)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #2b2b2b;
                border: 2px solid #555;
                border-radius: 10px;
                color: white;
                font-size: 16px;
            }
        """)
        self.video_label.setText("攝影機尚未啟動\nCamera Not Started")
        left_layout.addWidget(self.video_label)

        # 輸入來源選擇
        source_layout = QHBoxLayout()
        source_label = QLabel("輸入來源：")
        source_label.setStyleSheet("font-size: 12px; font-weight: bold;")

        self.source_combo = QComboBox()
        self.source_combo.addItems(["攝影機 Camera", "影片檔 Video File"])
        self.source_combo.setStyleSheet("""
            QComboBox {
                padding: 5px;
                font-size: 12px;
                border: 1px solid #ccc;
                border-radius: 3px;
            }
        """)
        self.source_combo.currentIndexChanged.connect(self.on_source_changed)

        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText("選擇影片檔路徑…")
        self.file_path_input.setEnabled(False)
        self.file_path_input.setStyleSheet("""
            QLineEdit {
                padding: 5px;
                font-size: 12px;
                border: 1px solid #ccc;
                border-radius: 3px;
            }
        """)

        self.browse_button = QPushButton("瀏覽")
        self.browse_button.setEnabled(False)
        self.browse_button.setStyleSheet("""
            QPushButton {
                background-color: #9E9E9E;
                color: white;
                font-size: 12px;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:enabled {
                background-color: #607D8B;
            }
            QPushButton:enabled:hover {
                background-color: #546E7A;
            }
        """)
        self.browse_button.clicked.connect(self.browse_video_file)

        source_layout.addWidget(source_label)
        source_layout.addWidget(self.source_combo, 1)
        source_layout.addWidget(self.file_path_input, 2)
        source_layout.addWidget(self.browse_button)
        left_layout.addLayout(source_layout)

        # 控制按鈕
        button_layout = QHBoxLayout()

        self.start_button = QPushButton("啟動偵測 Start")
        self.start_button.setFont(QFont("Arial", 12, QFont.Bold))
        self.start_button.setMinimumHeight(50)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.start_button.clicked.connect(self.toggle_detection)

        self.reset_button = QPushButton("重置統計 Reset")
        self.reset_button.setFont(QFont("Arial", 12, QFont.Bold))
        self.reset_button.setMinimumHeight(50)
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        self.reset_button.clicked.connect(self.reset_statistics)

        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.reset_button)
        left_layout.addLayout(button_layout)

        main_layout.addLayout(left_layout, 3)

        # ===================== 右側 - 狀態與設定區 =====================
        right_layout = QVBoxLayout()

        # 參數設定
        config_group = QGroupBox("參數設定 Configuration")
        config_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #666;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        config_layout = QVBoxLayout()

        # 解析度
        resolution_layout = QHBoxLayout()
        resolution_label = QLabel("解析度：")
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(Config.RESOLUTION_OPTIONS)
        self.resolution_combo.setCurrentText("640x480")
        self.resolution_combo.currentTextChanged.connect(self.on_resolution_changed)
        resolution_layout.addWidget(resolution_label)
        resolution_layout.addWidget(self.resolution_combo)
        config_layout.addLayout(resolution_layout)

        # 偵測頻率
        skip_layout = QHBoxLayout()
        skip_label = QLabel("偵測頻率（每 N 幀）：")
        self.skip_spinbox = QSpinBox()
        self.skip_spinbox.setRange(1, 10)
        self.skip_spinbox.setValue(1)
        self.skip_spinbox.setSuffix(" 幀")
        self.skip_spinbox.valueChanged.connect(self.on_skip_frames_changed)
        skip_layout.addWidget(skip_label)
        skip_layout.addWidget(self.skip_spinbox)
        config_layout.addLayout(skip_layout)

        # 脖子前傾警戒角度（原：側面頸部閾值）
        side_neck_layout = QHBoxLayout()
        side_neck_label = QLabel("低頭／脖子前傾警戒角度：")
        self.side_neck_spinbox = QDoubleSpinBox()
        self.side_neck_spinbox.setRange(20, 80)
        self.side_neck_spinbox.setValue(Config.DEFAULT_SIDE_NECK_THRESHOLD)
        self.side_neck_spinbox.setSuffix("°")
        self.side_neck_spinbox.valueChanged.connect(self.on_threshold_changed)
        side_neck_layout.addWidget(side_neck_label)
        side_neck_layout.addWidget(self.side_neck_spinbox)
        config_layout.addLayout(side_neck_layout)

        # 身體前傾警戒角度（原：側面躯干閾值）
        side_torso_layout = QHBoxLayout()
        side_torso_label = QLabel("駝背／身體前傾警戒角度：")
        self.side_torso_spinbox = QDoubleSpinBox()
        self.side_torso_spinbox.setRange(5, 40)
        self.side_torso_spinbox.setValue(Config.DEFAULT_SIDE_TORSO_THRESHOLD)
        self.side_torso_spinbox.setSuffix("°")
        self.side_torso_spinbox.valueChanged.connect(self.on_threshold_changed)
        side_torso_layout.addWidget(side_torso_label)
        side_torso_layout.addWidget(self.side_torso_spinbox)
        config_layout.addLayout(side_torso_layout)

        # 不良姿勢持續多久才提醒（原：报警时间阈值）
        warning_time_layout = QHBoxLayout()
        warning_time_label = QLabel("姿勢不良持續多久才提醒：")
        self.warning_time_spinbox = QDoubleSpinBox()
        self.warning_time_spinbox.setRange(0.5, 10.0)
        self.warning_time_spinbox.setSingleStep(0.5)
        self.warning_time_spinbox.setDecimals(1)
        self.warning_time_spinbox.setValue(Config.DEFAULT_WARNING_TIME)
        self.warning_time_spinbox.setSuffix(" 秒")
        self.warning_time_spinbox.valueChanged.connect(self.on_warning_time_changed)
        warning_time_layout.addWidget(warning_time_label)
        warning_time_layout.addWidget(self.warning_time_spinbox)
        config_layout.addLayout(warning_time_layout)

        # 久坐提醒（分鐘）
        sitting_layout = QHBoxLayout()
        sitting_label = QLabel("久坐提醒（分鐘）：")
        self.sitting_minutes_spinbox = QSpinBox()
        self.sitting_minutes_spinbox.setRange(1, 600)
        self.sitting_minutes_spinbox.setValue(self.sitting_minutes)
        self.sitting_minutes_spinbox.setSuffix(" 分鐘")
        self.sitting_minutes_spinbox.valueChanged.connect(self.on_sitting_minutes_changed)
        sitting_layout.addWidget(sitting_label)
        sitting_layout.addWidget(self.sitting_minutes_spinbox)
        config_layout.addLayout(sitting_layout)

        # 設定檔 存檔/載入
        config_button_layout = QHBoxLayout()
        self.save_config_button = QPushButton("儲存設定")
        self.save_config_button.clicked.connect(self.save_config)
        self.save_config_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        self.load_config_button = QPushButton("載入設定")
        self.load_config_button.clicked.connect(self.load_config)
        self.load_config_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)

        config_button_layout.addWidget(self.save_config_button)
        config_button_layout.addWidget(self.load_config_button)
        config_layout.addLayout(config_button_layout)

        config_group.setLayout(config_layout)
        right_layout.addWidget(config_group)

        # 即時狀態
        status_group = QGroupBox("即時狀態 Status")
        status_group.setStyleSheet(config_group.styleSheet())
        status_layout = QVBoxLayout()

        self.posture_status_label = QLabel("姿勢狀態：等待偵測…")
        self.posture_status_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.posture_status_label.setAlignment(Qt.AlignCenter)
        self.posture_status_label.setStyleSheet("""
            padding: 15px;
            border-radius: 5px;
            background-color: #f0f0f0;
        """)

        self.view_type_label = QLabel("視角：--")
        self.angle_info_label = QLabel("角度資訊：--")

        for label in [self.view_type_label, self.angle_info_label]:
            label.setFont(QFont("Arial", 10))
            label.setStyleSheet("padding: 3px;")
            label.setWordWrap(True)

        status_layout.addWidget(self.posture_status_label)
        status_layout.addWidget(self.view_type_label)
        status_layout.addWidget(self.angle_info_label)
        status_group.setLayout(status_layout)
        right_layout.addWidget(status_group)

        # 辨識結果（統計）
        results_group = QGroupBox("辨識結果 Recognition Results")
        results_group.setStyleSheet(config_group.styleSheet())
        results_layout = QVBoxLayout()

        self.correct_time_label = QLabel("正確坐姿時間：0.0 秒")
        self.incorrect_time_label = QLabel("不良坐姿時間：0.0 秒")
        self.total_sitting_time_label = QLabel("總坐姿時間：0.0 秒")

        for label in [self.correct_time_label, self.incorrect_time_label, self.total_sitting_time_label]:
            label.setFont(QFont("Arial", 10))
            label.setStyleSheet("padding: 3px;")

        results_layout.addWidget(self.correct_time_label)
        results_layout.addWidget(self.incorrect_time_label)
        results_layout.addWidget(self.total_sitting_time_label)
        results_group.setLayout(results_layout)
        right_layout.addWidget(results_group)

        # 使用提示（白話版：讓「閾值」不再難懂）
        tips_group = QGroupBox("使用提示 Tips")
        tips_group.setStyleSheet(config_group.styleSheet())
        tips_layout = QVBoxLayout()

        tips_text = QLabel(
            "• 角度越大＝姿勢歪得越多\n"
            "• 超過「警戒角度」才會被判定為姿勢不良\n"
            "• 想要少提醒 → 把角度調大\n"
            "• 想要更嚴格 → 把角度調小\n"
            "• 綠色＝姿勢正常，紅色＝需要調整"
        )
        tips_text.setWordWrap(True)
        tips_text.setStyleSheet("padding: 8px; font-size: 9px;")
        tips_layout.addWidget(tips_text)
        tips_group.setLayout(tips_layout)
        right_layout.addWidget(tips_group)

        right_layout.addStretch()
        main_layout.addLayout(right_layout, 1)

    # ==================== 事件處理方法 ====================

    def on_resolution_changed(self, text):
        """解析度變更"""
        w, h = map(int, text.split('x'))
        self.resolution = (w, h)
        if self.cap and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)

    def on_skip_frames_changed(self, value):
        """偵測頻率變更"""
        self.skip_frames = int(value)

    def on_threshold_changed(self):
        """警戒角度變更"""
        # 啟動階段 load_config() 會觸發 valueChanged；此時 detector 可能尚未初始化
        if not self.detector:
            return
        self.detector.update_thresholds(
            self.side_neck_spinbox.value(),
            self.side_torso_spinbox.value()
        )

    def on_source_changed(self, index):
        """輸入來源切換"""
        is_video_file = (index == 1)
        self.file_path_input.setEnabled(is_video_file)
        self.browse_button.setEnabled(is_video_file)

        if not is_video_file:
            self.file_path_input.clear()

    def browse_video_file(self):
        """瀏覽並選擇影片檔"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇影片檔 Select Video File",
            "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.m4v);;All Files (*.*)"
        )
        if file_path:
            self.file_path_input.setText(file_path)

    def on_warning_time_changed(self, value):
        """提醒延遲時間變更"""
        if self.detector:
            self.detector.update_warning_time(float(value))

    def save_config(self):
        """儲存目前設定到檔案"""
        config_dict = {
            'side_neck_threshold': self.side_neck_spinbox.value(),
            'side_torso_threshold': self.side_torso_spinbox.value(),
            'warning_time': self.warning_time_spinbox.value(),
            'sitting_minutes': self.sitting_minutes_spinbox.value(),
            'resolution': self.resolution,
            'skip_frames': self.skip_frames,
        }

        if self.config_manager.save_config(config_dict):
            QMessageBox.information(self, "儲存成功", "設定已儲存到 config.txt")

    def load_config(self):
        """從檔案載入設定"""
        config_dict = self.config_manager.load_config()

        if config_dict:
            # 更新 UI 元件
            if 'side_neck_threshold' in config_dict:
                self.side_neck_spinbox.setValue(config_dict['side_neck_threshold'])
            if 'side_torso_threshold' in config_dict:
                self.side_torso_spinbox.setValue(config_dict['side_torso_threshold'])
            if 'warning_time' in config_dict:
                self.warning_time_spinbox.setValue(config_dict['warning_time'])
            if 'sitting_minutes' in config_dict:
                self.sitting_minutes_spinbox.setValue(int(config_dict['sitting_minutes']))
            if 'resolution' in config_dict:
                self.resolution = config_dict['resolution']
                resolution_str = f"{self.resolution[0]}x{self.resolution[1]}"
                idx = self.resolution_combo.findText(resolution_str)
                if idx >= 0:
                    self.resolution_combo.setCurrentIndex(idx)
            if 'skip_frames' in config_dict:
                self.skip_frames = int(config_dict['skip_frames'])
                self.skip_spinbox.setValue(self.skip_frames)

            # 更新偵測器
            if self.detector:
                self.detector.update_thresholds(
                    self.side_neck_spinbox.value(),
                    self.side_torso_spinbox.value()
                )
                self.detector.update_warning_time(self.warning_time_spinbox.value())

            QMessageBox.information(self, "載入成功", "設定已從 config.txt 載入")
        else:
            QMessageBox.information(self, "提示", "找不到設定檔或讀取失敗，已使用預設值")

    def on_sitting_minutes_changed(self, value: int):
        """久坐提醒分鐘數變更"""
        self.sitting_minutes = int(value)

    def _reset_sit_timer(self):
        """重置久坐計時（例如：連續多次偵測不到人）"""
        self._sit_seconds = 0.0
        self._sit_last_ts = None
        self._sit_reminder_played = False

    def _update_sit_timer(self, posture_info):
        """
        更新久坐計時與提醒：
        - 有人時累計坐姿時間（只累計「有人」的時間）
        - 連續 10 次偵測不到人則清零重新計時
        - 達到設定分鐘數播放 output2.wav（每次計時週期只播一次）
        """
        if not posture_info:
            return

        person_detected = bool(posture_info.get('person_detected', False))

        if person_detected:
            self._no_person_streak = 0
            now = time.time()
            if self._sit_last_ts is None:
                self._sit_last_ts = now
            else:
                self._sit_seconds += max(0.0, now - self._sit_last_ts)
                self._sit_last_ts = now
        else:
            self._no_person_streak += 1
            self._sit_last_ts = None
            if self._no_person_streak >= 10:
                self._no_person_streak = 0
                self._reset_sit_timer()
                return

        threshold_seconds = float(self.sitting_minutes) * 60.0
        print(threshold_seconds)
        print(self._sit_reminder_played)
        print(self._sit_seconds)
        if threshold_seconds > 0 and (not self._sit_reminder_played) and self._sit_seconds >= threshold_seconds:
            
            if self.detector and hasattr(self.detector, 'audio_player'):
                self.detector.audio_player.play_audio('sitting')
            self._sit_reminder_played = False
            # 重置计时器，让提醒可以周期性触发
            self._sit_seconds = 0.0
            self._sit_last_ts = time.time()  # 重新开始计时

    # ==================== 偵測控制方法 ====================

    def toggle_detection(self):
        """切換偵測狀態"""
        if not self.is_running:
            self.start_detection()
        else:
            self.stop_detection()

    def start_detection(self):
        """啟動偵測"""
        # 依輸入來源初始化影像擷取
        if self.source_combo.currentIndex() == 0:
            # 攝影機
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.video_label.setText("無法開啟攝影機\nCannot open camera")
                return
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        else:
            # 影片檔
            video_path = self.file_path_input.text().strip()
            if not video_path:
                self.video_label.setText("請先選擇影片檔\nPlease select a video file")
                return

            self.cap = cv2.VideoCapture(video_path)
            if not self.cap.isOpened():
                self.video_label.setText("無法開啟影片檔\nCannot open video file")
                return

        self.is_running = True
        self.start_button.setText("停止偵測 Stop")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)

        # 偵測中禁用部分設定控件（避免變更造成不一致）
        self.source_combo.setEnabled(False)
        self.browse_button.setEnabled(False)
        self.file_path_input.setEnabled(False)
        self.resolution_combo.setEnabled(False)
        self.warning_time_spinbox.setEnabled(False)

        self.timer.start(Config.TIMER_INTERVAL)

    def stop_detection(self):
        """停止偵測"""
        self.is_running = False
        self.timer.stop()

        if self.cap:
            self.cap.release()
            self.cap = None

        # 停止後重置久坐計時
        self._no_person_streak = 0
        self._reset_sit_timer()

        self.video_label.setText("偵測已停止\nDetection Stopped")
        self.start_button.setText("啟動偵測 Start")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        # 重新啟用設定控件
        self.source_combo.setEnabled(True)
        self.resolution_combo.setEnabled(True)
        self.warning_time_spinbox.setEnabled(True)
        if self.source_combo.currentIndex() == 1:
            self.browse_button.setEnabled(True)
            self.file_path_input.setEnabled(True)

    def update_frame(self):
        """更新影像幀"""
        ret, frame = self.cap.read()
        if not ret:
            if self.source_combo.currentIndex() == 1:
                self.stop_detection()
                self.video_label.setText("影片播放完畢\nVideo Finished")
            return

        processed_frame, posture_info = self.detector.process_frame(frame, self.skip_frames)

        self.display_frame(processed_frame)

        if posture_info and posture_info.get('is_correct') is not None:
            self.update_posture_info(posture_info)

        # 久坐計時/提醒（與是否「坐姿正確」無關，只要偵測到人就累計）
        self._update_sit_timer(posture_info)

        self.update_statistics()

    def display_frame(self, frame):
        """顯示影像幀"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.video_label.setPixmap(scaled_pixmap)

    def update_posture_info(self, posture_info):
        """更新姿勢資訊顯示"""
        if posture_info.get('view_type') == 'front':
            self.posture_status_label.setText("正面視角（不做姿勢判斷）")
            self.posture_status_label.setStyleSheet("""
                padding: 15px;
                border-radius: 5px;
                background-color: #f0f0f0;
                color: black;
            """)
        elif posture_info.get('is_correct'):
            self.posture_status_label.setText("✓ 坐姿正常")
            self.posture_status_label.setStyleSheet("""
                padding: 15px;
                border-radius: 5px;
                background-color: #4CAF50;
                color: white;
            """)
        else:
            self.posture_status_label.setText("✗ 姿勢不良（請調整）")
            self.posture_status_label.setStyleSheet("""
                padding: 15px;
                border-radius: 5px;
                background-color: #f44336;
                color: white;
            """)

        view_type = "正面 Front" if posture_info.get('view_type') == 'front' else "側面 Side"
        self.view_type_label.setText(f"視角：{view_type}")

        if posture_info.get('view_type') == 'front':
            self.angle_info_label.setText("角度資訊：正面視角不做姿勢判斷")
        else:
            angle_text = (
                f"脖子角度：{posture_info.get('angles', {}).get('neck', 0):.1f}° "
                f"(警戒 < {self.side_neck_spinbox.value():.1f}°)\n"
                f"身體角度：{posture_info.get('angles', {}).get('torso', 0):.1f}° "
                f"(警戒 < {self.side_torso_spinbox.value():.1f}°)"
            )
            self.angle_info_label.setText(angle_text)

    def update_statistics(self):
        """更新辨識結果（累計時間）"""
        total_good_time, total_bad_time, total_sitting_time = self.detector.get_statistics()
        self.correct_time_label.setText(f"正確坐姿時間：{total_good_time:.1f} 秒")
        self.incorrect_time_label.setText(f"不良坐姿時間：{total_bad_time:.1f} 秒")
        self.total_sitting_time_label.setText(f"總坐姿時間：{total_sitting_time:.1f} 秒")

    def reset_statistics(self):
        """重置統計資訊"""
        if self.detector:
            self.detector.reset_statistics()
        self.update_statistics()
        self.posture_status_label.setText("姿勢狀態：統計已重置")
        self.posture_status_label.setStyleSheet("""
            padding: 15px;
            border-radius: 5px;
            background-color: #f0f0f0;
        """)

    def init_detector(self):
        """初始化偵測器"""
        self.detector = PostureDetector(
            side_neck_threshold=self.side_neck_spinbox.value(),
            side_torso_threshold=self.side_torso_spinbox.value(),
            warning_time=self.warning_time_spinbox.value()
        )

    def closeEvent(self, event):
        """視窗關閉事件"""
        if self.is_running:
            self.stop_detection()
        if self.detector:
            self.detector.release()
        event.accept()
