import numpy as np
from collections import Counter


class FrameProcessor:
    """单帧处理模块，统一处理检测、追踪、可视化逻辑"""
    
    def __init__(self, detection_manager, tracker_manager, visualizer, fps_manager, inventory, light_controller=None):
        self.detection_manager = detection_manager
        self.tracker_manager = tracker_manager
        self.visualizer = visualizer
        self.fps_manager = fps_manager
        self.inventory = inventory
        self.light_controller = light_controller
    
    def process_frame(self, frame, visualize=True):
        """处理单帧，返回标注后的帧和相关信息"""
        # 进行目标检测
        annotated_frame, filtered_boxes = self.detection_manager.process_frame(frame)
        
        # 拆分各类
        by_class = self.detection_manager.split_by_class(filtered_boxes)
        
        # class0转为ndarray用于追踪
        class0_nd = self.detection_manager.get_detections_for_tracking(
            by_class.get(0, []), target_class=0
        )
        
        # 更新追踪
        tracked_boxes, disappeared_ids = self.tracker_manager.update_tracks(class0_nd, target_class=0)
        
        # 为每个追踪到的storage box统计内部件计数
        tracked_xyxy = tracked_boxes[:, :4] if tracked_boxes.size > 0 else np.empty((0, 4))
        
        # 非class0转为ndarray(含cls)
        others_list = []
        for cls_id, lst in by_class.items():
            if cls_id == 0:
                continue
            others_list.extend(lst)
        others_nd = self.detection_manager.boxes_to_ndarray(others_list)
        
        # 将内件分配到每个class0框（注意：使用追踪框）
        items_assign = {}
        rects_by_track = {}
        if tracked_boxes.size > 0 and others_nd.size > 0:
            assign = self.detection_manager.assign_items_to_boxes(tracked_xyxy, others_nd)
            # 计数 map: track_index -> Counter({'class1': n, ...})
            for idx, rows in assign.items():
                c = {}
                rects = []
                for r in rows:
                    cls_id = int(r[5])
                    if 1 <= cls_id <= 6:
                        key = f'class{cls_id}'
                        c[key] = c.get(key, 0) + 1
                    rects.append([r[0], r[1], r[2], r[3], cls_id])
                items_assign[int(tracked_boxes[idx, 4])] = Counter(c)
                rects_by_track[int(tracked_boxes[idx, 4])] = rects
        
        # 更新装配状态
        self.inventory.update_for_frame(tracked_boxes, items_assign)
        
        # 处理消失报警（只处理曾经被追踪器返回过的ID）
        alerts, disappearance_status = self.inventory.handle_disappearance(disappeared_ids)
        if alerts:
            print(f"[DEBUG] 触发报警: {alerts}")
        
        # self.fps_manager.print_fps() #调试用,输出FPS

        if visualize:
            # 仅绘制storage box框与ID
            annotated_frame = self.visualizer.draw_storage_boxes(annotated_frame, tracked_boxes)
            
            # 在class0区域内绘制其他目标框（不显示名称）
            if rects_by_track:
                annotated_frame = self.visualizer.draw_item_boxes(annotated_frame, rects_by_track)
            
            # 绘制右侧标签（显示本帧计数/需求）
            for tb in tracked_boxes:
                tid = int(tb[4])
                labels = self.inventory.get_labels_for_track(tid)
                annotated_frame = self.visualizer.draw_requirements_labels(annotated_frame, tb, labels)
            
            # 显示FPS
            annotated_frame = self.fps_manager.show_fps(annotated_frame)
            annotated_frame = self.visualizer.draw_center_alert(annotated_frame, alerts)
        else:
            annotated_frame = frame

        # 三色灯控制逻辑
        if self.light_controller:
            has_storage_box = tracked_boxes.size > 0
            self._update_light_status(has_storage_box, disappearance_status)
        return annotated_frame, tracked_boxes
    
    def _update_light_status(self, has_storage_box, disappearance_status):
        """更新三色灯状态，包含优先级控制"""
        
        # 1. 获取刚刚消失的ID状态
        completed_ids = disappearance_status.get('completed_ids', []) if disappearance_status else []
        incomplete_ids = disappearance_status.get('incomplete_ids', []) if disappearance_status else []

        # 2. 优先级最高：瞬间触发的事件
        if incomplete_ids:
            # 如果有未完成的，红灯闪烁并蜂鸣1秒（这会启动一个独立的定时器）
            self.light_controller.red_light_flash_with_buzzer(duration=1)
            return  # 触发后直接返回，防止被后续逻辑覆盖

        if completed_ids:
            # 如果消失的box全部完成，绿灯常亮0.5秒
            self.light_controller.green_light_on(duration=0.5)
            return  # 触发后直接返回

        # 3. 优先级次高：如果灯光控制器正在执行倒计时（报警中），不要打断它！
        if self.light_controller.is_timer_running():
            return

        # 4. 优先级最低：常规状态（没有报警时执行）
        if not has_storage_box:
            # 未检测到目标0类storage box时，黄灯常亮
            self.light_controller.yellow_light_on()
        else:
            # 检测到目标，正常检测状态，蓝灯常亮
            self.light_controller.blue_light_on()


