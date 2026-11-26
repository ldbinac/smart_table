import hashlib
import io
import json
import logging
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app

from app.extensions import db
from app.models.plugin import (
    Plugin, PluginVersion, PluginConfig, PluginInstallation,
    PluginType, PluginStatus, PluginConfigScope,
)

log = logging.getLogger(__name__)

def parse_semver(version: str) -> Optional[Tuple[int, int, int]]:
    """解析 semver 字符串为 (major, minor, patch)，非法返回 None"""
    if not isinstance(version, str):
        return None
    m = _SEMVER_RE.match(version.strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def semver_gt(a: str, b: str) -> bool:
    """a 是否严格大于 b（仅比较 major.minor.patch，忽略预发布/构建元数据）"""
    pa, pb = parse_semver(a), parse_semver(b)
    if pa is None or pb is None:
        return False
    return pa > pb


def _split_range(range_text: str) -> List[str]:
    """将 '>=1.7.0 <2.0.0' 拆为比较子句列表"""
    return [p for p in re.split(r'\s+', range_text.strip()) if p]


def satisfies_range(version: str, range_text: str) -> bool:
    """检查 semver 是否满足简单范围表达式（支持 > >= < <= = 与空=任意）"""
    v = parse_semver(version)
    if v is None:
        return False
    if not range_text or range_text.strip() in ('*', ''):
        return True
    for clause in _split_range(range_text):
        m = re.match(r'^(>=|<=|>|<|=|\^|~)?\s*(.+)$', clause)
        if not m:
            return False
        op, target = m.group(1) or '=', m.group(2)
        t = parse_semver(target)
        if t is None:
            return False
        if op == '>=' and not v >= t:
            return False
        if op == '<=' and not v <= t:
            return False
        if op == '>' and not v > t:
            return False
        if op == '<' and not v < t:
            return False
        if op == '=' and v != t:
            return False
        if op == '^':
            # ^1.2.3 := >=1.2.3 <2.0.0
            if not (t <= v < (t[0] + 1, 0, 0)):
                return False
        if op == '~':
            # ~1.2.3 := >=1.2.3 <1.3.0
            if not (t <= v < (t[0], t[1] + 1, 0)):
                return False
    return True


def get_host_version() -> str:
    """读取宿主版本（version.json），带缓存"""
    global _host_version_cache
    if _host_version_cache is None:
        try:
            candidates = []
            # PyInstaller 打包：优先 exe 同目录（允许部署时覆盖），其次解压资源目录
            meipass = getattr(sys, '_MEIPASS', None)
            if meipass:
                candidates.append(Path(sys.executable).parent / 'version.json')
                candidates.append(Path(meipass) / 'version.json')
            # 源码运行：version.json 位于仓库根目录（smarttable-backend 的上一级）
            root = Path(current_app.root_path)
            candidates.append(root.parent.parent / 'version.json')
            candidates.append(root.parent / 'version.json')
            for c in candidates:
                if c.exists():
                    with open(c, 'r', encoding='utf-8') as f:
                        _host_version_cache = json.load(f).get('version', '0.0.0')
                    break
            else:
                log.warning('[PluginService] 未找到 version.json，宿主版本按 0.0.0 处理，已探测: %s',
                            [str(c) for c in candidates])
                _host_version_cache = '0.0.0'
        except Exception:
            log.exception('[PluginService] 读取宿主版本失败')
            _host_version_cache = '0.0.0'
    return _host_version_cache