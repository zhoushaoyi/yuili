import cv2
from cv2 import getTickCount, getTickFrequency


class FPSManager:
    """FPS管理模块 - 使用平滑的移动平均算法"""
    
    def __init__(self, window_size=30):
        self.loop_start = None
        self.fps_history = []  # 存储最近N帧的FPS
        self.window_size = window_size  # 移动平均窗口大小
    
    def start_timer(self):
        """开始计时"""
        self.loop_start = getTickCount()
    
    def end_timer(self):
        """结束计时并计算FPS"""
        if self.loop_start is None:
            return 0
        loop_time = getTickCount() - self.loop_start
        total_time = loop_time / getTickFrequency()
        if total_time > 0:
            fps = 1.0 / total_time
            self.fps_history.append(fps)
            # 保持窗口大小
            if len(self.fps_history) > self.window_size:
                self.fps_history.pop(0)
            return fps
        return 0
    
    def get_smooth_fps(self):
        """获取平滑后的FPS（使用移动平均）"""
        if not self.fps_history:
            return 0
        return sum(self.fps_history) / len(self.fps_history)
    
    def show_fps(self, frame):
        """显示FPS信息"""
        smooth_fps = self.get_smooth_fps()
        fps_text = f"FPS: {smooth_fps:.1f}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1
        font_thickness = 2
        text_color = (0, 255, 0)  # 绿色
        text_position = (10, 30)  # 左上角位置

        cv2.putText(frame, fps_text, text_position, font, font_scale, text_color, font_thickness)
        return frame
    
    def print_fps(self):
        """获取FPS"""
        smooth_fps = self.get_smooth_fps()
        print(f"FPS: {smooth_fps:.1f}")
        return smooth_fps
