from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Any


class InventoryManager:
    """按配置管理每个storage box(track_id)的装配完成状态，并在消失时给出报警。"""

    def __init__(self, spec: Dict[str, Any], alert_display_time=90):
        self.spec = spec
        self.alert_display_time = alert_display_time  # 存储报警时长参数
        # required: class key -> required qty (>0)
        self.required = {k: v['quantity'] for k, v in spec['class0']['contains'].items() if int(v['quantity']) > 0}
        self.names = {k: v['name'] for k, v in spec['class0']['contains'].items()}
        # 状态: track_id -> {achieved: Counter, completed: {classX: bool}}
        self.state: Dict[int, Dict[str, Any]] = {}
        # 当前仍在追踪的track id集合（主要用于调试）
        self.active_ids: set[int] = set()
        # 曾经被追踪器返回过的ID集合（累积集合，用于判断消失的ID是否应该被处理）
        # 只有达到min_hits被追踪器返回的ID才会被添加到这里
        self.ever_tracked_ids: set[int] = set()

    def _ensure_track(self, track_id: int):
        if track_id not in self.state:
            self.state[track_id] = {
                'achieved': Counter(),
                'completed': {cls_key: False for cls_key in self.required.keys()},
                'is_all_completed': False,
            }

    def update_for_frame(self, tracked_boxes, items_by_track: Dict[int, Counter]):
        """
        更新当前帧的装配达成情况（按帧计数，不累计）。
        tracked_boxes: ndarray N x 5 [x1,y1,x2,y2,id]
        items_by_track: track_id -> Counter({'class1': n1, ...})
        本帧只依据当前计数对completed置位；completed一旦为True保持True。
        """
        current_ids: set[int] = set()
        for tb in tracked_boxes:
            track_id = int(tb[4])
            current_ids.add(track_id)
            # 记录曾经被追踪器返回过的ID（达到min_hits的ID）
            self.ever_tracked_ids.add(track_id)
            self._ensure_track(track_id)
            # 使用本帧计数覆盖achieved显示，但不减少既往完成状态
            frame_counts = items_by_track.get(track_id, Counter())
            # 更新已达成数量
            self.state[track_id]['achieved'].clear()
            for cls_key, num in frame_counts.items():
                if cls_key in self.required:
                    self.state[track_id]['achieved'][cls_key] = int(num)
            # 依据本帧计数置完成；一旦完成保持完成
            for cls_key, need in self.required.items():
                if not self.state[track_id]['completed'][cls_key]:
                    have = self.state[track_id]['achieved'][cls_key]
                    if have >= need:
                        self.state[track_id]['completed'][cls_key] = True
            self.state[track_id]['is_all_completed'] = all(self.state[track_id]['completed'].values()) if self.required else True
        self.active_ids = current_ids

    def handle_disappearance(self, disappeared_ids: List[int]):
        """处理追踪器报告的消失ID，返回报警及状态。
        只处理那些曾经被追踪器返回过的ID（即达到min_hits的ID）。
        这样可以确保只处理已经正常追踪的目标消失，忽略未达到min_hits就被删除的追踪器。
        
        参数:
            disappeared_ids: 追踪器报告的消失ID列表
        """
        alerts = []
        completed_ids = []
        incomplete_ids = []

        if disappeared_ids:
            print(f"[DEBUG] 追踪器报告消失ID: {disappeared_ids}")
            print(f"[DEBUG] 曾经被追踪过的ID集合: {self.ever_tracked_ids}")

        for tid in disappeared_ids or []:
            # 只处理那些曾经被追踪器返回过的ID
            if tid not in self.ever_tracked_ids:
                print(f"[DEBUG] ID {tid} 从未被追踪器返回过，跳过处理")
                continue
                
            info = self.state.get(tid)
            print(f"[DEBUG] 检查ID {tid} 的状态: {info}")
            if info:
                if info['is_all_completed']:
                    completed_ids.append(tid)
                    print(f"[DEBUG] ID {tid} 已完成所有装配，记为完成消失")
                else:
                    missing = []
                    for cls_key, need in self.required.items():
                        if not info['completed'].get(cls_key, False):
                            missing.append((cls_key, self.names.get(cls_key, cls_key)))
                    if missing:
                        print(f"[DEBUG] ID {tid} 触发报警，缺失: {missing}")
                        alerts.append({'track_id': tid, 'missing': missing})
                    incomplete_ids.append(tid)
            else:
                print(f"[DEBUG] ID {tid} 未找到状态信息")

        status = {
            'completed_ids': completed_ids,
            'incomplete_ids': incomplete_ids,
        }
        return alerts, status

    def get_labels_for_track(self, track_id: int) -> List[Dict[str, Any]]:
        """提供绘制标签所需的数据: [{name, required, achieved, completed}]（仅quantity>0）。"""
        self._ensure_track(track_id)
        labels = []
        for cls_key, need in self.required.items():
            labels.append({
                'class_key': cls_key,
                'name': self.names.get(cls_key, cls_key),
                'required': int(need),
                'achieved': int(self.state[track_id]['achieved'][cls_key]),
                'completed': bool(self.state[track_id]['completed'][cls_key]),
            })
        return labels
