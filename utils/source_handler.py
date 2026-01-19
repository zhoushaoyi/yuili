"""
视频源处理模块：统一处理摄像头和文件视频源
"""
import os
import cv2
from typing import Union, Tuple


class SourceHandler:
    """视频源处理器 - 统一处理摄像头ID、视频文件、URL等"""
    
    SUPPORTED_VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
    
    @staticmethod
    def is_camera_id(source: Union[str, int]) -> bool:
        """判断是否为摄像头ID"""
        if isinstance(source, int):
            return source >= 0
        if isinstance(source, str):
            return source.isdigit()
        return False
    
    @staticmethod
    def is_video_file(source: Union[str, int]) -> bool:
        """判断是否为视频文件"""
        if not isinstance(source, str):
            return False
        if not os.path.isfile(source):
            return False
        ext = os.path.splitext(source)[1].lower()
        return ext in SourceHandler.SUPPORTED_VIDEO_EXTENSIONS
    
    @staticmethod
    def is_valid_source(source: Union[str, int]) -> bool:
        """判断是否为有效的视频源"""
        return SourceHandler.is_camera_id(source) or SourceHandler.is_video_file(source)
    
    @staticmethod
    def get_source_type(source: Union[str, int]) -> str:
        """获取源类型"""
        if SourceHandler.is_camera_id(source):
            return 'camera'
        elif SourceHandler.is_video_file(source):
            return 'file'
        else:
            return 'invalid'
    
    @staticmethod
    def parse_camera_id(source: Union[str, int]) -> int:
        """从源转换为摄像头ID"""
        if isinstance(source, int):
            return source
        if isinstance(source, str) and source.isdigit():
            return int(source)
        raise ValueError(f"无效的摄像头ID: {source}")
    
    @staticmethod
    def validate_source(source: Union[str, int]) -> Tuple[bool, str]:
        """验证源的有效性，返回 (is_valid, message)"""
        source_type = SourceHandler.get_source_type(source)
        
        if source_type == 'camera':
            cam_id = SourceHandler.parse_camera_id(source)
            try:
                cap = cv2.VideoCapture(cam_id)
                if not cap.isOpened():
                    return False, f"无法打开摄像头 {cam_id}，请检查设备是否连接或被占用"
                # 尝试读一帧
                ret, frame = cap.read()
                cap.release()
                if not ret:
                    return False, f"摄像头 {cam_id} 无法读取帧"
                return True, f"✓ 摄像头 {cam_id} 可用"
            except Exception as e:
                return False, f"摄像头验证异常: {e}"
        
        elif source_type == 'file':
            if not os.path.exists(source):
                return False, f"视频文件不存在: {source}"
            try:
                cap = cv2.VideoCapture(source)
                if not cap.isOpened():
                    return False, f"无法打开视频文件: {source}"
                cap.release()
                return True, f"✓ 视频文件可用: {source}"
            except Exception as e:
                return False, f"视频文件验证异常: {e}"
        
        else:
            return False, f"无效的视频源: {source}"
    
    @staticmethod
    def get_source_info(source: Union[str, int]) -> dict:
        """获取视频源的详细信息"""
        source_type = SourceHandler.get_source_type(source)
        info = {
            'source': source,
            'type': source_type,
            'valid': False,
            'fps': 0,
            'width': 0,
            'height': 0,
            'frame_count': 0
        }
        
        try:
            if source_type == 'camera':
                cam_id = SourceHandler.parse_camera_id(source)
                cap = cv2.VideoCapture(cam_id)
            elif source_type == 'file':
                cap = cv2.VideoCapture(source)
            else:
                return info
            
            if cap.isOpened():
                info['valid'] = True
                info['fps'] = cap.get(cv2.CAP_PROP_FPS) or 0
                info['width'] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                info['height'] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                info['frame_count'] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                cap.release()
        except Exception:
            pass
        
        return info
