#!/usr/bin/env python3
"""复制所有模型到 HF 缓存"""
import os
import shutil
from pathlib import Path

# 设置环境变量
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HOME'] = 'C:/hf_cache'

# 源目录 (ModelScope 缓存)
modelscope_cache = Path(r"C:\Users\Administrator\.cache\modelscope\OpenDataLab\PDF-Extract-Kit-1.0\models")

# 目标目录 (HF 缓存)
hf_cache = Path(r"C:\hf_cache\hub\models--opendatalab--PDF-Extract-Kit-1.0\snapshots")

# 找到最新的 snapshot
snapshots = list(hf_cache.iterdir()) if hf_cache.exists() else []
if snapshots:
    target_snapshot = snapshots[0]
    print(f"目标 snapshot: {target_snapshot}")
    
    target_models = target_snapshot / "models"
    target_models.mkdir(exist_ok=True)
    
    # 复制所有模型目录
    for model_dir in modelscope_cache.iterdir():
        if model_dir.is_dir():
            src = model_dir
            dst = target_models / model_dir.name
            print(f"复制 {model_dir.name}...")
            if dst.exists():
                shutil.rmtree(str(dst))
            shutil.copytree(str(src), str(dst))
            print(f"  已复制到: {dst}")
    
    print("\n所有模型复制完成！")
else:
    print("未找到 HF 缓存 snapshot，请先运行一次 MinerU 下载基础模型")
