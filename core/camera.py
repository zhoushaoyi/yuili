import cv2
import os
import platform


class CameraManager:
    """摄像头管理模块（修复版）"""
    
    def __init__(self):
        self.cap = None
    
    def init_camera(self, camera_id=0):
        """初始化摄像头"""
        # 1. 针对 Windows 的 DSHOW 优化 - 解决USB摄像头启动慢问题
        if os.name == 'nt' or platform.system() == 'Windows':
            self.cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
        else:
            self.cap = cv2.VideoCapture(camera_id)
        
        # 添加异常处理检查
        if not self.cap or not self.cap.isOpened():
            raise RuntimeError(f"无法打开摄像头 {camera_id}，请检查设备是否连接或被占用")
        
        # 2. 强制设置 MJPG 格式 (解决 USB 带宽瓶颈)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        
        # 3. 设置分辨率和帧率
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # 720p宽
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)  # 720p高
        self.cap.set(cv2.CAP_PROP_FPS, 30)  # 设置帧率为30
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # 设置自动曝光模式
        
        # 调试输出
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        print(f"✓ 摄像头已启动 | ID: {camera_id} | FPS: {actual_fps}")
        return self.cap
    
    def init_video(self, video_path):
        """初始化视频文件"""
        self.cap = cv2.VideoCapture(video_path)
        return self.cap
    
    def read_frame(self):
        """读取帧"""
        if self.cap is None:
            return False, None
        return self.cap.read()
    
    def is_opened(self):
        """检查是否打开"""
        if self.cap is None:
            return False
        return self.cap.isOpened()
    
    def release(self):
        """释放资源"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
