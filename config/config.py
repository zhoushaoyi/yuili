"""
配置管理模块：统一管理应用配置和默认值
"""
from typing import Dict, Any


class Config:
    """应用配置管理"""
    
    # 默认检测参数
    DEFAULT_DETECTION_PARAMS = {
        'source': '0',  # 默认摄像头 0
        'model': 'data/best.pt',
        'conf': 0.25,
        'iou': 0.45,
        'imgsz': 640,
        'device': 0,
        'classes': '',
        'fps': 30,
        'output_dir': 'output',
        'save_results': False,
    }
    
    # 默认三色灯参数
    DEFAULT_LIGHT_PARAMS = {
        'port': 'COM3',
        'enabled': True,
        'baud_rate': 9600,
        'timeout': 1.0,
    }
    
    # 告警参数
    DEFAULT_ALERT_PARAMS = {
        'pre_seconds': 5,
        'post_seconds': 5,
        'min_duration': 0.5,  # 最小告警时长（秒）
    }
    
    # 视频处理参数
    DEFAULT_VIDEO_PARAMS = {
        'max_age': 20,  # SORT 追踪器参数
        'min_hits': 20,
        'iou_threshold': 0.5,
    }
    
    # FPS 管理参数
    DEFAULT_FPS_PARAMS = {
        'window_size': 30,  # 平滑 FPS 的窗口大小
        'target_fps': 30,  # 目标 FPS
    }
    
    # Web 服务参数
    DEFAULT_WEB_PARAMS = {
        'host': '0.0.0.0',
        'port': 5000,
        'debug': False,
        'log_level': 'INFO',
    }
    
    @classmethod
    def get_detection_config(cls, user_args: Dict[str, Any] = None) -> Dict[str, Any]:
        """获取检测配置（合并用户参数）"""
        config = cls.DEFAULT_DETECTION_PARAMS.copy()
        if user_args:
            config.update(user_args)
        return config
    
    @classmethod
    def get_light_config(cls, user_args: Dict[str, Any] = None) -> Dict[str, Any]:
        """获取灯控配置"""
        config = cls.DEFAULT_LIGHT_PARAMS.copy()
        if user_args:
            config.update(user_args)
        return config
    
    @classmethod
    def get_alert_config(cls, user_args: Dict[str, Any] = None) -> Dict[str, Any]:
        """获取告警配置"""
        config = cls.DEFAULT_ALERT_PARAMS.copy()
        if user_args:
            config.update(user_args)
        return config
    
    @classmethod
    def validate_source(cls, source: str) -> bool:
        """验证视频源是否有效"""
        # 简单验证：是否为数字（摄像头ID）或有效文件
        import os
        if isinstance(source, str):
            if source.isdigit():
                return True
            if os.path.isfile(source):
                return True
        return False
