import json
import os
from typing import Dict, Any


def load_spec(config_path: str = 'Configuration.josn') -> Dict[str, Any]:
    """加载并校验装配规范配置。

    返回结构示例:
    {
        'class0': {
            'name': 'storage box',
            'contains': {
                'class1': {'name': 'comb clamp', 'quantity': 1},
                ...
            }
        }
    }
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f'配置文件不存在: {config_path}')

    with open(config_path, 'r', encoding='utf-8') as f:
        spec = json.load(f)

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
        name = v.get('name', f'class{cls_idx}')
        qty = int(v.get('quantity', 0))
        if qty < 0:
            qty = 0
        normalized[f'class{cls_idx}'] = {'name': name, 'quantity': qty}

    spec['class0']['contains'] = normalized
    return spec
