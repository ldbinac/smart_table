# Auto-split skeleton

"""
插件服务模块
负责安装包（.stplugin.zip）解包校验、manifest 清单校验、semver/宿主版本兼容检查、
生命周期状态机（安装/升级/回滚/启停/卸载）与两层 RBAC 辅助。

安全要点：
- zip 路径穿越防护（绝对路径 / .. / 盘符前缀）
- zip bomb 防护（解压总大小 / 文件数上限）
- manifest jsonschema 校验（入口存在、semver、engines 兼容、apiVersion 协商）
"""
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

from ._version import parse_semver, semver_gt, _split_range, satisfies_range, get_host_version
from ._pkg import _validate_manifest, _backend_root, _plugin_storage_root, resolve_package_path, _PackageError, _safe_extract, _read_manifest_from_zip, PluginValidationError, PluginNotFoundError
from ._other import log, MAX_PACKAGE_SIZE, MAX_FILE_COUNT, MAX_ENTRY_RATIO, MAX_ICON_SIZE, PLUGIN_STORAGE_ROOT_NAME, SUPPORTED_API_VERSIONS, ERR_INVALID_PACKAGE, ERR_MANIFEST_INVALID, ERR_ENTRY_MISSING, ERR_VERSION_INVALID, ERR_ENGINES_INCOMPATIBLE, ERR_API_VERSION_MISMATCH, ERR_DOWNGRADE_FORBIDDEN, ERR_CONFIG_INCOMPATIBLE, ERR_PLUGIN_EXISTS_VERSION, ERR_PLUGIN_TYPE_NOT_INSTALLABLE, AUTO_ERROR_FAILURE_THRESHOLD, _SEMVER_RE, _PLUGIN_ID_RE, _VALID_PERMISSION_LEVELS, _VALID_EXTENSION_TYPES, PluginService
