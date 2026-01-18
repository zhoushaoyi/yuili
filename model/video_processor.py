import cv2
import os
from datetime import datetime

import numpy as np

from .camera import CameraManager
from .detection import DetectionManager
from .fps import FPSManager
from .tracker import TrackerManager
from .visualizer import Visualizer
from .config_loader import load_spec
from .inventory import InventoryManager
from .frame_processor import FrameProcessor
from .light_controller import LightController


class VideoProcessor:
    """视频处理模块，负责视频流的读取和写入"""
    
    def __init__(self, model_path, output_dir="run", light_port='COM3', light_enabled=True):
        self.camera_manager = CameraManager()
        self.detection_manager = DetectionManager(model_path)
        self.fps_manager = FPSManager()
        self.tracker_manager = TrackerManager(max_age=20, min_hits=20, iou_threshold=0.5)
        self.visualizer = Visualizer()
        # 配置与装配状态
        try:
            self.spec = load_spec('Configuration.josn')
        except Exception:
            # 回退：空规范
            self.spec = {'class0': {'name': 'storage box', 'contains': {}}}
        self.inventory = InventoryManager(self.spec)
        # 初始化三色灯控制器
        self.light_controller = LightController(port=light_port, enabled=light_enabled)
        # 创建帧处理器
        self.frame_processor = FrameProcessor(
            self.detection_manager,
            self.tracker_manager,
            self.visualizer,
            self.fps_manager,
            self.inventory,
            self.light_controller
        )
        self.output_dir = output_dir
        self._ensure_output_dir()
    
    def _ensure_output_dir(self):
        """确保输出目录存在"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def _get_output_path(self, input_path, suffix=""):
        """生成输出文件路径"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if os.path.isfile(input_path):
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            return os.path.join(self.output_dir, f"{base_name}_{timestamp}{suffix}.jpg")
        else:
            return os.path.join(self.output_dir, f"camera_{timestamp}{suffix}.jpg")
    
    def _get_video_output_path(self, input_path):
        """生成视频输出文件路径（.mp4）。"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if isinstance(input_path, str) and os.path.isfile(input_path):
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            return os.path.join(self.output_dir, f"{base_name}_{timestamp}.mp4")
        return os.path.join(self.output_dir, f"camera_{timestamp}.mp4")
    
    def process_camera(self, camera_id=0, save_results=False, visualize=False):
        """处理摄像头视频流"""
        self.camera_manager.init_camera(camera_id)
        self._process_video_stream(
            source_name=f"camera_{camera_id}",
            window_name='Camera Detection with Tracking',
            save_results=save_results,
            wait_key_delay=1,
            allow_pause=False,
            visualize=visualize
        )
        self.camera_manager.release()
        if self.light_controller:
            self.light_controller.close()
        cv2.destroyAllWindows()
    
    def process_video_file(self, video_path, save_results=False, visualize=False):
        """处理本地视频文件"""
        self.camera_manager.init_video(video_path)
        
        if not self.camera_manager.is_opened():
            print(f"无法打开视频文件: {video_path}")
            return
        
        self._process_video_stream(
            source_name=video_path,
            window_name='Video Detection with Tracking',
            save_results=save_results,
            wait_key_delay=1,
            allow_pause=True,
            visualize=visualize
        )
        self.camera_manager.release()
        self.light_controller.close()
        # cv2.destroyAllWindows()


    def _process_video_stream(self, source_name, window_name, save_results=False, 
                             wait_key_delay=1, allow_pause=False, visualize=False):
        """统一的视频流处理流程"""
        frame_count = 0
        writer = None
        cap = self.camera_manager.cap
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.imshow(window_name, np.zeros((1, 1), dtype=np.uint8))
        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        while self.camera_manager.is_opened():
            self.fps_manager.start_timer()
            success, frame = self.camera_manager.read_frame()
            
            if not success:
                break

            annotated_frame, tracked_boxes = self.frame_processor.process_frame(frame, visualize=visualize)
            if visualize:

                cv2.imshow(window_name, annotated_frame)
            
            # 写入视频
            if save_results:
                if writer is None:
                    h, w = annotated_frame.shape[:2]
                    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    out_path = self._get_video_output_path(source_name)
                    writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))
                    print(f"视频输出: {out_path}")
                writer.write(annotated_frame)
            
            # 处理键盘输入
            if visualize:
                key = cv2.waitKey(wait_key_delay) & 0xFF
                if key == ord('q'):
                    break
                elif allow_pause and key == ord(' '):
                    cv2.waitKey(0)  # 暂停直到按任意键
                elif key == ord('s'):
                    output_path = self._get_output_path(source_name, f"_manual_{frame_count}")
                    cv2.imwrite(output_path, annotated_frame)
                    print(f"手动保存: {output_path}")
            
            frame_count += 1
        
        if writer is not None:
            writer.release()
