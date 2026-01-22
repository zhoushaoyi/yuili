import json
from pathlib import Path
from typing import Dict, Any
import os


# 全局配置缓存和时间戳 (用于检测配置文件是否被修改)
_spec_cache = {}
_spec_timestamp = {}


def get_project_root() -> Path:
    """获取项目根目录。"""
    return Path(__file__).resolve().parent.parent


def load_spec(config_filename: str = 'Configuration.json', force_reload: bool = False) -> Dict[str, Any]:
    """加载并校验装配规范配置。
    
    参数:
        config_filename: 配置文件名 (默认 'Configuration.json')
        force_reload: 强制重新加载，忽略缓存 (默认 False)
    
    返回:
        验证后的配置字典
    
    说明:
        - 使用文件修改时间戳检测配置变化，自动刷新缓存
        - force_reload=True 会强制重新读取文件
        - 每次读取都会输出调试信息以便追踪
    """
    
    # 获取项目根目录并构造标准配置路径
    project_root = get_project_root()
    config_path = project_root / 'config' / config_filename
    
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        raise FileNotFoundError(f'配置文件不存在: {config_path}')

    # 检查文件是否被修改
    try:
        current_mtime = os.path.getmtime(config_path)
    except OSError as e:
        print(f"❌ 无法获取文件修改时间: {e}")
        current_mtime = None

    # 判断是否需要重新加载
    cache_key = str(config_path)
    need_reload = (
        force_reload or 
        cache_key not in _spec_cache or 
        current_mtime is None or
        _spec_timestamp.get(cache_key) != current_mtime
    )
    
    if need_reload:
        # 加载文件
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                spec = json.load(f)
            print(f"✓ [重新加载配置] {config_path}")
            if current_mtime is not None:
                print(f"  文件修改时间: {current_mtime}")
        except json.JSONDecodeError as e:
            raise ValueError(f"配置文件格式错误: {e}")
    else:
        # 使用缓存
        spec = _spec_cache[cache_key]
        print(f"✓ [使用缓存配置] {config_path}")

    # 校验结构
    if 'class0' not in spec:
        raise ValueError('配置文件缺少class0定义')

    class0 = spec['class0']
    if 'name' not in class0 or 'contains' not in class0:
        raise ValueError('class0需包含name与contains字段')

    contains = class0['contains']
    if not isinstance(contains, dict):
        raise ValueError('class0.contains必须为对象')

    # 规范化：仅保留class1..class9，quantity为非负整数
    normalized = {}
    for k, v in contains.items():
        if not k.startswith('class'):
            continue
        try:
            cls_idx = int(k.replace('class', ''))
        except ValueError:
            continue
        if cls_idx < 1 or cls_idx > 10:  # 支持 class1 到 class9
            continue
        
        # 校验数量字段
        try:
            qty = int(v.get('quantity', 0))
            if qty < 0:
                qty = 0
        except (TypeError, ValueError):
            qty = 0

        normalized[k] = {
            'name': v.get('name', ''),
            'quantity': qty
        }

    spec['class0']['contains'] = normalized
    
    # 保存到缓存
    _spec_cache[cache_key] = spec
    _spec_timestamp[cache_key] = current_mtime
    
    print(f"  规范化后的物品列表: {list(normalized.keys())}")
    return spec

def get_project_root() -> Path:
    """获取项目根目录。"""
    return Path(__file__).resolve().parent.parent


def load_user_settings() -> Dict[str, Any]:
    """加载用户设置配置文件 (config/user_settings.json)。
    
    说明:
        - user_settings.json 用于保存用户在Web界面上的检测参数（非物品清单）
        - 每次启动时重新读取，不使用缓存
        - 如果文件不存在，返回空字典
    """
    settings_file = get_project_root() / 'config' / 'user_settings.json'
    
    if not settings_file.exists():
        print(f"ℹ 用户设置文件不存在: {settings_file}，使用默认值")
        return {}
    
    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        print(f"✓ 用户设置已加载: {settings_file}")
        return settings
    except Exception as e:
        print(f"❌ 加载用户配置失败: {e}")
        return {}


def save_user_settings(settings: Dict[str, Any]) -> None:
    """保存用户设置配置文件到 config/user_settings.json。
    
    说明:
        - 每次启动检测前保存当前的Web界面参数
        - 这与 Configuration.json (物品清单) 是分离的
    """
    config_dir = get_project_root() / 'config'
    config_dir.mkdir(exist_ok=True)
    settings_file = config_dir / 'user_settings.json'
    
    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        print(f"✓ 用户配置已保存: {settings_file}")
    except Exception as e:
        print(f"❌ 保存用户配置失败: {e}")
