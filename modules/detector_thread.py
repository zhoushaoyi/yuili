import threading
import time
import os
from collections import deque
from datetime import datetime
import cv2

from .video_processor import VideoProcessor
from .alert_manager import AlertManager


class DetectorThread(threading.Thread):
    """后台检测线程：负责视频循环、帧获取、结果分发"""
    
    def __init__(self, args: dict):
        super().__init__(daemon=True)
        self.args = args
        self.running = False
        self._stop_event = threading.Event()
        
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.logs = deque(maxlen=200)
        self.alerts = []
        
        model_path = self.args.get('model', 'data/best.pt')
        output_dir = self.args.get('output_dir', 'output')
        light_port = self.args.get('light_port', 'COM3')
        output_name = self.args.get('output_name', 'alert')
        
        # [核心修复] 将整个 args (包含所有配置参数) 传给 VideoProcessor
        self.processor = VideoProcessor(
            model_path=model_path,
            output_dir=output_dir,
            light_port=light_port,
            config=self.args  # <--- 新增这一行
        )
        
        # [修复] 传入 output_name_prefix
        self.alert_manager = AlertManager(output_dir=output_dir, output_name_prefix=output_name)
        self.pre_buffer = deque(maxlen=1)
        self.cap_fps = 30.0

    def log(self, msg: str):
        ts = datetime.now().strftime('%H:%M:%S')
        print(f"[{ts}] {msg}")
        self.logs.append(f"[{ts}] {msg}")

    def run(self):
        # =========================================================
        # [核心修复] 立即标记为运行中，防止前端连接时因初始化延迟而断开
        # 此时画面会显示加载中（旋转条），直到初始化完成
        # =========================================================
        self.running = True
        
        video_source = self.args.get('video', '0')
        self.log(f"正在初始化视频源: {video_source}")
        
        # [参数修复] 获取前端传递的保存和翻转参数
        save_enabled = self.args.get('save_results', True)
        flip_code = int(self.args.get('flip', 0))

        try:
            if str(video_source).isdigit():
                cam_id = int(video_source)
                self.processor.camera_manager.init_camera(cam_id)
                self.log(f"✓ 已连接摄像头 {cam_id}")
            else:
                if not os.path.exists(video_source):
                    self.log(f"❌ 视频文件不存在 -> {video_source}")
                    self.running = False
                    return
                self.processor.camera_manager.init_video(video_source)
                self.log(f"✓ 已打开视频文件 {video_source}")
        except Exception as e:
            self.log(f"❌ 视频源初始化异常: {e}")
            import traceback
            traceback.print_exc()
            self.running = False
            return

        if not self.processor.camera_manager.is_opened():
            self.log("❌ 无法打开视频源，请检查连接或路径")
            self.running = False
            return

        cap = self.processor.camera_manager.cap
        file_fps = cap.get(cv2.CAP_PROP_FPS) or 30
        self.cap_fps = file_fps
        
        # [核心修复] 获取前端设置的目标FPS，而不是使用文件原始FPS
        target_fps = float(self.args.get('fps', 30.0))
        self.pre_buffer = deque(maxlen=int(file_fps * 5))
        
        self.log(f"✓ 系统启动 | 目标FPS: {target_fps}")

        frame_count = 0
        while not self._stop_event.is_set() and self.processor.camera_manager.is_opened():
            # [核心修复] 记录本帧开始时刻，用于后续计算实际处理耗时
            frame_start_time = time.time()
            
            self.processor.fps_manager.start_timer()
            
            success, frame = self.processor.camera_manager.read_frame()
            if not success:
                self.log("⚠ 视频播放结束或流中断")
                break
            
            # [参数修复] 应用图像翻转（如果前端设置了翻转）
            if flip_code != 0:
                frame = cv2.flip(frame, flip_code)

            try:
                # 核心处理
                annotated_frame, tracked_boxes, alerts = \
                    self.processor.frame_processor.process_frame(frame, visualize=True)
                
                # 更新 Web 显示帧
                ret, jpg = cv2.imencode('.jpg', annotated_frame)
                if ret:
                    with self.frame_lock:
                        self.latest_frame = jpg.tobytes()

                # 告警处理
                self.pre_buffer.append(annotated_frame)
                
                if alerts:
                    try:
                        # [参数修复] 只在启用保存时才进行录制
                        if save_enabled:
                            task = self.alert_manager.start_recording(annotated_frame, self.cap_fps, alerts)
                            if task:
                                self.alert_manager.write_pre_buffer(self.pre_buffer, task)
                        
                        # 告警日志始终输出（无论是否保存视频）
                        alert_str_list = []
                        for item in alerts:
                            if isinstance(item, dict):
                                tid = item.get('track_id', '?')
                                missing = item.get('missing', [])
                                missing_names = [m[1] for m in missing]
                                alert_str_list.append(f"ID{tid}缺:{','.join(missing_names)}")
                            else:
                                alert_str_list.append(str(item))
                        
                        t = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        self.alerts.append({'time': t, 'alerts': alerts})
                        self.log(f"✓ 告警: {'; '.join(alert_str_list)}")
                    except Exception as e:
                        self.log(f"⚠ 告警记录异常: {e}")
                
                self.alert_manager.write_frame(annotated_frame)
                frame_count += 1

            except Exception as e:
                self.log(f"❌ 帧处理错误: {e}")
                import traceback
                traceback.print_exc()
                break

            self.processor.fps_manager.end_timer()
            
            # =======================================================
            # [核心修复] 使用前端设置的FPS，不受文件原始FPS限制
            # =======================================================
            processing_time = time.time() - frame_start_time
            
            if not str(video_source).isdigit():
                # 视频文件模式：按前端设置的目标FPS（支持倍速播放）
                target_interval = 1.0 / target_fps if target_fps > 0 else 0.033
                wait_time = max(0.0001, target_interval - processing_time)
                time.sleep(wait_time)
            else:
                # 摄像头模式：全速运行，仅极短休眠释放 CPU
                time.sleep(0.0001)

        # 结束清理
        self.processor.release()
        self.alert_manager.cleanup()
        self.running = False
        self.log(f"✓ 检测线程已退出 (共处理 {frame_count} 帧)")

    def stop(self):
        self._stop_event.set()

    def is_running(self):
        return self.running

    def get_frame(self):
        with self.frame_lock:
            return self.latest_frame
    
    def get_logs(self):
        return list(self.logs)
    
    def list_alerts(self):
        return self.alert_manager.list_alerts()
    
    def list_alert_files(self):
        return self.alert_manager.list_alert_files()
