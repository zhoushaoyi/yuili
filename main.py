import cv2
from modules.video_processor import VideoProcessor


def main():
    """主函数，通过video_path变量控制处理模式"""
    model_path = r"data/best.pt"
    output_dir = r"output/videos"
    save_results = False
    visualize_display = True

    # 视频路径
    # video_path = r"data/1.mp4"
    # video_path = r"D:\video\video_0010.mp4"
    video_path = 0

    # 创建视频处理器
    processor = VideoProcessor(
        model_path,
        output_dir=output_dir
    )
    # processor.detection_manager.set_ignore_regions([(0, 392, 1280, 717)])

    # 打开视频源
    try:
        if isinstance(video_path, int) or (isinstance(video_path, str) and video_path.isdigit()):
            processor.camera_manager.init_camera(int(video_path) if isinstance(video_path, str) else video_path)
            print(f"✓ 已连接摄像头 {video_path}")
        else:
            processor.camera_manager.init_video(video_path)
            print(f"✓ 已打开视频文件 {video_path}")
    except Exception as e:
        print(f"✗ 错误: {e}")
        return

    # 处理视频流
    while processor.camera_manager.is_opened():
        success, frame = processor.camera_manager.read_frame()
        if not success:
            break

        processor.fps_manager.start_timer()
        
        # 处理帧
        annotated_frame, tracked_boxes, alerts = processor.frame_processor.process_frame(frame, visualize=visualize_display)
        
        if visualize_display:
            cv2.imshow('Detection', annotated_frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
        
        processor.fps_manager.end_timer()

    processor.release()
    cv2.destroyAllWindows()
    print("✓ 处理完成")


if __name__ == "__main__":
    main()
