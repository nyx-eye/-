# media_scanner.py
import os
import threading
from config import SUPPORTED_IMAGE_EXTENSIONS, SUPPORTED_VIDEO_EXTENSIONS
from utils import log_info

class MediaScanner:
    def __init__(self, root_path, stop_event=None, progress_callback=None):
        self.root = root_path
        self.image_files = []
        self.video_files = []
        self.stop_event = stop_event or threading.Event()
        self.progress_callback = progress_callback

    def scan(self):
        log_info(f"正在扫描: {self.root}")

        # 先收集所有文件路径
        all_files = []
        for r, _, fs in os.walk(self.root):
            if self.stop_event.is_set():
                log_info("扫描被用户停止")
                return 0
            for f in fs:
                all_files.append((r, f))

        total = len(all_files)
        cnt = 0
        for idx, (r, f) in enumerate(all_files):
            # 每 100 个文件检查一次停止标志
            if idx % 100 == 0 and self.stop_event.is_set():
                log_info("扫描被用户停止")
                break

            ext = os.path.splitext(f)[1].lower()
            full = os.path.join(r, f)
            if ext in SUPPORTED_IMAGE_EXTENSIONS:
                self.image_files.append(full)
                cnt += 1
            elif ext in SUPPORTED_VIDEO_EXTENSIONS:
                self.video_files.append(full)
                cnt += 1

            # 进度回调
            if self.progress_callback and idx % 50 == 0:
                self.progress_callback('scan', idx + 1, total)

        # 扫描完成
        if self.progress_callback:
            self.progress_callback('scan', total, total)

        log_info(f"扫描完成：图片 {len(self.image_files)} 视频 {len(self.video_files)}")
        return cnt

    def get_summary(self):
        return {
            'total_files': len(self.image_files) + len(self.video_files),
            'image_files': len(self.image_files),
            'video_files': len(self.video_files)
        }
