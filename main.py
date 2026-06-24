# main.py
from hybrid_deduplicator import HybridMediaDeduplicator

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python main.py 目标文件夹")
        sys.exit(1)
    folder = sys.argv[1]
    dedup = HybridMediaDeduplicator(folder)
    dedup.run()
    dedup.get_summary()