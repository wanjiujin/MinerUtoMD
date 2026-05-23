#!/usr/bin/env python3
"""
复制 ModelScope 模型到 HuggingFace 缓存目录
解决 HuggingFace 镜像无法访问的问题
"""
import os
import shutil
from pathlib import Path

def copy_models():
    """复制所有模型到 HF 缓存"""
    # 设置环境变量
    os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
    os.environ['HF_HOME'] = 'C:/hf_cache'
    
    # 源目录 (ModelScope 缓存)
    modelscope_cache = Path(r"C:\Users\Administrator\.cache\modelscope\OpenDataLab\PDF-Extract-Kit-1.0\models")
    
    # 目标目录 (HF 缓存)
    hf_cache = Path(r"C:\hf_cache\hub\models--opendatalab--PDF-Extract-Kit-1.0\snapshots")
    
    if not modelscope_cache.exists():
        print(f"错误: ModelScope 缓存目录不存在: {modelscope_cache}")
        print("请先运行一次 MinerU 下载基础模型")
        return False
    
    # 找到 HF 缓存的 snapshot
    snapshots = list(hf_cache.iterdir()) if hf_cache.exists() else []
    
    if not snapshots:
        print("错误: 未找到 HF 缓存 snapshot")
        print("请先运行一次 MinerU 初始化缓存")
        return False
    
    target_snapshot = snapshots[0]
    print(f"目标 snapshot: {target_snapshot}")
    
    target_models = target_snapshot / "models"
    target_models.mkdir(exist_ok=True)
    
    # 复制所有模型目录
    copied_count = 0
    for model_dir in modelscope_cache.iterdir():
        if model_dir.is_dir():
            src = model_dir
            dst = target_models / model_dir.name
            
            print(f"复制 {model_dir.name}...")
            
            if dst.exists():
                shutil.rmtree(str(dst))
            
            shutil.copytree(str(src), str(dst))
            print(f"  ✓ 已复制到: {dst}")
            copied_count += 1
    
    print(f"\n完成！共复制 {copied_count} 个模型目录")
    return True


if __name__ == "__main__":
    copy_models()
