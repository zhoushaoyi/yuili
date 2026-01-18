import serial
import threading
import time
from typing import Optional


class LightController:
    """三色灯控制模块"""
    
    # 功能对应的报文
    COMMANDS = {
        "关闭全部": bytes.fromhex("01 05 00 0A 00 00 ED C8"),
        "打开测试功能": bytes.fromhex("01 05 00 0B 01 00 BD 98"),
        "红灯爆闪": bytes.fromhex("01 05 00 01 04 00 9E CA"),
        "红灯快闪": bytes.fromhex("01 05 00 01 03 00 9C FA"),
        "红灯慢闪": bytes.fromhex("01 05 00 01 02 00 9D 6A"),
        "红灯常亮": bytes.fromhex("01 05 00 01 01 00 9D 9A"),
        "关闭红灯": bytes.fromhex("01 05 00 01 00 00 9C 0A"),
        "绿灯爆闪": bytes.fromhex("01 05 00 02 04 00 6E CA"),
        "绿灯快闪": bytes.fromhex("01 05 00 02 03 00 6C FA"),
        "绿灯慢闪": bytes.fromhex("01 05 00 02 02 00 6D 6A"),
        "绿灯常亮": bytes.fromhex("01 05 00 02 01 00 6D 9A"),
        "关闭绿灯": bytes.fromhex("01 05 00 02 00 00 6C 0A"),
        "蓝灯爆闪": bytes.fromhex("01 05 00 03 04 00 3F 0A"),
        "蓝灯快闪": bytes.fromhex("01 05 00 03 03 00 3D 3A"),
        "蓝灯慢闪": bytes.fromhex("01 05 00 03 02 00 3C AA"),
        "蓝灯常亮": bytes.fromhex("01 05 00 03 01 00 3C 5A"),
        "关闭蓝灯": bytes.fromhex("01 05 00 03 00 00 3D CA"),
        "黄灯爆闪": bytes.fromhex("01 05 00 04 04 00 8E CB"),
        "黄灯快闪": bytes.fromhex("01 05 00 04 03 00 8C FB"),
        "黄灯慢闪": bytes.fromhex("01 05 00 04 02 00 8D 6B"),
        "黄灯常亮": bytes.fromhex("01 05 00 04 01 00 8D 9B"),
        "关闭黄灯": bytes.fromhex("01 05 00 04 00 00 8C 0B"),
        "蜂鸣爆响": bytes.fromhex("01 05 00 05 04 00 DF 0B"),
        "蜂鸣快响": bytes.fromhex("01 05 00 05 03 00 DD 3B"),
        "蜂鸣慢响": bytes.fromhex("01 05 00 05 02 00 DC AB"),
        "蜂鸣常响": bytes.fromhex("01 05 00 05 01 00 DC 5B"),
        "关闭蜂鸣": bytes.fromhex("01 05 00 05 00 00 DD CB"),
        "红灯爆闪+蜂鸣": bytes.fromhex("01 05 00 06 04 00 2F 0B"),
        "红灯快闪+蜂鸣": bytes.fromhex("01 05 00 06 03 00 2D 3B"),
        "红灯慢闪+蜂鸣": bytes.fromhex("01 05 00 06 02 00 2C AB"),
        "红灯常亮+蜂鸣": bytes.fromhex("01 05 00 06 01 00 2C 5B"),
        "关闭红灯+蜂鸣": bytes.fromhex("01 05 00 06 00 00 2D CB"),
    }
    
    def __init__(self, port='COM1', baudrate=9600, enabled=True):
        """
        初始化三色灯控制器
        Args:
            port: 串口端口，默认COM1
            baudrate: 波特率，默认9600
            enabled: 是否启用三色灯控制，默认True
        """
        self.port = port
        self.baudrate = baudrate
        self.enabled = enabled
        self.ser: Optional[serial.Serial] = None
        self.lock = threading.Lock()
        self.current_state = "关闭全部"  # 当前状态
        self.timer_thread: Optional[threading.Thread] = None
        self.timer_active = False
        
        if self.enabled:
            try:
                self.ser = serial.Serial(
                    port=port,
                    baudrate=baudrate,
                    bytesize=8,
                    parity='N',
                    stopbits=1,
                    timeout=1
                )
                print(f"三色灯控制器已连接到 {port}")
            except Exception as e:
                print(f"警告: 无法连接到三色灯设备 {port}: {e}")
                print("三色灯控制功能将被禁用")
                self.enabled = False
                self.ser = None
        
    # 提供给外部查询当前是否有定时任务在运行
    def is_timer_running(self):
        """检查是否有定时任务（闪烁/蜂鸣）正在运行"""
        return self.timer_active
        
    def _send_command(self, command_name: str):
        """发送命令到串口"""
        if not self.enabled or self.ser is None:
            return
            
        #状态去重
        if command_name == self.current_state:
            return

        if command_name not in self.COMMANDS:
            print(f"警告: 未知的命令 '{command_name}'")
            return
        
        try:
            with self.lock:
                self.ser.write(self.COMMANDS[command_name])
                self.current_state = command_name
        except Exception as e:
            print(f"发送三色灯命令失败: {e}")
    
    def yellow_light_on(self):
        """黄灯常亮"""
        self._cancel_timer()
        self._send_command("黄灯常亮")

    def blue_light_on(self):
        """蓝灯常亮"""
        self._cancel_timer()
        self._send_command("蓝灯常亮")

    def green_light_on(self, duration=0.5):
        """绿灯常亮指定时间后恢复蓝灯"""
        self._send_command("绿灯常亮")
        self._start_timer(duration, self.blue_light_on)

    def red_light_flash_with_buzzer(self, duration=2.0):
        """红灯闪烁并蜂鸣指定时间后恢复蓝灯"""
        self._send_command("红灯快闪+蜂鸣")

        def _restore():
            self._send_command("关闭红灯+蜂鸣")
            time.sleep(0.1)
            self.blue_light_on()

        self._start_timer(duration, _restore)
    
    def turn_off_all(self):
        """关闭全部"""
        self._cancel_timer()
        self._send_command("关闭全部")

    def _start_timer(self, duration: float, callback):
        """启动定时器，在指定时间后执行回调"""
        self._cancel_timer()
        self.timer_active = True
        
        def timer_func():
            time.sleep(duration)
            if self.timer_active:
                callback()
                self.timer_active = False
        
        self.timer_thread = threading.Thread(target=timer_func, daemon=True)
        self.timer_thread.start()
    
    def _cancel_timer(self):
        """取消定时器"""
        self.timer_active = False
        if self.timer_thread and self.timer_thread.is_alive():
            # 等待线程结束
             if threading.current_thread() != self.timer_thread:
                self.timer_thread.join(timeout=0.1)
    
    def close(self):
        """关闭串口连接"""
        self._cancel_timer()
        if self.ser and self.ser.is_open:
            try:
                self.turn_off_all()
                self.ser.flush() 
                time.sleep(0.1) # 增加短暂延时，确保串口命令发送完毕后再关闭
                self.ser.close()
                print("三色灯控制器已关闭")
            except Exception as e:
                print(f"关闭三色灯控制器时出错: {e}")

