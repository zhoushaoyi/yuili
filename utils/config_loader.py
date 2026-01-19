import json
from pathlib import Path
from typing import Dict, Any


def load_spec(config_filename: str = 'Configuration.json') -> Dict[str, Any]:
    """加载并校验装配规范配置。
    
    使用 pathlib 查找 config/ 目录下的配置文件。
    """
    
    # 获取项目根目录并构造标准配置路径
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent
    config_path = project_root / 'config' / config_filename
    
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        raise FileNotFoundError(f'配置文件不存在: {config_path}')

    # 加载文件
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            spec = json.load(f)
        print(f"✓ 配置文件已加载: {config_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"配置文件格式错误: {e}")

    # 校验结构
    if 'class0' not in spec:
        raise ValueError('配置文件缺少class0定义')

    class0 = spec['class0']
    if 'name' not in class0 or 'contains' not in class0:
        raise ValueError('class0需包含name与contains字段')

    contains = class0['contains']
    if not isinstance(contains, dict):
        raise ValueError('class0.contains必须为对象')

    # 规范化：仅保留class1..class6，quantity为非负整数
    normalized = {}
    for k, v in contains.items():
        if not k.startswith('class'):
            continue
        try:
            cls_idx = int(k.replace('class', ''))
        except ValueError:
            continue
        if cls_idx < 1 or cls_idx > 6:
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
    return spec

def get_project_root() -> Path:
    """获取项目根目录。"""
    return Path(__file__).resolve().parent.parent


def load_user_settings() -> Dict[str, Any]:
    """加载用户设置配置文件 (config/user_settings.json)。"""
    settings_file = get_project_root() / 'config' / 'user_settings.json'
    
    if not settings_file.exists():
        return {}
    
    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载用户配置失败: {e}")
        return {}


def save_user_settings(settings: Dict[str, Any]) -> None:
    """保存用户设置配置文件到 config/user_settings.json。"""
    config_dir = get_project_root() / 'config'
    config_dir.mkdir(exist_ok=True)
    settings_file = config_dir / 'user_settings.json'
    
    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        print(f"✓ 用户配置已保存到 {settings_file}")
    except Exception as e:
        print(f"❌ 保存用户配置失败: {e}")
