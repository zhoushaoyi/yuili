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
    
    def process_frame(self, frame, visualize=True, debug=False):
        """处理单帧，返回标注后的帧、追踪框和报警信息
        
        参数:
          frame: 输入帧
          visualize: 是否进行可视化
          debug: 是否输出详细的调试信息
          
        流程:
          1. 对整个帧进行YOLO检测
          2. 将class0检测结果送给SORT追踪器追踪
          3. 将其他class的检测结果分配到追踪到的class0框内
          4. 根据配置更新装配状态（只计算class0框内的物品）
          5. 处理消失的box（报警）
          6. 如需可视化，绘制框和标签
        """
        # 第一步：进行目标检测（整个帧）
        annotated_frame, filtered_boxes = self.detection_manager.process_frame(frame)
        
        if debug:
            print(f"\n{'='*70}")
            print(f"[帧处理] 开始处理帧")
            print(f"  检测到的目标总数: {len(filtered_boxes)}")
        
        # 第二步：按类别拆分检测结果
        by_class = self.detection_manager.split_by_class(filtered_boxes)
        
        if debug:
            for cls_id, boxes in sorted(by_class.items()):
                print(f"  class{cls_id}: {len(boxes)} 个目标")
        
        # 第三步：将class0检测结果转为SORT格式
        class0_nd = self.detection_manager.get_detections_for_tracking(
            by_class.get(0, []), target_class=0
        )
        
        if debug:
            print(f"\n[class0 追踪] 准备追踪class0 (storage box)")
            print(f"  本帧class0检测数: {len(class0_nd)}")
        
        # 第四步：更新SORT追踪器（只追踪class0）
        tracked_boxes, disappeared_ids = self.tracker_manager.update_tracks(class0_nd, target_class=0)
        
        if debug:
            print(f"  追踪到的class0数: {len(tracked_boxes)}")
            if len(tracked_boxes) > 0:
                for tb in tracked_boxes:
                    print(f"    track_id={int(tb[4])}: 框=({tb[0]:.0f},{tb[1]:.0f},{tb[2]:.0f},{tb[3]:.0f})")
        
        # 第五步：提取追踪框的XYXY坐标（用于物品分配）
        tracked_xyxy = tracked_boxes[:, :4] if tracked_boxes.size > 0 else np.empty((0, 4))
        
        # 第六步：收集非class0的检测结果
        others_list = []
        for cls_id, lst in by_class.items():
            if cls_id == 0:
                continue
            others_list.extend(lst)
        others_nd = self.detection_manager.boxes_to_ndarray(others_list)
        
        if debug:
            print(f"\n[物品分配] 准备分配物品到class0框")
            print(f"  待分配的物品总数: {len(others_nd)} (class1-class9)")
        
        # 第七步：将物品分配到class0框（根据中心点位置）
        items_assign = {}
        rects_by_track = {}
        
        if tracked_boxes.size > 0 and others_nd.size > 0:
            # 关键：使用改进的分配逻辑，只计算class0框内的物品
            assign = self.detection_manager.assign_items_to_boxes(
                tracked_xyxy, others_nd, debug=debug
            )
            
            # 第八步：为每个追踪的class0计数物品
            for idx, rows in assign.items():
                c = {}
                rects = []
                
                for r in rows:
                    cls_id = int(r[5])
                    # 只计算class1-class9的物品
                    if 1 <= cls_id <= 9:
                        key = f'class{cls_id}'
                        c[key] = c.get(key, 0) + 1
                    rects.append([r[0], r[1], r[2], r[3], cls_id])
                
                items_assign[int(tracked_boxes[idx, 4])] = Counter(c)
                rects_by_track[int(tracked_boxes[idx, 4])] = rects
                
                if debug:
                    track_id = int(tracked_boxes[idx, 4])
                    print(f"  track_id={track_id}: 计数结果={dict(c)}")
        
        if debug and (tracked_boxes.size == 0 or others_nd.size == 0):
            print(f"  (跳过物品分配: class0框数={len(tracked_boxes)}, 物品数={len(others_nd)})")
        
        # 第九步：更新装配状态（InventoryManager）
        self.inventory.update_for_frame(tracked_boxes, items_assign)
        
        # 第十步：处理消失的追踪box（报警逻辑）
        alerts, disappearance_status = self.inventory.handle_disappearance(disappeared_ids)
        if alerts:
            print(f"[报警] 触发报警: {alerts}")
        
        if debug:
            print(f"{'='*70}\n")

        # 可视化部分
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
        
        # 返回报警信息以便外层触发存储等操作
        return annotated_frame, tracked_boxes, alerts
    
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


