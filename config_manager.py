# -*- coding: utf-8 -*-
# Time : 2025/12/7 17:32
# User : l'r's
# Software: PyCharm
# File : config_manager.py
"""
設定管理模組 - Configuration Manager Module
處理設定參數的儲存與載入
"""

import os
from config_module import Config


class ConfigManager:
    """設定管理器類別"""

    CONFIG_FILE = "config.txt"  # 設定檔路徑

    @staticmethod
    def save_config(config_dict):
        """
        將設定儲存至檔案

        Args:
            config_dict: 設定字典，包含所有需要儲存的參數
        """
        try:
            with open(ConfigManager.CONFIG_FILE, 'w', encoding='utf-8') as f:
                for key, value in config_dict.items():
                    # 處理不同型別的值
                    if isinstance(value, tuple):
                        # 元組轉成字串，例如 (640, 480) -> "640x480"
                        f.write(f"{key}={value[0]}x{value[1]}\n")
                    elif isinstance(value, float):
                        f.write(f"{key}={value}\n")
                    elif isinstance(value, int):
                        f.write(f"{key}={value}\n")
                    else:
                        f.write(f"{key}={value}\n")
            print(f"設定已儲存至 {ConfigManager.CONFIG_FILE}")
            return True
        except Exception as e:
            print(f"儲存設定失敗: {e}")
            return False

    @staticmethod
    def load_config():
        """
        從檔案載入設定

        Returns:
            dict: 設定字典；若檔案不存在或讀取失敗則回傳 None
        """
        if not os.path.exists(ConfigManager.CONFIG_FILE):
            print(f"設定檔 {ConfigManager.CONFIG_FILE} 不存在，使用預設設定")
            return None

        try:
            config_dict = {}
            with open(ConfigManager.CONFIG_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):  # 略過空行與註解
                        continue

                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()

                        # 嘗試轉成數字
                        try:
                            if '.' in value:
                                config_dict[key] = float(value)
                            else:
                                config_dict[key] = int(value)
                        except ValueError:
                            # 若非數字，檢查是否為解析度格式
                            if 'x' in value and value.replace('x', '').isdigit():
                                w, h = map(int, value.split('x'))
                                config_dict[key] = (w, h)
                            else:
                                config_dict[key] = value

            print(f"設定已從 {ConfigManager.CONFIG_FILE} 載入")
            return config_dict
        except Exception as e:
            print(f"載入設定失敗: {e}")
            return None

    @staticmethod
    def get_default_config():
        """
        取得預設設定字典

        Returns:
            dict: 預設設定字典
        """
        return {
            'side_neck_threshold': Config.DEFAULT_SIDE_NECK_THRESHOLD,
            'side_torso_threshold': Config.DEFAULT_SIDE_TORSO_THRESHOLD,
            'warning_time': Config.DEFAULT_WARNING_TIME,
            'sitting_minutes': Config.DEFAULT_SITTING_MINUTES,
            'resolution': Config.DEFAULT_RESOLUTION,
            'skip_frames': Config.DEFAULT_SKIP_FRAMES,
        }
