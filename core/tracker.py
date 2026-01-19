import numpy as np
from filterpy.kalman import KalmanFilter


def linear_assignment(cost_matrix):
    """线性分配算法"""
    try:
        import lap
        _, x, y = lap.lapjv(cost_matrix, extend_cost=True)
        return np.array([[y[i],i] for i in x if i >= 0])
    except ImportError:
        from scipy.optimize import linear_sum_assignment
        x, y = linear_sum_assignment(cost_matrix)
        return np.array(list(zip(x, y)))


def iou_batch(bb_test, bb_gt):
    """
    计算两个边界框之间的IOU
    bb_test: [x1,y1,x2,y2]
    bb_gt: [x1,y1,x2,y2]
    """
    bb_gt = np.expand_dims(bb_gt, 0)
    bb_test = np.expand_dims(bb_test, 1)
    
    xx1 = np.maximum(bb_test[..., 0], bb_gt[..., 0])
    yy1 = np.maximum(bb_test[..., 1], bb_gt[..., 1])
    xx2 = np.minimum(bb_test[..., 2], bb_gt[..., 2])
    yy2 = np.minimum(bb_test[..., 3], bb_gt[..., 3])
    w = np.maximum(0., xx2 - xx1)
    h = np.maximum(0., yy2 - yy1)
    wh = w * h
    o = wh / ((bb_test[..., 2] - bb_test[..., 0]) * (bb_test[..., 3] - bb_test[..., 1])                                      
        + (bb_gt[..., 2] - bb_gt[..., 0]) * (bb_gt[..., 3] - bb_gt[..., 1]) - wh)                                              
    return(o)


def convert_bbox_to_z(bbox):
    """
    将边界框 [x1,y1,x2,y2] 转换为 [x,y,s,r] 格式
    其中 x,y 是中心点，s 是面积，r 是宽高比
    """
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = bbox[0] + w/2.
    y = bbox[1] + h/2.
    s = w * h    # scale is just area
    r = w / float(h)
    return np.array([x, y, s, r]).reshape((4, 1))


def convert_x_to_bbox(x, score=None):
    """
    将 [x,y,s,r] 格式转换为 [x1,y1,x2,y2] 格式
    """
    w = np.sqrt(x[2] * x[3])
    h = x[2] / w
    if(score==None):
        return np.array([x[0]-w/2.,x[1]-h/2.,x[0]+w/2.,x[1]+h/2.]).reshape((1,4))
    else:
        return np.array([x[0]-w/2.,x[1]-h/2.,x[0]+w/2.,x[1]+h/2.,score]).reshape((1,5))


class KalmanBoxTracker:
    """
    卡尔曼滤波器追踪器，用于追踪单个目标
    """
    count = 0
    
    def __init__(self, bbox):
        """
        使用初始边界框初始化追踪器
        """
        # 定义恒定速度模型
        self.kf = KalmanFilter(dim_x=7, dim_z=4) 
        self.kf.F = np.array([[1,0,0,0,1,0,0],[0,1,0,0,0,1,0],[0,0,1,0,0,0,1],[0,0,0,1,0,0,0],  [0,0,0,0,1,0,0],[0,0,0,0,0,1,0],[0,0,0,0,0,0,1]])
        self.kf.H = np.array([[1,0,0,0,0,0,0],[0,1,0,0,0,0,0],[0,0,1,0,0,0,0],[0,0,0,1,0,0,0]])

        self.kf.R[2:,2:] *= 10.
        self.kf.P[4:,4:] *= 1000. # 给不可观测的初始速度高不确定性
        self.kf.P *= 10.
        self.kf.Q[-1,-1] *= 0.01
        self.kf.Q[4:,4:] *= 0.01

        self.kf.x[:4] = convert_bbox_to_z(bbox)
        self.time_since_update = 0
        self.id = KalmanBoxTracker.count
        KalmanBoxTracker.count += 1
        self.history = []
        self.hits = 0
        self.hit_streak = 0
        self.age = 0
        self.has_been_returned = False  # 标记是否曾经被返回过（即达到过min_hits）

    def update(self, bbox):
        """
        使用观测到的边界框更新状态向量
        """
        self.time_since_update = 0
        self.history = []
        self.hits += 1
        self.hit_streak += 1
        self.kf.update(convert_bbox_to_z(bbox))

    def predict(self):
        """
        推进状态向量并返回预测的边界框估计
        """
        if((self.kf.x[6]+self.kf.x[2])<=0):
            self.kf.x[6] *= 0.0
        self.kf.predict()
        self.age += 1
        if(self.time_since_update>0):
            self.hit_streak = 0
        self.time_since_update += 1
        self.history.append(convert_x_to_bbox(self.kf.x))
        return self.history[-1]

    def get_state(self):
        """
        返回当前边界框估计
        """
        return convert_x_to_bbox(self.kf.x)


def associate_detections_to_trackers(detections, trackers, iou_threshold=0.3):
    """
    将检测结果分配给追踪目标
    返回匹配、未匹配检测和未匹配追踪器的列表
    """
    if(len(trackers)==0):
        return np.empty((0,2),dtype=int), np.arange(len(detections)), np.empty((0,5),dtype=int)

    iou_matrix = iou_batch(detections, trackers)

    if min(iou_matrix.shape) > 0:
        a = (iou_matrix > iou_threshold).astype(np.int32)
        if a.sum(1).max() == 1 and a.sum(0).max() == 1:
            matched_indices = np.stack(np.where(a), axis=1)
        else:
            matched_indices = linear_assignment(-iou_matrix)
    else:
        matched_indices = np.empty(shape=(0,2))

    unmatched_detections = []
    for d, det in enumerate(detections):
        if(d not in matched_indices[:,0]):
            unmatched_detections.append(d)
    unmatched_trackers = []
    for t, trk in enumerate(trackers):
        if(t not in matched_indices[:,1]):
            unmatched_trackers.append(t)

    # 过滤低IOU的匹配
    matches = []
    for m in matched_indices:
        if(iou_matrix[m[0], m[1]]<iou_threshold):
            unmatched_detections.append(m[0])
            unmatched_trackers.append(m[1])
        else:
            matches.append(m.reshape(1,2))
    if(len(matches)==0):
        matches = np.empty((0,2),dtype=int)
    else:
        matches = np.concatenate(matches,axis=0)

    return matches, np.array(unmatched_detections), np.array(unmatched_trackers)


class Sort:
    """
    SORT追踪器主类
    """
    def __init__(self, max_age=30, min_hits=60, iou_threshold=0.5):
        """
        设置SORT的关键参数
        """
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.trackers = []
        self.frame_count = 0

    def update(self, dets=np.empty((0, 5))):
        """
        更新追踪器
        参数:
          dets - 检测结果数组，格式为 [[x1,y1,x2,y2,score],[x1,y1,x2,y2,score],...]
        返回:
          (追踪结果数组, disappeared_ids)
          追踪结果数组最后一列是目标ID；disappeared_ids为本帧内死亡的track id列表
        """
        self.frame_count += 1
        # 从现有追踪器获取预测位置
        trks = np.zeros((len(self.trackers), 5))
        to_del = []
        disappeared_ids = []
        ret = []
        for t, trk in enumerate(trks):
            pos = self.trackers[t].predict()[0]
            trk[:] = [pos[0], pos[1], pos[2], pos[3], 0]
            if np.any(np.isnan(pos)):
                to_del.append(t)
        trks = np.ma.compress_rows(np.ma.masked_invalid(trks))
        for t in reversed(to_del):
            tracker = self.trackers.pop(t)
            # 只有曾经被返回过的追踪器才报告为消失
            if tracker.has_been_returned:
                disappeared_ids.append(tracker.id + 1)
        matched, unmatched_dets, unmatched_trks = associate_detections_to_trackers(dets,trks, self.iou_threshold)

        # 用分配的检测结果更新匹配的追踪器
        for m in matched:
            self.trackers[m[1]].update(dets[m[0], :])

        # 为未匹配的检测创建和初始化新的追踪器
        for i in unmatched_dets:
            trk = KalmanBoxTracker(dets[i,:])
            self.trackers.append(trk)
        i = len(self.trackers)
        for trk in reversed(self.trackers):
            d = trk.get_state()[0]
            track_id = trk.id + 1
            if (trk.time_since_update < 1) and (trk.hit_streak >= self.min_hits or self.frame_count <= self.min_hits):
                ret.append(np.concatenate((d,[track_id])).reshape(1,-1)) # +1 因为MOT基准需要正数
                trk.has_been_returned = True  # 标记该追踪器曾经被返回过
            i -= 1
            # 移除死亡的追踪器（只报告那些曾经被返回过的追踪器的消失）
            if(trk.time_since_update > self.max_age):
                self.trackers.pop(i)
                # 只有曾经被返回过的追踪器才报告为消失
                if trk.has_been_returned:
                    disappeared_ids.append(track_id)
        if(len(ret)>0):
            tracks = np.concatenate(ret)
        else:
            tracks = np.empty((0,5))
        return tracks, disappeared_ids


class TrackerManager:
    """
    追踪管理器，封装SORT追踪器
    """
    def __init__(self, max_age=30, min_hits=30, iou_threshold=0.5):
        """
        初始化追踪管理器
        """
        self.sort_tracker = Sort(max_age=max_age, min_hits=min_hits, iou_threshold=iou_threshold)
        self.tracked_boxes = []
        self.last_disappeared_ids = []
    
    def update_tracks(self, detections, target_class=0):
        """
        更新追踪
        参数:
            detections: 检测结果数组 [x1,y1,x2,y2,score]
            target_class: 目标类别，默认为0（storage box）
        返回:
            追踪结果数组 [x1,y1,x2,y2,id]
        """
        # 更新SORT追踪器
        tracked_results, disappeared_ids = self.sort_tracker.update(detections)
        self.tracked_boxes = tracked_results
        self.last_disappeared_ids = disappeared_ids
        return tracked_results, disappeared_ids
    
    def get_tracked_boxes(self):
        """
        获取当前追踪的目标列表
        """
        return self.tracked_boxes
