import cv2


class CameraManager:
    """摄像头管理模块"""
    
    def __init__(self):
        self.cap = None
    
    def init_camera(self, camera_id=0):
        """初始化摄像头"""
        self.cap = cv2.VideoCapture(camera_id)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # 720p宽
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)  # 720p高
        self.cap.set(cv2.CAP_PROP_FPS, 30)  # 设置帧率为60
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # 设置自动曝光模式
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
