# Media Deduplicator

图片/视频去重工具，支持 GPU 加速（NVIDIA NVDEC），大规模媒体库的快速重复文件检测。

## 功能

- **图片去重**：基于 pHash 感知哈希，支持完全相同和压缩版本的检测
- **视频去重**：场景检测 + 关键帧提取 + 倒排索引锚点评分，支持剪辑/压缩/重编码版本的识别
- **GPU 加速**：RTX 4060+ 利用 ffmpeg NVDEC 硬件解码，视频处理提速 2-5x
- **断点续跑**：SQLite checkpoint，崩溃后从断点继续，不重算
- **GUI 界面**：tkinter 图形界面，支持缩略图预览、结果导入导出

## 安装

```bash
pip install -r requirements.txt
```

### GPU 加速（可选）

需要安装带 CUDA 支持的 ffmpeg：

```powershell
winget install Gyan.FFmpeg
```

## 使用

### 命令行

```bash
python main.py <目标文件夹>
```

### GUI

```bash
python gui.py
```

## 配置

编辑 `config.py` 调整阈值和参数。

## 输出

处理结果保存在 `results/duplicates.json`，可在 GUI 中通过「导入报告」加载。

## 依赖

- Python 3.8+
- Pillow, opencv-python, imagehash, scikit-image, numpy, tqdm
- ffmpeg（可选，GPU 加速）
