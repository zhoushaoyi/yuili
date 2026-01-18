import os
from .video_processor import VideoProcessor


class PathHandler:
    """路径处理模块，负责路径分析和路由到相应的处理流程"""
    
    def __init__(self, model_path, output_dir="run", default_save_results=False, default_visualize=False):
        self.processor = VideoProcessor(model_path, output_dir)
        self.default_save_results = default_save_results
        self.default_visualize = default_visualize
    
    def _is_camera_id(self, path):
        """判断是否为摄像头ID（纯数字字符串）"""
        if isinstance(path, str):
            return path.isdigit()
        elif isinstance(path, int):
            return True
        return False
    
    def _is_video_file(self, path):
        """判断是否为视频文件"""
        if not isinstance(path, str) or not os.path.isfile(path):
            return False
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv']
        ext = os.path.splitext(path)[1].lower()
        return ext in video_extensions
    
    def _analyze_path(self, path):
        """分析路径类型，返回路径类型字符串"""
        if self._is_camera_id(path):
            return 'camera'
        elif self._is_video_file(path):
            return 'video'
        else:
            return 'invalid'
    
    def process_path(self, video_path, save_results=None, visualize=None):
        """根据路径类型执行相应的处理"""
        try:
            if save_results is None:
                save_results = self.default_save_results
            if visualize is None:
                visualize = self.default_visualize
            path_type = self._analyze_path(video_path)
            
            if path_type == 'camera':
                # 数字：使用摄像头
                camera_id = int(video_path) if isinstance(video_path, str) else video_path
                print(f"启动摄像头 {camera_id} 检测...")
                print("按 'q' 键退出，按 's' 键保存当前帧")
                self.processor.process_camera(camera_id, save_results=save_results, visualize=visualize)
                
            elif path_type == 'video':
                # 视频文件：处理单个视频文件
                print(f"开始处理视频文件: {video_path}")
                print("按 'q' 键退出，按空格键暂停，按 's' 键保存当前帧")
                self.processor.process_video_file(video_path, save_results=save_results, visualize=visualize)
                
            else:
                print(f"无效路径: {video_path}")
                self._print_usage_instructions()
                
        except Exception as e:
            print(f"处理路径时出错: {e}")
            raise
    
    def _print_usage_instructions(self):
        """打印使用说明"""
        print("请设置正确的video_path变量:")
        print("- 数字 (如 '0', '1'): 使用对应摄像头")
        print("- 视频文件路径: 处理单个视频文件")

