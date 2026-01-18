import cv2
from model.path_handler import PathHandler


def main():
    """主函数，通过video_path变量控制处理模式"""
    model_path = r"C:\Users\Administrator\Desktop\weights\best.pt"
    output_dir = r"D:\vision\videos"
    save_results = False
    visualize_display = True

    # 视频路径
    # video_path = r"D:\vision\yueli-video/ceshi2.mp4"
    # video_path = r"D:\video\video_0010.mp4"
    video_path = 0

    # 创建路径处理器
    path_handler = PathHandler(
        model_path,
        output_dir=output_dir,
        default_save_results=save_results,
        default_visualize=visualize_display
    )
    # path_handler.processor.detection_manager.set_ignore_regions([(0, 392, 1280, 717)])

    # 使用路径处理器处理指定路径
    path_handler.process_path(video_path, save_results=save_results, visualize=visualize_display)

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
