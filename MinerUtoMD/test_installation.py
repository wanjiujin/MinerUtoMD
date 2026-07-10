"""
测试脚本 - 验证安装和基本功能
"""
import sys
import io
from pathlib import Path

# 设置UTF-8输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """测试模块导入"""
    print("=" * 50)
    print("测试模块导入...")
    print("=" * 50)
    
    try:
        from mineru_extractor import MinerUExtractor
        print("[OK] MinerUExtractor 导入成功")
    except Exception as e:
        print(f"[FAIL] MinerUExtractor 导入失败: {e}")
        return False
    
    try:
        from pandoc_converter import PandocConverter
        print("[OK] PandocConverter 导入成功")
    except Exception as e:
        print(f"[FAIL] PandocConverter 导入失败: {e}")
        return False
    
    try:
        from markdown_optimizer import MarkdownOptimizer
        print("[OK] MarkdownOptimizer 导入成功")
    except Exception as e:
        print(f"[FAIL] MarkdownOptimizer 导入失败: {e}")
        return False
    
    try:
        from doc_workflow import PDFWorkflow, WordWorkflow
        print("[OK] Workflow 模块导入成功")
    except Exception as e:
        print(f"[FAIL] Workflow 导入失败: {e}")
        return False
    
    return True


def test_dependencies():
    """测试依赖工具"""
    print("\n" + "=" * 50)
    print("测试依赖工具...")
    print("=" * 50)
    
    from pandoc_converter import PandocConverter
    from mineru_extractor import MinerUExtractor
    
    # 测试Pandoc
    pandoc = PandocConverter()
    if pandoc.check_installation():
        print("[OK] Pandoc 已安装并可用")
    else:
        print("[FAIL] Pandoc 未安装或不可用")
        print("  请从 https://pandoc.org/installing.html 下载安装")
    
    # 测试MinerU
    mineru = MinerUExtractor()
    if mineru.check_installation():
        print("[OK] MinerU 已安装并可用")
    else:
        print("[FAIL] MinerU 未安装或不可用")
        print("  运行: pip install magic-pdf[full]")
    
    return True


def test_markdown_optimizer():
    """测试Markdown优化器"""
    print("\n" + "=" * 50)
    print("测试Markdown优化器...")
    print("=" * 50)
    
    from markdown_optimizer import MarkdownOptimizer
    
    optimizer = MarkdownOptimizer()
    
    # 测试内容
    test_md = """
# 标题1


## 标题2



内容段落1

内容段落2
"""
    
    # 创建临时文件
    temp_file = Path("test_temp.md")
    temp_file.write_text(test_md, encoding='utf-8')
    
    try:
        result = optimizer.optimize(str(temp_file))
        
        if result['success']:
            print("[OK] Markdown优化功能正常")
            print(f"  原始长度: {result['original_length']}")
            print(f"  优化后长度: {result['optimized_length']}")
        else:
            print(f"[FAIL] Markdown优化失败: {result['error']}")
        
    finally:
        # 清理临时文件
        if temp_file.exists():
            temp_file.unlink()
    
    return True


def test_config():
    """测试配置文件"""
    print("\n" + "=" * 50)
    print("测试配置文件...")
    print("=" * 50)
    
    import yaml
    
    config_file = Path(__file__).parent / "config.yaml"
    
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            print("[OK] 配置文件加载成功")
            print(f"  MinerU输出格式: {config.get('mineru', {}).get('output_format')}")
            print(f"  Pandoc PDF引擎: {config.get('pandoc', {}).get('pdf_engine')}")
        except Exception as e:
            print(f"[FAIL] 配置文件加载失败: {e}")
    else:
        print("[FAIL] 配置文件不存在")
    
    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 50)
    print("MinerUtoMD 测试脚本")
    print("=" * 50 + "\n")
    
    tests = [
        ("模块导入", test_imports),
        ("依赖工具", test_dependencies),
        ("Markdown优化器", test_markdown_optimizer),
        ("配置文件", test_config),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n[FAIL] 测试 '{name}' 异常: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"测试完成: {passed} 通过, {failed} 失败")
    print("=" * 50 + "\n")
    
    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
