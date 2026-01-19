import cv2
import os
import queue
import threading
from datetime import datetime

class AlertManager:
    def __init__(self, output_dir, output_name_prefix='alert'):
        self.output_dir = output_dir
        self.prefix = output_name_prefix  # 存储输出文件前缀
        self.current_alert_file = None
        self.recording_end_time = 0
        
        # [关键修复] 初始化任务字典，防止 "no attribute 'save_tasks'" 错误
        self.save_tasks = {} 
        
        # 异步写入队列
        self.write_queue = queue.Queue(maxsize=300) 
        self.is_running = True
        
        # 启动后台写入线程
        self.writer_thread = threading.Thread(target=self._writer_worker, daemon=True)
        self.writer_thread.start()

        self._ensure_dir(os.path.join(output_dir, "videos"))

    def _ensure_dir(self, path):
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

    def _writer_worker(self):
        """后台消费者线程：处理硬盘IO"""
        writers = {} # 存储路径与 VideoWriter 的映射
        
        while self.is_running:
            try:
                task = self.write_queue.get(timeout=1)
            except queue.Empty:
                continue

            cmd = task.get('cmd')
            path = task.get('path')
            
            try:
                if cmd == 'OPEN':
                    if path not in writers:
                        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                        writers[path] = cv2.VideoWriter(path, fourcc, task['fps'], task['size'])
                    
                elif cmd == 'WRITE':
                    if path in writers:
                        writers[path].write(task['frame'])
                        
                elif cmd == 'CLOSE':
                    if path in writers:
                        writers[path].release()
                        del writers[path]
                        
                elif cmd == 'STOP_THREAD':
                    for w in writers.values(): w.release()
                    break
            except Exception as e:
                print(f"[AlertManager] 写入异常: {e}")
            finally:
                self.write_queue.task_done()

    def start_recording(self, frame, fps, alerts):
        """主线程调用：开启录制"""
        now = datetime.now()
        self.recording_end_time = now.timestamp() + 5.0 # 报警后持续录制5秒
        
        if self.current_alert_file:
            return self.current_alert_file
        
        date_str = now.strftime('%Y%m%d')
        time_str = now.strftime('%H%M%S')
        save_dir = os.path.join(self.output_dir, date_str)
        self._ensure_dir(save_dir)
        
        # [修复] 使用自定义前缀生成文件名
        filepath = os.path.join(save_dir, f"{self.prefix}_{date_str}_{time_str}.mp4")
        h, w = frame.shape[:2]
        
        self.write_queue.put({
            'cmd': 'OPEN',
            'path': filepath,
            'fps': fps,
            'size': (w, h)
        })
        
        self.current_alert_file = filepath
        # 将文件路径记录在任务字典中
        self.save_tasks[filepath] = True 
        return filepath

    def write_pre_buffer(self, pre_buffer, task_file):
        """写入预留缓冲"""
        if not self.current_alert_file or task_file != self.current_alert_file:
            return
        for f in list(pre_buffer):
            self.write_queue.put({
                'cmd': 'WRITE',
                'path': task_file,
                'frame': f.copy()
            })

    def write_frame(self, frame):
        """持续写入当前帧"""
        if not self.current_alert_file:
            return

        self.write_queue.put({
            'cmd': 'WRITE',
            'path': self.current_alert_file,
            'frame': frame.copy()
        })
        
        if datetime.now().timestamp() > self.recording_end_time:
            self.stop_recording()

    def stop_recording(self):
        if self.current_alert_file:
            path = self.current_alert_file
            self.write_queue.put({'cmd': 'CLOSE', 'path': path})
            if path in self.save_tasks:
                del self.save_tasks[path]
            self.current_alert_file = None

    def cleanup(self):
        self.is_running = False
        self.write_queue.put({'cmd': 'STOP_THREAD'})