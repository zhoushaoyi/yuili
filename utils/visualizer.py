import cv2


class Visualizer:
    """
    可视化模块，负责绘制追踪结果
    """
    
    def __init__(self):
        """
        初始化可视化器
        """
        # 预定义颜色列表，用于区分不同的追踪ID
        self.colors = [
            (255, 0, 0),    # 红色
            (0, 255, 0),    # 绿色
            (0, 0, 255),    # 蓝色
            (255, 255, 0),  # 青色
            (255, 0, 255),  # 洋红色
            (0, 255, 255),  # 黄色
            (128, 0, 128),  # 紫色
            (255, 165, 0),  # 橙色
            (0, 128, 128),  # 深青色
            (128, 128, 0),  # 橄榄色
            (255, 192, 203), # 粉色
            (0, 128, 0),    # 深绿色
            (128, 0, 0),    # 深红色
            (0, 0, 128),    # 深蓝色
            (128, 128, 128), # 灰色
            (255, 255, 255), # 白色
        ]
    
    def get_color(self, track_id):
        """
        根据追踪ID获取颜色
        """
        return self.colors[track_id % len(self.colors)]
    
    def draw_tracked_boxes(self, frame, tracked_boxes, class_name="storage box"):
        """
        在帧上绘制追踪框和ID
        参数:
            frame: 输入帧
            tracked_boxes: 追踪结果数组 [x1,y1,x2,y2,id]
            class_name: 类别名称
        返回:
            绘制了追踪框的帧
        """
        annotated_frame = frame.copy()

        for box in tracked_boxes:
            if len(box) >= 5:  # 确保有足够的元素 [x1,y1,x2,y2,id]
                x1, y1, x2, y2, track_id = int(box[0]), int(box[1]), int(box[2]), int(box[3]), int(box[4])
                
                # 获取该ID对应的颜色
                color = self.get_color(track_id)
                
                # 绘制边界框
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                
                # 仅显示追踪ID（不显示类别名）
                label = f"#{track_id}"
                
                # 计算文本大小
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.6
                font_thickness = 2
                (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)
                
                # 绘制文本背景
                cv2.rectangle(annotated_frame, 
                             (x1, y1 - text_height - baseline - 5), 
                             (x1 + text_width, y1), 
                             color, -1)
                
                # 绘制文本
                cv2.putText(annotated_frame, label, 
                           (x1, y1 - baseline - 5), 
                           font, font_scale, (255, 255, 255), font_thickness)
        
        return annotated_frame

    def draw_item_boxes(self, frame, rects_by_track):
        """绘制class0区域内的其他目标框（无标签）。
        rects_by_track: dict track_id -> list of [x1,y1,x2,y2,cls]
        不同类别使用不同颜色（class1..class6稳定映射）。
        """
        annotated = frame.copy()
        # 为class1..class6定义稳定颜色
        class_colors = {
            1: (0, 255, 255),   # comb clamp -> yellow
            2: (255, 0, 255),   # hair clipper -> magenta
            3: (0, 165, 255),   # lubricant -> orange
            4: (255, 0, 0),     # instructions -> blue
            5: (0, 255, 0),     # data cable -> green
            6: (128, 0, 128),   # brush -> purple
        }
        default_color = (200, 200, 200)
        for tid, rects in rects_by_track.items():
            for r in rects:
                x1, y1, x2, y2 = [int(v) for v in r[:4]]
                cls_id = int(r[4]) if len(r) > 4 else -1
                color = class_colors.get(cls_id, default_color)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        return annotated

    def draw_storage_boxes(self, frame, tracked_boxes):
        """仅绘制Class0盒子及追踪ID（不绘制其它类别的框）。"""
        return self.draw_tracked_boxes(frame, tracked_boxes, "storage box")

    def draw_requirements_labels(self, frame, tracked_box, labels):
        """在盒子右侧绘制纵向标签队列（仅quantity>0）。
        labels: [{name, required, achieved, completed}]
        颜色：completed=True -> 绿色；否则红色。
        文本："name x need/achieved"
        """
        annotated = frame.copy()
        x1, y1, x2, y2, track_id = [int(tracked_box[i]) for i in range(5)]
        # 起始位置：框右侧，顶端对齐
        start_x = x2 + 8
        start_y = y1
        line_h = 22
        for idx, lab in enumerate(labels):
            name = lab['name']
            need = lab['required']
            achv = lab['achieved']
            if need <= 0:
                continue
            ok = lab['completed']
            color = (0, 200, 0) if ok else (0, 0, 255)
            text = f"{name} x {need}/{achv}"
            # 背板
            font = cv2.FONT_HERSHEY_SIMPLEX
            scale = 0.6
            thick = 1
            (tw, th), bl = cv2.getTextSize(text, font, scale, 1)
            pad = 4
            y_top = start_y + idx * line_h
            cv2.rectangle(annotated, (start_x, y_top), (start_x + tw + pad*2, y_top + th + pad*2), color, -1)
            cv2.putText(annotated, text, (start_x + pad, y_top + th + pad - 2), font, scale, (255, 255, 255), thick)
        return annotated

    def draw_center_alert(self, frame, missing_info_list):
        """在屏幕中央绘制报警文本（支持多条）。
        例如："The ID[3] is missing class[class1][comb clamp]"
        """
        if not missing_info_list:
            return frame
        annotated = frame.copy()
        h, w = annotated.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.8
        thick = 2
        y = h // 2 - 20 * (len(missing_info_list) - 1)
        for alert in missing_info_list:
            tid = alert['track_id']
            parts = ", ".join([f"class[{ck}][{nm}]" for ck, nm in alert['missing']])
            text = f"The ID[{tid}] is missing {parts}"
            (tw, th), bl = cv2.getTextSize(text, font, scale, thick)
            x = (w - tw) // 2
            # 背板
            cv2.rectangle(annotated, (x - 8, y - th - 8), (x + tw + 8, y + bl + 8), (0, 0, 255), -1)
            cv2.putText(annotated, text, (x, y), font, scale, (255, 255, 255), thick)
            y += th + 20
        return annotated
    
    def print_tracking_info(self, tracked_boxes, class_name="storage box"):
        """
        打印追踪信息到控制台
        参数:
            tracked_boxes: 追踪结果数组 [x1,y1,x2,y2,id]
            class_name: 类别名称
        """
        if len(tracked_boxes) > 0:
            print(f"追踪到 {len(tracked_boxes)} 个 {class_name}:")
            for box in tracked_boxes:
                if len(box) >= 5:
                    x1, y1, x2, y2, track_id = int(box[0]), int(box[1]), int(box[2]), int(box[3]), int(box[4])
                    width = x2 - x1
                    height = y2 - y1
                    print(f"  {class_name} #{track_id}: 位置({x1},{y1}) 大小({width}x{height})")
        else:
            print(f"未追踪到 {class_name}")
