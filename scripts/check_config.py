#!/usr/bin/env python3
"""
配置诊断脚本：检查 Configuration.json 和 user_settings.json 的加载情况

使用方法:
    python scripts/check_config.py
"""

import os
import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from utils.config_loader import load_spec, load_user_settings, get_project_root


def print_section(title):
    """打印分隔符标题"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def check_files_exist():
    """检查配置文件是否存在"""
    print_section("1. 检查配置文件是否存在")
    
    root = get_project_root()
    config_dir = root / 'config'
    config_file = config_dir / 'Configuration.json'
    settings_file = config_dir / 'user_settings.json'
    
    print(f"项目根目录: {root}")
    print(f"config 目录: {config_dir}")
    print(f"  存在: {config_dir.exists()}\n")
    
    print(f"Configuration.json: {config_file}")
    print(f"  存在: {config_file.exists()}")
    if config_file.exists():
        print(f"  大小: {config_file.stat().st_size} 字节")
        print(f"  修改时间: {config_file.stat().st_mtime}\n")
    
    print(f"user_settings.json: {settings_file}")
    print(f"  存在: {settings_file.exists()}")
    if settings_file.exists():
        print(f"  大小: {settings_file.stat().st_size} 字节")
        print(f"  修改时间: {settings_file.stat().st_mtime}\n")
    
    return config_file.exists(), settings_file.exists()


def check_configuration_json():
    """检查 Configuration.json 的内容"""
    print_section("2. 检查 Configuration.json 内容")
    
    try:
        spec = load_spec('Configuration.json', force_reload=True)
        
        print("✓ Configuration.json 加载成功\n")
        
        if 'class0' in spec:
            class0 = spec['class0']
            print(f"  storage box 名称: {class0.get('name', 'N/A')}\n")
            
            contains = class0.get('contains', {})
            print(f"  物品清单 ({len(contains)} 项):")
            for cls_key, item in sorted(contains.items()):
                name = item.get('name', 'Unknown')
                qty = item.get('quantity', 0)
                print(f"    {cls_key}: {name} (数量: {qty})")
        else:
            print("❌ 缺少 class0 字段")
        
        return True
    except Exception as e:
        print(f"❌ 加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_user_settings():
    """检查 user_settings.json 的内容"""
    print_section("3. 检查 user_settings.json 内容")
    
    try:
        settings = load_user_settings()
        
        if settings:
            print("✓ user_settings.json 加载成功\n")
            print("  用户配置参数:")
            for key, value in sorted(settings.items()):
                print(f"    {key}: {value}")
        else:
            print("ℹ user_settings.json 为空或不存在（首次运行是正常的）")
        
        return True
    except Exception as e:
        print(f"❌ 加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_cache_mechanism():
    """检查缓存机制是否正常工作"""
    print_section("4. 检查缓存机制")
    
    try:
        print("第一次加载 (force_reload=True):")
        spec1 = load_spec('Configuration.json', force_reload=True)
        print(f"  物品数量: {len(spec1['class0']['contains'])}\n")
        
        print("第二次加载 (使用缓存):")
        spec2 = load_spec('Configuration.json', force_reload=False)
        print(f"  物品数量: {len(spec2['class0']['contains'])}\n")
        
        if spec1 == spec2:
            print("✓ 缓存机制正常工作")
            return True
        else:
            print("❌ 缓存内容不一致")
            return False
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


def main():
    """主诊断程序"""
    print("\n" + "="*70)
    print("  配置诊断工具 (Configuration Diagnostic Tool)")
    print("="*70)
    
    config_exists, settings_exists = check_files_exist()
    config_ok = check_configuration_json() if config_exists else False
    settings_ok = check_user_settings()
    cache_ok = check_cache_mechanism() if config_ok else False
    
    # 总结
    print_section("诊断总结")
    
    checks = [
        ("配置文件存在", config_exists),
        ("Configuration.json 可加载", config_ok),
        ("user_settings.json 可加载", settings_ok),
        ("缓存机制正常", cache_ok),
    ]
    
    all_ok = all(result for _, result in checks)
    
    for check_name, result in checks:
        status = "✓" if result else "❌"
        print(f"  {status} {check_name}")
    
    print()
    if all_ok:
        print("✓ 所有检查通过！配置系统工作正常。")
        print("\n使用建议:")
        print("  1. 修改 Configuration.json 后，下次启动检测时会自动加载新配置")
        print("  2. Web 界面上的参数会保存到 user_settings.json")
        print("  3. 可以定期运行此脚本检查配置状态\n")
        return 0
    else:
        print("❌ 诊断发现问题，请检查上述输出并修复相关文件。\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
