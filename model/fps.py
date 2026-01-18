import cv2
from cv2 import getTickCount, getTickFrequency


class FPSManager:
    """FPS管理模块"""
    
    def __init__(self):
        self.loop_start = None
    
    def start_timer(self):
        """开始计时"""
        self.loop_start = getTickCount()
    
    def show_fps(self, frame):
        """显示FPS信息"""
        if self.loop_start is None:
            return frame
            
        loop_time = getTickCount() - self.loop_start
        total_time = loop_time / getTickFrequency()
        FPS = int(1 / total_time)

        fps_text = f"FPS: {FPS:.2f}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1
        font_thickness = 2
        text_color = (0, 0, 255)  # 红色
        text_position = (10, 30)  # 左上角位置

        cv2.putText(frame, fps_text, text_position, font, font_scale, text_color, font_thickness)
        return frame
    
    def print_fps(self):
        """获取FPS"""
        if self.loop_start is None:
            return 0
        loop_time = getTickCount() - self.loop_start
        total_time = loop_time / getTickFrequency()
        FPS = int(1 / total_time)
        print(f"FPS: {FPS:.2f}")
        return 
