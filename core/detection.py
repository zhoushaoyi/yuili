import numpy as np
from ultralytics import YOLO
from collections import defaultdict
from typing import List, Tuple


class DetectionManager:
    """目标检测管理模块"""
    
    def __init__(self, model_path, conf_threshold=0.5):
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold  # 存储置信度参数
        # 忽略区域，列表[ (x1,y1,x2,y2), ... ]，坐标为像素
        self.ignore_regions: List[Tuple[int,int,int,int]] = []
    
    def set_ignore_regions(self, regions: List[Tuple[int,int,int,int]]):
        """设置忽略区域，区域内目标将被忽略（不参与检测/计数/追踪）。"""
        self.ignore_regions = regions or []
    
    def is_in_ignored(self, x1: float, y1: float, x2: float, y2: float) -> bool:
        """判断框中心是否位于忽略区域中。"""
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        for rx1, ry1, rx2, ry2 in self.ignore_regions:
            if cx >= rx1 and cx <= rx2 and cy >= ry1 and cy <= ry2:
                return True
        return False
    
    def process_frame(self, frame, confidence_threshold=None):
        """进行目标检测并进行置信度过滤"""
        # [修复] 使用实例属性中存储的置信度，如果没有传入参数
        if confidence_threshold is None:
            confidence_threshold = self.conf_threshold
        results = self.model.predict(source=frame, verbose=False) #关闭YOLO调试信息
        boxes = results[0].boxes
        filtered_boxes = []

        # 过滤低置信度框，并应用忽略区域过滤
        for box in boxes:
            if box.conf[0] > confidence_threshold:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                if not self.is_in_ignored(x1, y1, x2, y2):
                    filtered_boxes.append(box)

        # annotated_frame = results[0].plot()  # 绘制目标检测框
        return frame, filtered_boxes
    
    def get_detections_for_tracking(self, filtered_boxes, target_class=0):
        """
        将YOLO检测结果转换为SORT追踪格式
        参数:
            filtered_boxes: YOLO检测结果列表
            target_class: 目标类别，默认为0（storage box）
        返回:
            numpy数组，格式为 [x1,y1,x2,y2,score]，只包含指定类别
        """
        detections = []
        
        for box in filtered_boxes:
            # 检查类别是否为指定类别
            if int(box.cls[0]) == target_class:
                # 获取边界框坐标 [x1, y1, x2, y2]
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                # 获取置信度
                confidence = box.conf[0].cpu().numpy()
                # 添加到检测列表
                detections.append([x1, y1, x2, y2, confidence])
        
        if len(detections) > 0:
            return np.array(detections)
        else:
            return np.empty((0, 5))
    
    def split_by_class(self, filtered_boxes):
        """按类别拆分检测结果，返回 dict[class_id] = list(box).
        注意：box原样返回（YOLO的box对象）。
        """
        by_class = defaultdict(list)
        for box in filtered_boxes:
            cls_id = int(box.cls[0])
            by_class[cls_id].append(box)
        return by_class
    
    def boxes_to_ndarray(self, boxes_with_cls):
        """将YOLO box对象转换为 ndarray: [x1,y1,x2,y2,score,cls] 列表。"""
        rows = []
        for box in boxes_with_cls:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            score = float(box.conf[0].cpu().numpy())
            cls_id = int(box.cls[0])
            rows.append([x1, y1, x2, y2, score, cls_id])
        if rows:
            return np.array(rows, dtype=float)
        return np.empty((0, 6), dtype=float)
    
    @staticmethod
    def assign_items_to_boxes(class0_boxes_xyxy, items_xyxycls, debug=False):
        """将非class0物品分配到包含其中心点的class0框中。
        
        参数:
          class0_boxes_xyxy: ndarray N x 4 (x1,y1,x2,y2) - 追踪到的storage box框
          items_xyxycls: ndarray M x 6 (x1,y1,x2,y2,score,cls) - 检测到的物品
          debug: 是否打印调试信息
          
        返回:
          dict box_index -> list of item rows
          
        说明:
          - 只对class0框范围内的物品进行计数
          - 使用中心点判断物品是否在class0框内
          - 返回分配情况，外层根据配置进行计数
        """
        from collections import defaultdict as dd
        assign = dd(list)
        
        if debug:
            print(f"\n[分配物品] 开始分配物品到class0框")
            print(f"  class0框数量: {len(class0_boxes_xyxy)}")
            print(f"  待分配物品数: {len(items_xyxycls)}")
        
        # 遍历每个追踪到的class0框
        for i, b in enumerate(class0_boxes_xyxy):
            x1, y1, x2, y2 = b
            box_width = x2 - x1
            box_height = y2 - y1
            
            if debug:
                print(f"\n  框 {i}: 位置=({x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}) 大小={box_width:.0f}x{box_height:.0f}")
            
            matched_items = []
            
            # 检查每个物品是否在该框内
            for row in items_xyxycls:
                ix1, iy1, ix2, iy2, score, cls_id = row
                
                # 计算物品的中心点和尺寸
                item_cx = (ix1 + ix2) / 2.0
                item_cy = (iy1 + iy2) / 2.0
                item_width = ix2 - ix1
                item_height = iy2 - iy1
                
                # 判断物品中心点是否在class0框内
                # 条件：中心点坐标在框的边界内
                center_in_box = (item_cx >= x1 and item_cx <= x2 and 
                                item_cy >= y1 and item_cy <= y2)
                
                if center_in_box:
                    assign[i].append(row)
                    matched_items.append((int(cls_id), item_cx, item_cy, score))
                    if debug:
                        cls_name = f"class{int(cls_id)}"
                        print(f"    ✓ {cls_name}: 中心({item_cx:.0f},{item_cy:.0f}) 置信度={score:.2f}")
                elif debug:
                    # 未匹配的物品也输出，便于调试
                    cls_name = f"class{int(cls_id)}"
                    print(f"    ✗ {cls_name}: 中心({item_cx:.0f},{item_cy:.0f}) 在框外")
            
            if debug and not matched_items:
                print(f"    (框内未检测到物品)")
        
        if debug:
            print(f"\n[分配结果] 总共分配了 {sum(len(v) for v in assign.values())} 个物品\n")
        
        return assign
    
    def print_detection_info(self, filtered_boxes):
        """打印检测信息"""
        print(f"Filtered boxes: {len(filtered_boxes)}")
        for box in filtered_boxes:
            print(f"Class: {box.cls[0]}, Confidence: {box.conf[0]}")
