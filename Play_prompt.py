# -*- coding: utf-8 -*-
# Time : 2025/12/7 17:32
# User : l'r's
# Software: PyCharm
# File : Play_prompt.py
"""
語音播報模組 - Audio Player Module
處理坐姿異常的音訊提醒
"""

import pygame
import pyttsx3
import time
import threading
import os


class AudioPlayer:
    """音訊播放器類別"""
    
    def __init__(self):
        # 初始化 pygame 的混音器模組
        pygame.mixer.init()
        self.audio_file = "output.wav"
        self.is_playing = False  # 用於判斷是否正在播放音訊
        
        # 音訊檔案對應（預留功能：可依不同異常類型選擇不同音訊）
        self.audio_files = {
            'default': 'output.wav',
            'head_down': 'output.wav',   # 可替換為專用音訊檔
            'head_up': 'output.wav',
            'hunchback': 'output.wav',
            'tilt': 'output.wav',
            'neck_forward': 'output.wav',
            'torso_tilt': 'output.wav',
            # 久坐提醒
            'sitting': 'output2.wav',
        }
        
        # 確保預設音訊檔存在（若不存在，將於首次使用時產生）
        self._ensure_audio_file_exists()
    
    def _ensure_audio_file_exists(self):
        """確保預設音訊檔存在，若不存在則產生"""
        if not os.path.exists(self.audio_file):
            # 產生預設提示音訊
            self.text_to_audio("請注意，您的坐姿不正確，請調整姿勢")
    
    def text_to_audio(self, text):
        """
        將文字轉為音訊並儲存
        
        Args:
            text: 要轉換的文字
        """
        try:
            # 初始化語音引擎
            engine = pyttsx3.init()
            
            # 設定語音屬性（可選）
            engine.setProperty('rate', 150)   # 語速
            engine.setProperty('volume', 1)   # 音量
            
            # 嘗試設定中文語音（若系統支援）
            voices = engine.getProperty('voices')
            for voice in voices:
                if 'chinese' in voice.name.lower() or 'zh' in voice.id.lower():
                    engine.setProperty('voice', voice.id)
                    break
            
            # 將文字轉為音訊並儲存
            engine.save_to_file(text, self.audio_file)
            engine.runAndWait()
        except Exception as e:
            print(f"文字轉音訊失敗: {e}")
    
    def play_audio(self, audio_type='default'):
        """
        播放音訊
        
        Args:
            audio_type: 音訊類型，用於選擇不同音訊檔（預留功能）
        """
        if self.is_playing:
            print("音訊已在播放中，略過此次播放請求")
            return
        
        # 依類型選擇音訊檔（預留功能）
        audio_file = self.audio_files.get(audio_type, self.audio_file)
        
        # 檢查音訊檔是否存在
        if not os.path.exists(audio_file):
            print(f"音訊檔不存在: {audio_file}，改用預設檔案")
            audio_file = self.audio_file
            if not os.path.exists(audio_file):
                print(f"預設音訊檔也不存在: {audio_file}")
                return
        
        # 於新執行緒中播放，避免阻塞主執行緒
        thread = threading.Thread(target=self._play_audio_thread, args=(audio_file,))
        thread.daemon = True
        thread.start()
    
    def _play_audio_thread(self, audio_file):
        """於背景執行緒中播放音訊"""
        try:
            self.is_playing = True
            
            # 載入音訊檔
            pygame.mixer.music.load(audio_file)
            
            # 播放音訊
            pygame.mixer.music.play()
            
            # 等待音訊播放結束
            while pygame.mixer.music.get_busy():  # 音訊播放中
                time.sleep(0.1)
            
            print("播放完成")
        except Exception as e:
            print(f"播放音訊錯誤: {e}")
        finally:
            self.is_playing = False
    
    def stop_audio(self):
        """停止播放音訊"""
        try:
            pygame.mixer.music.stop()
            self.is_playing = False
        except Exception as e:
            print(f"停止音訊錯誤: {e}")
    
    def play_posture_warning(self, posture_info):
        """
        依坐姿資訊播放對應的警示音訊
        
        Args:
            posture_info: 姿勢資訊字典
        """
        view_type = posture_info.get('view_type')
        angles = posture_info.get('angles', {})
        is_correct = posture_info.get('is_correct', True)
        
        # 若坐姿正確，不播放
        if is_correct:
            return
        
        # 依不同異常狀況選擇音訊類型（僅側面視角進行偵測）
        audio_type = 'default'
        
        if view_type == 'side':
            # 側面視角的異常判斷
            neck_angle = angles.get('neck', 0)
            torso_angle = angles.get('torso', 0)
            
            if neck_angle > 50:
                audio_type = 'neck_forward'
            elif torso_angle > 20:
                audio_type = 'torso_tilt'
        
        # 播放音訊
        self.play_audio(audio_type)
    
    def release(self):
        """釋放資源"""
        try:
            self.stop_audio()
            pygame.mixer.quit()
        except Exception as e:
            print(f"釋放音訊資源錯誤: {e}")
