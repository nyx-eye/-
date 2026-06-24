# hybrid_deduplicator.py
import threading
import os
from media_scanner import MediaScanner
from image_deduplicator import ImageDeduplicator
from video_deduplicator import VideoDeduplicator
from checkpoint import Checkpoint
from utils import get_file_size_mb, log_info, log_success


class HybridMediaDeduplicator:
    def __init__(self, folder_path, max_workers=4,
                 stop_event=None, progress_callback=None,
                 fail_callback=None, resume=True):
        self.folder_path = folder_path
        self.max_workers = max_workers
        self.stop_event = stop_event or threading.Event()
        self.progress_callback = progress_callback
        self.all_duplicates = []
        self.summary = {}

        # ── checkpoint ──
        self.checkpoint = Checkpoint() if resume else None
        self._resume = resume

        if self.checkpoint:
            status = self.checkpoint.get_status()
            counts = status.get("_counts", {})
            if counts.get("images", 0) > 0 or counts.get("videos", 0) > 0:
                log_info(f"发现断点: {counts.get('images', 0)} 图 + "
                         f"{counts.get('videos', 0)} 视频已处理, "
                         f"{counts.get('duplicates', 0)} 组重复已记录")

        self.scanner = MediaScanner(folder_path,
                                    stop_event=self.stop_event,
                                    progress_callback=self.progress_callback)

        self.image_dedup = ImageDeduplicator(max_workers,
                                              stop_event=self.stop_event,
                                              progress_callback=self.progress_callback)
        if self.checkpoint:
            self.image_dedup.set_checkpoint(self.checkpoint)

        self.video_dedup = VideoDeduplicator(max_workers,
                                              stop_event=self.stop_event,
                                              progress_callback=self.progress_callback)
        if self.checkpoint:
            self.video_dedup.set_checkpoint(self.checkpoint)

        if fail_callback:
            self.image_dedup.set_fail_callback(fail_callback)
            self.video_dedup.set_fail_callback(fail_callback)

    def _check_stop(self):
        return self.stop_event.is_set()

    def run(self):
        log_info("=" * 50)
        log_info("多媒体去重 — checkpoint + 锚点评分")
        log_info("=" * 50)

        cp = self.checkpoint

        # ── 阶段1: 扫描 ──
        if cp and cp.is_phase_done("scan"):
            log_info("阶段1 扫描已完成，跳过")
        else:
            cnt = self.scanner.scan()
            if self._check_stop():
                return False
            if cnt == 0:
                return False
            if cp:
                cp.save_progress("scan", cnt, cnt)

        # ── 阶段2: 图片 ──
        if cp and cp.is_phase_done("images"):
            log_info("阶段2 图片处理已完成，从 checkpoint 恢复")
            for path, phash_str, _size in cp.get_processed_images():
                self.image_dedup.file_to_hash[path] = phash_str
                self.image_dedup.image_hashes[phash_str].append(path)
            self.image_dedup.find_duplicates()
            if self.image_dedup.duplicate_groups:
                self.all_duplicates.extend(self.image_dedup.duplicate_groups)
        elif self.scanner.image_files:
            if self._check_stop():
                return False
            self.all_duplicates.extend(
                self.image_dedup.run(self.scanner.image_files)
            )
            if cp:
                # total 用实际算哈希的数量（大小分组后），不是全量
                processed = len(self.image_dedup.file_to_hash)
                cp.save_progress("images", processed, processed)
        if self._check_stop():
            return False

        # ── 阶段3: 视频提取 ──
        if cp and cp.is_phase_done("videos"):
            log_info("阶段3 视频提取已完成，从 checkpoint 恢复")
            loaded = self.video_dedup.load_checkpoint()
            log_info(f"恢复 {loaded} 个视频的关键帧")
        elif self.scanner.video_files:
            if self._check_stop():
                return False
            self.video_dedup.process_videos(self.scanner.video_files)
        if self._check_stop():
            return False

        # ── 阶段4: 视频匹配 ──
        if cp and cp.is_phase_done("matching"):
            log_info("阶段4 视频匹配已完成，从 checkpoint 读取结果")
            self.all_duplicates.extend(cp.get_duplicates())
        elif len(self.video_dedup.video_keyframe_hashes) >= 2:
            if self._check_stop():
                return False
            self.video_dedup.find_identical_videos()
            self.video_dedup.find_edited_reencoded_videos()
            self.video_dedup._merge_connected_groups()
            self.all_duplicates.extend(self.video_dedup.duplicate_groups)
            if cp:
                # 将图片重复组也写入 checkpoint 的 duplicates 表
                cp.clear_duplicates()
                for idx, g in enumerate(self.all_duplicates, 1):
                    cp.save_duplicate_group(idx, g)
                cp.save_progress("matching", 1, 1)

        # ── 阶段5: 报告 ──
        if cp:
            cp.save_progress("report", 1, 1)
            cp.cleanup()  # 结果已出，清空 checkpoint 数据

        log_success("处理完成")
        return True

    def get_summary(self):
        s = self.scanner.get_summary()
        total_dup = sum(g.get("count", 0) for g in self.all_duplicates)
        save = self._calc_save()
        self.summary = {
            "scan_folder": self.folder_path,
            "total_files": s["total_files"],
            "image_files": s["image_files"],
            "video_files": s["video_files"],
            "duplicate_groups": len(self.all_duplicates),
            "total_duplicates": total_dup,
            "can_save_mb": round(save, 2),
        }
        return self.summary

    def _calc_save(self):
        t = 0
        for g in self.all_duplicates:
            fs = g.get("files", [])
            if len(fs) < 2:
                continue
            sz = sorted([get_file_size_mb(f) for f in fs])
            t += sum(sz[1:])
        return t
