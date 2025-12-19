# -*- coding: utf-8 -*-
# Time : 2025/12/7 17:32
# User : l'r's
# Software: PyCharm
# File : detector_module.py
"""
辨識模組 - Detector Module
處理姿勢偵測邏輯
"""

import cv2
import numpy as np
import mediapipe as mp
import time
import math as m
from config_module import Config
from Play_prompt import AudioPlayer


def findDistance(x1, y1, x2, y2):
    """計算兩點之間的距離"""
    dist = m.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    return dist


def findAngle_hor(x1, y1, x2, y2):
    """計算水平角度"""
    if (m.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) * y1) == 0:
        return 0
    theta = m.acos((y2 - y1) * (-y1) / (m.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) * y1))
    degree = int(180 / m.pi) * theta
    return abs(degree - 90)


def findAngle_ver(x1, y1, x2, y2):
    """計算垂直角度"""
    if (m.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) * y1) == 0:
        return 0
    theta = m.acos((y2 - y1) * (-y1) / (m.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) * y1))
    degree = int(180 / m.pi) * theta
    return degree


class PostureDetector:
    """姿勢偵測器"""

    def __init__(self, side_neck_threshold=None, side_torso_threshold=None,
                 warning_time=None):
        # 初始化 MediaPipe
        self.mp_pose = mp.solutions.pose
        self.mp_face_detection = mp.solutions.face_detection

        # 初始化 Pose 偵測器
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=Config.MP_MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=Config.MP_MIN_TRACKING_CONFIDENCE,
            model_complexity=Config.MP_MODEL_COMPLEXITY
        )

        # 姿勢統計
        self.good_frames = 0
        self.bad_frames = 0
        self.total_frames = 0
        self.frame_counter = 0

        # 累計時間統計（秒）
        self.total_good_time = 0.0  # 累計正確坐姿時間
        self.total_bad_time = 0.0   # 累計不正確坐姿時間
        self.total_sitting_time = 0.0  # 累計總坐姿時間（偵測到人的總時間）

        # 基於時間戳的姿勢狀態計時
        self.bad_posture_start_time = None   # 開始不正確姿勢的時間戳
        self.good_posture_start_time = None  # 開始正確姿勢的時間戳
        self.last_posture_change_time = None  # 上次姿勢變更的時間戳

        # 可調整的閾值參數
        self.side_neck_threshold = side_neck_threshold or Config.DEFAULT_SIDE_NECK_THRESHOLD
        self.side_torso_threshold = side_torso_threshold or Config.DEFAULT_SIDE_TORSO_THRESHOLD

        # 儲存上一次的臉部資訊（用於跳幀）
        self.last_face_center = None  # (x, y)

        # FPS 計算
        self.start_time = time.time()
        self.fps = 0

        # 儲存上一次的偵測結果（用於跳幀）
        self.last_posture_info = None
        self.last_keypoints = None  # 儲存關鍵點座標字典

        # 初始化語音播報
        self.audio_player = AudioPlayer()

        # 警示時間閾值（可設定）
        self.warning_time = warning_time or Config.DEFAULT_WARNING_TIME

        # 用於控制語音播報頻率
        self.last_warning_time = 0
        self.warning_interval = 5.0  # 警告播報間隔（秒）

    def update_thresholds(self, side_neck, side_torso):
        """更新閾值參數"""
        self.side_neck_threshold = side_neck
        self.side_torso_threshold = side_torso

    def update_warning_time(self, warning_time):
        """更新警示時間閾值"""
        self.warning_time = warning_time

    def process_frame(self, frame, skip_frames=1):
        """處理單幀影像"""
        h, w, _ = frame.shape
        # OpenCV 攝影機影像幀是 BGR；MediaPipe 需要 RGB
        # 這裡統一：偵測用 RGB，所有繪製都在 BGR 上進行（Config 內顏色也以 BGR 定義）
        image_bgr = frame
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 計算 FPS
        now = time.time()
        fps_time = now - self.start_time
        self.start_time = now
        self.fps = 1 / fps_time if fps_time > 0 else 0

        posture_info = {
            'is_correct': None,
            'view_type': None,
            'angles': {},
            'good_time': 0,
            'bad_time': 0,
            # 當前幀是否偵測到人（供上層做久坐計時／重置使用）
            'person_detected': False,
        }

        # 跳幀邏輯
        self.frame_counter += 1
        should_detect = (self.frame_counter % skip_frames == 0)

        # 臉部偵測（每幀都執行）
        face_center = None  # 初始化臉部中心點
        with self.mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.8) as face_detection:
            face_results = face_detection.process(image_rgb)
            if face_results.detections:
                posture_info['person_detected'] = True
                for detection in face_results.detections:
                    box = detection.location_data.relative_bounding_box
                    cx = int(box.xmin * w)
                    cy = int(box.ymin * h)
                    cw = int(box.width * w)
                    ch = int(box.height * h)
                    cv2.rectangle(image_bgr, (cx, cy), (cx + cw, cy + ch), Config.COLOR_BLUE, 2)

                    # 計算臉部中心點
                    face_center_x = cx + cw // 2
                    face_center_y = cy + ch // 2
                    face_center = (face_center_x, face_center_y)

                    # 繪製臉部中心點
                    cv2.circle(image_bgr, face_center, 5, Config.COLOR_BLUE, -1)

        # 若未偵測到臉部，使用上一次的結果
        if face_center is None:
            face_center = self.last_face_center
        else:
            self.last_face_center = face_center

        # 姿勢偵測
        if should_detect:
            keypoints = self.pose.process(image_rgb)
            lm = keypoints.pose_landmarks
            lmPose = self.mp_pose.PoseLandmark

            if lm and hasattr(lm, 'landmark'):
                posture_info['person_detected'] = True
                self.total_frames += 1

                # 取出關鍵點座標
                keypoints_dict = self._extract_keypoints(lm, lmPose, w, h)

                # 計算肩膀距離判斷視角
                offset = findDistance(
                    keypoints_dict['l_shldr_x'], keypoints_dict['l_shldr_y'],
                    keypoints_dict['r_shldr_x'], keypoints_dict['r_shldr_y']
                )

                if offset > Config.FRONT_VIEW_THRESHOLD:  # 正面視角
                    # 正面視角僅判斷視角類型，不進行偵測
                    posture_info['view_type'] = 'front'
                    posture_info['is_correct'] = None  # 正面不參與偵測
                    posture_info['angles'] = {}
                    w = image_bgr.shape[1]
                    cv2.putText(image_bgr, f"{int(offset)} front (no detection)", (w - 200, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, Config.COLOR_BLUE, 2)
                else:  # 側面視角
                    posture_info['view_type'] = 'side'
                    self._process_side_view(image_bgr, keypoints_dict, offset, posture_info)

                # 使用 time.time() 計算目前連續姿勢時間（更準確，不依賴 FPS）
                current_time = time.time()

                if posture_info['is_correct']:
                    # 計算目前連續正確姿勢時間
                    if self.good_posture_start_time is not None:
                        posture_info['good_time'] = current_time - self.good_posture_start_time
                    else:
                        posture_info['good_time'] = 0
                    posture_info['bad_time'] = 0
                else:
                    # 計算目前連續不正確姿勢時間
                    if self.bad_posture_start_time is not None:
                        posture_info['bad_time'] = current_time - self.bad_posture_start_time
                    else:
                        posture_info['bad_time'] = 0
                    posture_info['good_time'] = 0

                # 首次偵測到側面視角時，初始化時間戳
                if posture_info['view_type'] == 'side':
                    # 若為首次偵測，初始化相對應時間戳
                    if posture_info['is_correct']:
                        if self.good_posture_start_time is None:
                            self.good_posture_start_time = current_time
                    else:
                        if self.bad_posture_start_time is None:
                            self.bad_posture_start_time = current_time

                # 當坐姿異常且持續時間超過閾值時，觸發語音播報
                if (posture_info['view_type'] == 'side' and
                    posture_info['is_correct'] == False and
                    posture_info['bad_time'] > self.warning_time):  # 異常持續超過閾值
                    if (current_time - self.last_warning_time) > self.warning_interval:
                        print(f"觸發語音播報: bad_time={posture_info['bad_time']:.2f}s, warning_time={self.warning_time}s")
                        self.audio_player.play_posture_warning(posture_info)
                        self.last_warning_time = current_time

                # 儲存本次偵測結果
                self.last_posture_info = posture_info.copy()
                self.last_keypoints = keypoints_dict
        else:
            # 跳幀時使用上一次的偵測結果，但更新時間戳（基於實際時間）
            if self.last_posture_info is not None and self.last_keypoints is not None:
                posture_info = self.last_posture_info.copy()
                # 使用 time.time() 更新時間（基於實際經過時間）
                current_time = time.time()

                if posture_info.get('is_correct'):
                    if self.good_posture_start_time is not None:
                        posture_info['good_time'] = current_time - self.good_posture_start_time
                    else:
                        posture_info['good_time'] = 0
                    posture_info['bad_time'] = 0
                elif posture_info.get('is_correct') == False:
                    if self.bad_posture_start_time is not None:
                        posture_info['bad_time'] = current_time - self.bad_posture_start_time
                    else:
                        posture_info['bad_time'] = 0
                    posture_info['good_time'] = 0

                # 繪製快取的偵測資訊（正面不繪製）
                if posture_info['view_type'] == 'side':
                    self._draw_side_cached(image_bgr, self.last_keypoints, posture_info, w, h)
                elif posture_info['view_type'] == 'front':
                    # 正面僅顯示視角標示
                    cv2.putText(image_bgr, f"front (no detection)", (w - 200, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, Config.COLOR_BLUE, 2)

        # 顯示 FPS
        cv2.putText(image_bgr, f'FPS: {int(self.fps)}', (w - 150, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, Config.COLOR_BLUE, 2)

        return image_bgr, posture_info

    def _extract_keypoints(self, lm, lmPose, w, h):
        """取出關鍵點座標"""
        return {
            'l_shldr_x': int(lm.landmark[lmPose.LEFT_SHOULDER].x * w),
            'l_shldr_y': int(lm.landmark[lmPose.LEFT_SHOULDER].y * h),
            'r_shldr_x': int(lm.landmark[lmPose.RIGHT_SHOULDER].x * w),
            'r_shldr_y': int(lm.landmark[lmPose.RIGHT_SHOULDER].y * h),
            'l_ear_x': int(lm.landmark[lmPose.LEFT_EAR].x * w),
            'l_ear_y': int(lm.landmark[lmPose.LEFT_EAR].y * h),
            'r_ear_x': int(lm.landmark[lmPose.RIGHT_EAR].x * w),
            'r_ear_y': int(lm.landmark[lmPose.RIGHT_EAR].y * h),
            'l_eye_x': int(lm.landmark[lmPose.LEFT_EYE].x * w),
            'l_eye_y': int(lm.landmark[lmPose.LEFT_EYE].y * h),
            'r_eye_x': int(lm.landmark[lmPose.RIGHT_EYE].x * w),
            'r_eye_y': int(lm.landmark[lmPose.RIGHT_EYE].y * h),
            'l_hip_x': int(lm.landmark[lmPose.LEFT_HIP].x * w),
            'l_hip_y': int(lm.landmark[lmPose.LEFT_HIP].y * h),
            'r_hip_x': int(lm.landmark[lmPose.RIGHT_HIP].x * w),
            'r_hip_y': int(lm.landmark[lmPose.RIGHT_HIP].y * h),
        }

    def _process_side_view(self, image, kp, offset, posture_info):
        """處理側面視角 - 只繪製必要的關鍵點與連線"""
        w = image.shape[1]

        cv2.putText(image, f"{int(offset)} side", (w - 150, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, Config.COLOR_DARK_BLUE, 2)

        # 計算角度
        neck_inclination = findAngle_ver(kp['l_shldr_x'], kp['l_shldr_y'], kp['l_ear_x'], kp['l_ear_y'])
        torso_inclination = findAngle_ver(kp['l_hip_x'], kp['l_hip_y'], kp['l_shldr_x'], kp['l_shldr_y'])

        posture_info['angles'] = {'neck': neck_inclination, 'torso': torso_inclination}

        # 判斷姿勢
        is_correct = (neck_inclination < self.side_neck_threshold and
                      torso_inclination < self.side_torso_threshold)

        current_time = time.time()

        if is_correct:
            # 若先前是不正確姿勢，現在轉為正確，累計不正確時間並重置
            if self.bad_posture_start_time is not None:
                elapsed_bad_time = current_time - self.bad_posture_start_time
                self.total_bad_time += elapsed_bad_time
                self.bad_posture_start_time = None

            # 記錄正確姿勢開始時間（若尚未記錄）
            if self.good_posture_start_time is None:
                self.good_posture_start_time = current_time

            self.bad_frames = 0
            self.good_frames += 1
            posture_info['is_correct'] = True
            color = Config.COLOR_LIGHT_GREEN
        else:
            # 若先前是正確姿勢，現在轉為不正確，累計正確時間並重置
            if self.good_posture_start_time is not None:
                elapsed_good_time = current_time - self.good_posture_start_time
                self.total_good_time += elapsed_good_time
                self.good_posture_start_time = None

            # 記錄不正確姿勢開始時間（若尚未記錄）
            if self.bad_posture_start_time is None:
                self.bad_posture_start_time = current_time

            self.good_frames = 0
            self.bad_frames += 1
            posture_info['is_correct'] = False
            color = Config.COLOR_RED

        # 繪製關鍵點與連線
        self._draw_side_keypoints(image, kp, color, neck_inclination, torso_inclination)

    def _draw_side_keypoints(self, image, kp, color, neck_angle, torso_angle):
        """繪製側面視角的關鍵點"""
        # 繪製關鍵點
        cv2.circle(image, (kp['l_shldr_x'], kp['l_shldr_y']), 7, Config.COLOR_YELLOW, -1)
        cv2.circle(image, (kp['l_ear_x'], kp['l_ear_y']), 7, Config.COLOR_YELLOW, -1)
        cv2.circle(image, (kp['l_hip_x'], kp['l_hip_y']), 7, Config.COLOR_YELLOW, -1)
        cv2.circle(image, (kp['l_shldr_x'], kp['l_shldr_y'] - 100), 7, Config.COLOR_YELLOW, -1)
        cv2.circle(image, (kp['l_hip_x'], kp['l_hip_y'] - 100), 7, Config.COLOR_YELLOW, -1)

        # 繪製連線
        cv2.line(image, (kp['l_shldr_x'], kp['l_shldr_y']), (kp['l_ear_x'], kp['l_ear_y']), color, 4)
        cv2.line(image, (kp['l_shldr_x'], kp['l_shldr_y']), (kp['l_shldr_x'], kp['l_shldr_y'] - 100), color, 4)
        cv2.line(image, (kp['l_hip_x'], kp['l_hip_y']), (kp['l_shldr_x'], kp['l_shldr_y']), color, 4)
        cv2.line(image, (kp['l_hip_x'], kp['l_hip_y']), (kp['l_hip_x'], kp['l_hip_y'] - 100), color, 4)

        # 顯示角度文字（關鍵！）
        angle_text = f'Neck: {int(neck_angle)}  Torso: {int(torso_angle)}'
        cv2.putText(image, angle_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

        # 在關鍵點旁顯示角度數值
        cv2.putText(image, str(int(neck_angle)), (kp['l_shldr_x'] + 10, kp['l_shldr_y']),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        cv2.putText(image, str(int(torso_angle)), (kp['l_hip_x'] + 10, kp['l_hip_y']),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

    def _draw_side_cached(self, image, kp, posture_info, w, h):
        """繪製快取的側面視角資訊"""
        color = Config.COLOR_LIGHT_GREEN if posture_info['is_correct'] else Config.COLOR_RED
        self._draw_side_keypoints(image, kp, color,
                                  posture_info['angles'].get('neck', 0),
                                  posture_info['angles'].get('torso', 0))
        cv2.putText(image, "(cached)", (w - 150, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, Config.COLOR_DARK_BLUE, 2)

    def get_statistics(self):
        """
        取得統計資訊（累計時間）

        Returns:
            tuple: (累計正確坐姿時間(秒), 累計不正確坐姿時間(秒), 累計總坐姿時間(秒))
        """
        # 計算目前未結束的時間區段並加總至統計中
        current_time = time.time()

        # 若目前是不正確姿勢，將目前時間段加到 total_bad_time
        current_total_bad_time = self.total_bad_time
        if self.bad_posture_start_time is not None:
            current_total_bad_time += (current_time - self.bad_posture_start_time)

        # 若目前是正確姿勢，將目前時間段加到 total_good_time
        current_total_good_time = self.total_good_time
        if self.good_posture_start_time is not None:
            current_total_good_time += (current_time - self.good_posture_start_time)

        # 總坐姿時間 = 正確時間 + 不正確時間
        current_total_sitting_time = current_total_good_time + current_total_bad_time

        return current_total_good_time, current_total_bad_time, current_total_sitting_time

    def reset_statistics(self):
        """重置統計資訊"""
        self.good_frames = 0
        self.bad_frames = 0
        self.total_frames = 0
        self.frame_counter = 0
        # 重置累計時間統計
        self.total_good_time = 0.0
        self.total_bad_time = 0.0
        self.total_sitting_time = 0.0
        # 重置時間戳
        self.bad_posture_start_time = None
        self.good_posture_start_time = None
        self.last_posture_change_time = None

    def release(self):
        """釋放資源"""
        self.pose.close()
        if hasattr(self, 'audio_player'):
            self.audio_player.release()
