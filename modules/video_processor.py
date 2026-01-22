import os

from core.camera import CameraManager
from core.detection import DetectionManager
from core.fps import FPSManager
from core.tracker import TrackerManager
from utils.visualizer import Visualizer
from utils.config_loader import load_spec
from .inventory import InventoryManager
from .frame_processor import FrameProcessor
from .light_controller import LightController


class VideoProcessor:
    """
    核心资源容器：负责初始化所有模块，但不包含循环逻辑。
    """
    
    def __init__(self, model_path, output_dir="output", light_port='COM3', light_enabled=True, config=None):
        # 防止 config 为 None
        self.config = config if config else {}
        
        # --- 1. 解析参数 ---
        # 置信度 (默认 0.5)
        conf_threshold = float(self.config.get('conf_threshold', 0.5))
        
        # SORT 追踪参数
        max_age = int(self.config.get('sort_max_age', 30))
        min_hits = int(self.config.get('sort_min_hits', 5))
        iou_threshold = float(self.config.get('sort_iou_threshold', 0.5))
        
        # 报警时长
        alert_frames = int(self.config.get('alert_display_time', 90))
        
        # --- 2. 初始化模块 (传入参数) ---
        self.camera_manager = CameraManager()
        
        # [修复] 传入置信度
        self.detection_manager = DetectionManager(model_path, conf_threshold=conf_threshold)
        self.fps_manager = FPSManager()
        
        # [修复] 传入 SORT 参数
        self.tracker_manager = TrackerManager(
            max_age=max_age, 
            min_hits=min_hits, 
            iou_threshold=iou_threshold
        )
        self.visualizer = Visualizer()
        
        # [关键修复] 加载业务配置
        # - 使用 force_reload=True 确保每次启动都重新读取最新的 Configuration.json
        # - 这样修改配置后无需重启程序即可生效
        try:
            self.spec = load_spec('Configuration.json', force_reload=True)
            print(f"[配置加载] 成功加载 Configuration.json，物品清单: {list(self.spec['class0']['contains'].keys())}")
        except Exception as e:
            print(f"❌ 严重警告: 配置文件加载失败: {e}")
            import traceback
            traceback.print_exc()
            # 给一个默认空配置，防止程序直接崩溃
            self.spec = {'class0': {'name': 'storage box', 'contains': {}}}
        
        # [修复] 传入报警时长
        self.inventory = InventoryManager(self.spec, alert_display_time=alert_frames)
        
        # 3. 硬件控制 (灯光)
        # 如果不需要灯光，light_enabled 设为 False 即可
        try:
            self.light_controller = LightController(port=light_port, enabled=light_enabled)
        except Exception as e:
            print(f"⚠ 灯光控制初始化失败: {e}，但不影响检测运行")
            self.light_controller = None
        
        # 4. 帧处理器 (业务聚合)
        self.frame_processor = FrameProcessor(
            self.detection_manager,
            self.tracker_manager,
            self.visualizer,
            self.fps_manager,
            self.inventory,
            self.light_controller
        )
        
        # 5. 输出目录
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
        print(f"✓ VideoProcessor 初始化完成，输出目录: {self.output_dir}")

    def release(self):
        """释放所有资源"""
        if self.camera_manager:
            self.camera_manager.release()
        if self.light_controller:
            try:
                self.light_controller.close()
            except Exception:
                pass
        print("✓ 资源已释放")
