from flask import Flask, Response, request, jsonify, send_file, abort, render_template
from modules.detector_thread import DetectorThread
from config.config import Config
from utils.config_loader import load_user_settings, save_user_settings
import threading
import time
import os
import signal
import json

app = Flask(__name__)

# 全局检测线程实例
detector = None
detector_lock = threading.Lock()
# 防止短时间内重复启动
starting = False

# 前端获取配置的接口
@app.route('/get_user_config', methods=['GET'])
def get_user_config():
    """获取用户保存的检测参数配置（用于Web页面表单初始化）。
    
    说明:
        - 返回 config/user_settings.json 中保存的参数
        - 这些是用户在Web界面上设置的检测参数（FPS、置信度等）
        - 与 Configuration.json (物品清单) 分离
    """
    saved_config = load_user_settings()
    if not saved_config:
        saved_config = Config.DEFAULT_DETECTION_PARAMS
    return jsonify(saved_config)

@app.route('/start_detection', methods=['POST'])
def start_detection():
    """启动检测线程。
    
    流程:
        1. 保存当前Web界面参数到 user_settings.json
        2. 创建 DetectorThread，其中会:
           - 创建 VideoProcessor
           - VideoProcessor 会强制重新加载 Configuration.json (业务配置)
        3. 启动检测线程
    """
    global detector
    global starting
    with detector_lock:
        # 防止重复快速点击/启动
        if starting:
            return jsonify({'status': 'error', 'message': '正在启动中，请稍后'})
        starting = True
        try:
            # 如果已存在旧线程且仍在运行，先请求停止并等待短时间再启动新线程，避免并发运行
            if detector and detector.is_alive():
                try:
                    detector.stop()
                    detector.join(timeout=3.0)
                except Exception:
                    pass
            args = request.form.to_dict()
            
            # [关键] 启动前，保存当前Web界面参数到 config/user_settings.json
            print(f"[Web API] 收到启动请求，当前参数:")
            for k, v in sorted(args.items()):
                print(f"  {k}: {v}")
            save_user_settings(args)
            
            # 参数类型转换和默认值处理
            if 'save_video' in args:
                args['save_results'] = args['save_video'].lower() in ('1', 'true', 'yes')
                del args['save_video']
            
            # 使用配置模块的默认值填充缺失参数
            config = Config.get_detection_config(args)
            
            # [关键] 创建检测线程
            # DetectorThread 会创建 VideoProcessor，
            # 而 VideoProcessor 会强制重新加载 Configuration.json
            print(f"[Web API] 创建 DetectorThread，准备加载业务配置...")
            detector = DetectorThread(config)
            detector.start()
            time.sleep(0.1)
            print(f"[Web API] DetectorThread 已启动")
            return jsonify({'status': 'success', 'message': '检测线程已启动'})
        finally:
            starting = False


@app.route('/shutdown', methods=['POST', 'GET'])
def shutdown():
    """优雅停止检测线程并退出进程（用于页面卸载时调用）。"""
    global detector, detector_lock
    with detector_lock:
        if detector and detector.is_alive():
            try:
                detector.stop()
                detector.join(timeout=3.0)
            except Exception:
                pass
    
    # 在后台线程中延迟杀死进程，这样可以先响应前端请求
    def kill_process():
        time.sleep(0.5)
        try:
            os.kill(os.getpid(), signal.SIGTERM)
        except Exception:
            pass
    
    kill_thread = threading.Thread(target=kill_process, daemon=True)
    kill_thread.start()
    
    return jsonify({'status': 'success', 'message': '已请求停止检测，程序将在1秒后关闭'})


@app.route('/get_config', methods=['GET'])
def get_config():
    # 返回默认配置，前端用于表单初始化
    return jsonify(Config.DEFAULT_DETECTION_PARAMS)


@app.route('/stop_detection', methods=['POST'])
def stop_detection():
    global detector
    with detector_lock:
        if not detector:
            return jsonify({'status': 'success', 'message': '没有运行的检测'})
        detector.stop()
        detector.join(timeout=3.0)
        # 清理全局引用，允许后续干净启动
        try:
            if not detector.is_alive():
                detector = None
        except Exception:
            detector = None
        return jsonify({'status': 'success', 'message': '已发送停止请求'})


@app.route('/get_logs', methods=['GET'])
def get_logs():
    global detector
    if not detector:
        return jsonify({'logs': [], 'is_running': False})
    
    # 获取日志，避免重复发送相同的日志
    try:
        all_logs = list(detector.logs)
        # 返回日志但不清空，让前端自行管理重复过滤
        # 前端应该通过时间戳或日志ID来过滤重复
    except Exception:
        all_logs = []
    
    # 只要线程还活着，就返回 True，保持前端不显示"意外停止"
    return jsonify({'logs': all_logs, 'is_running': detector.is_alive()})


@app.route('/video_feed')
def video_feed():
    global detector
    # 允许初始化阶段（detector非空但running可能刚设为True）
    if not detector:
        return Response(status=204)

    def gen():
        try:
            while True:
                # 只要线程对象存在且活着，就继续循环
                if not detector or not detector.is_alive():
                    break
                
                frame = detector.get_frame()
                if frame:
                    try:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n'
                               b'Content-Length: ' + str(len(frame)).encode() + b'\r\n\r\n'
                               + frame + b'\r\n')
                    except GeneratorExit:
                        # 客户端断开连接，尝试优雅停止检测线程
                        with detector_lock:
                            try:
                                if detector and detector.is_alive():
                                    detector.stop()
                            except Exception:
                                pass
                        break
                else:
                    # 初始化中，还没出图，等待一下，不要退出！
                    time.sleep(0.05)
        except Exception as e:
            # 遇到发送错误时尝试停止检测线程
            print(f"视频流异常: {e}")
            with detector_lock:
                try:
                    if detector and detector.is_alive():
                        detector.stop()
                except Exception:
                    pass
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/alerts', methods=['GET'])
def list_alerts():
    global detector
    if not detector:
        return jsonify([])
    return jsonify(detector.list_alerts())


@app.route('/alert_files', methods=['GET'])
def list_alert_files():
    global detector
    if not detector:
        return jsonify([])
    return jsonify(detector.list_alert_files())


@app.route('/download_alert')
def download_alert():
    path = request.args.get('path')
    if not path:
        abort(400)
    try:
        return send_file(path, as_attachment=True)
    except Exception:
        abort(404)


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    # 生产环境部署建议：threads=3 以上，避免视频流阻塞心跳
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=2)
