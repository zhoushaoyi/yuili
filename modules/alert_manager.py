"""
告警管理器：统一处理告警片段的保存、管理、查询
"""
import os
import cv2
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque


class AlertManager:
    """告警管理器 - 处理告警片段的保存和管理"""
    
    def __init__(self, output_dir: str = 'output', pre_seconds: int = 5, post_seconds: int = 5):
        """
        初始化告警管理器
        
        Args:
            output_dir: 输出目录
            pre_seconds: 告警前预录制时长（秒）
            post_seconds: 告警后录制时长（秒）
        """
        self.output_dir = output_dir
        self.pre_seconds = pre_seconds
        self.post_seconds = post_seconds
        self.save_tasks = []
        self.alert_history = []
        self._ensure_output_dir()
    
    def _ensure_output_dir(self):
        """确保输出目录存在"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def start_recording(self, frame: object, fps: float, alerts: List[str]) -> Optional[Dict]:
        """
        启动告警片段录制
        
        Args:
            frame: 当前帧（numpy array）
            fps: 帧率
            alerts: 告警信息列表
        
        Returns:
            录制任务字典，包含 writer 和 metadata
        """
        if not alerts:
            return None
        
        try:
            # 创建按天目录
            date_dir = datetime.now().strftime('%Y%m%d')
            save_dir = os.path.join(self.output_dir, date_dir)
            os.makedirs(save_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            clip_name = f"alert_{timestamp}.mp4"
            clip_path = os.path.join(save_dir, clip_name)
            
            # 创建 VideoWriter
            h, w = frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(clip_path, fourcc, fps, (w, h))
            
            # 记录告警
            self.alert_history.append({
                'timestamp': timestamp,
                'alerts': alerts,
                'path': clip_path,
                'start_time': datetime.now()
            })
            
            # 创建任务
            task = {
                'writer': writer,
                'remaining': int(self.post_seconds * fps),
                'path': clip_path,
                'alerts': alerts,
                'start_frame': frame.copy()
            }
            
            self.save_tasks.append(task)
            return task
        
        except Exception as e:
            print(f"创建告警录制任务失败: {e}")
            return None
    
    def write_frame(self, frame: object) -> None:
        """
        写入当前帧到所有活跃任务
        
        Args:
            frame: 当前帧（numpy array）
        """
        for task in list(self.save_tasks):
            try:
                task['writer'].write(frame)
                task['remaining'] -= 1
                
                # 检查是否完成
                if task['remaining'] <= 0:
                    self._finalize_task(task)
            
            except Exception as e:
                print(f"保存告警片段失败: {e}")
                self._finalize_task(task)
    
    def _finalize_task(self, task: Dict) -> None:
        """完成一个录制任务"""
        try:
            task['writer'].release()
            self.save_tasks.remove(task)
            print(f"✓ 告警片段已保存: {task['path']}")
        except Exception as e:
            print(f"关闭录制器失败: {e}")
    
    def write_pre_buffer(self, frame_buffer: deque, task: Optional[Dict]) -> None:
        """
        写入预缓冲的帧到任务
        
        Args:
            frame_buffer: 预缓冲（deque）
            task: 录制任务
        """
        if not task or not frame_buffer:
            return
        
        try:
            for buffered_frame in frame_buffer:
                task['writer'].write(buffered_frame)
        except Exception as e:
            print(f"写入预缓冲失败: {e}")
    
    def cleanup(self) -> None:
        """清理所有未完成的任务"""
        for task in list(self.save_tasks):
            self._finalize_task(task)
    
    def get_active_tasks(self) -> int:
        """获取活跃任务数"""
        return len(self.save_tasks)
    
    def list_alerts(self) -> List[Dict]:
        """列出所有告警记录"""
        return list(self.alert_history)
    
    def list_alert_files(self) -> List[Dict]:
        """列出所有告警视频文件"""
        files = []
        try:
            for day in sorted(os.listdir(self.output_dir)):
                day_dir = os.path.join(self.output_dir, day)
                if os.path.isdir(day_dir):
                    for f in sorted(os.listdir(day_dir)):
                        if f.lower().endswith('.mp4'):
                            file_path = os.path.join(day_dir, f)
                            file_size = os.path.getsize(file_path)
                            files.append({
                                'day': day,
                                'name': f,
                                'path': file_path,
                                'size': file_size,
                                'url': f'/download_alert?path={file_path}'
                            })
        except Exception as e:
            print(f"列出告警文件失败: {e}")
        
        return files
